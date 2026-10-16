<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'
import ePub, {
  EpubCFI,
  type Book,
  type Contents,
  type Location,
  type NavItem,
  type Rendition,
} from 'epubjs'
import { INK, type ReaderHandle, type ReaderProgress, type TocItem } from './types'
import { createSwipe, tapZone, type TurnDirection } from './swipe'

/** `singlePage` forces one page at a time (phones); otherwise wide screens get a spread. */
const props = defineProps<{ url: string; fontSize: number; singlePage: boolean }>()
const emit = defineEmits<{
  ready: [toc: TocItem[]]
  /** The table of contents again, now with page numbers (sent whenever pages are recounted). */
  toc: [toc: TocItem[]]
  progress: [progress: ReaderProgress]
  error: [message: string]
  key: [event: KeyboardEvent]
  turn: [direction: TurnDirection]
}>()

const viewer = useTemplateRef<HTMLDivElement>('viewer')
/** Page number(s) printed under the visible page(s): one, or two for a spread. */
const folios = ref<number[]>([])
const isSpread = ref(false)

let book: Book | null = null
let rendition: Rendition | null = null
let lastLocation: Location | null = null
let toc: TocItem[] = []

const MIN_SPREAD_WIDTH = 960
const swipe = createSwipe((direction) => emit('turn', direction))

/** Tap the left/right edge of the page to turn it (ignoring links and text selection). */
function onTap(event: MouseEvent) {
  const view = event.view as Window | null
  if ((event.target as Element | null)?.closest?.('a')) return
  if (view?.getSelection()?.toString()) return
  if (!viewer.value) return
  // Event coordinates are relative to the book's iframe; convert them to the main window's.
  const frame = view?.frameElement?.getBoundingClientRect()
  const zone = tapZone(event.clientX + (frame?.left ?? 0), viewer.value.getBoundingClientRect())
  if (zone) emit('turn', zone)
}

function flattenToc(items: NavItem[], depth = 0): TocItem[] {
  return items.flatMap((item) => [
    { id: item.id || item.href, label: item.label.trim(), depth, target: item.href },
    ...flattenToc(item.subitems ?? [], depth + 1),
  ])
}

// --- Page numbers -------------------------------------------------------------------------
// EPUBs have no fixed pages: text reflows to the screen. So the whole book is split into
// chunks holding as much text as one page shows at the current font size and screen size
// (epub.js "locations"), and chunk N is page N. They're recounted when the layout changes.

/** Page boundaries in reading order: page N ends at pageEnds[N - 1]. Empty until counted. */
let pageEnds: string[] = []
let countedLayout = '' // font size / spread / page size the count was made for
let countedBreak = 0 // characters per page used for that count
let refined = false // measured on a page full of real text (not e.g. a cover)
let countToken = 0
let counting = Promise.resolve()
const cfi = new EpubCFI()

/** epub.js keeps its locations list private; page counting needs to read and reset it. */
const locationList = (): string[] =>
  (book?.locations as unknown as { _locations?: string[] } | undefined)?._locations ?? []

// Ordinary prose used to measure how much text fits on a page in the book's own styling.
const SAMPLE_TEXT =
  'It was late in the evening when the travellers reached the old house at the end of the ' +
  'road. The windows were dark, and a thin rain had begun to fall, but the door opened at ' +
  'the first knock, and a woman with a lamp asked them in. They sat by the fire for a long ' +
  'time without speaking, listening to the wind in the chimney and the slow tick of a clock ' +
  'somewhere in the hall. Later, when the others had gone to bed, she told them what she ' +
  'knew about the valley, and why so few people came that way any more. '

/**
 * Characters that fit on one page: lay out a hidden paragraph of sample prose in the book's
 * page column (same font, size and width) and scale its height to the page height.
 */
function measureCharsPerPage(doc: Document): number | null {
  // epub.js lays each chapter out as CSS columns on <body>, one column per page.
  const body = doc.body
  const style = getComputedStyle(body)
  const columnWidth = parseFloat(style.columnWidth)
  const pageHeight =
    body.clientHeight - parseFloat(style.paddingTop || '0') - parseFloat(style.paddingBottom || '0')
  if (!(columnWidth > 0) || !(pageHeight > 0)) return null

  const probe = doc.createElement('p')
  probe.textContent = SAMPLE_TEXT.repeat(4)
  probe.style.cssText = `position:absolute;visibility:hidden;left:0;top:0;margin:0;width:${columnWidth}px`
  doc.body.appendChild(probe)
  const height = probe.getBoundingClientRect().height
  probe.remove()
  if (!(height > 0)) return null
  // Real chapters hold less than solid prose (paragraph ends, dialogue, headings): roughly
  // 75–85% in testing, so this is only the opening estimate (see measureChapter).
  return ((probe.textContent.length * pageHeight) / height) * 0.8
}

/** Characters epub.js counts in a document (text nodes that aren't only whitespace). */
function countedChars(doc: Document): number {
  let total = 0
  const walker = doc.createTreeWalker(doc.body, NodeFilter.SHOW_TEXT)
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (node.textContent?.trim()) total += node.textContent.length
  }
  return total
}

/**
 * The book's real density: characters per page in the chapter on screen, if it's a chapter
 * long enough to be representative (not a cover or title page).
 */
function measureChapter(location: Location, doc: Document): number | null {
  const pages = location.start.displayed?.total ?? 0
  const chars = countedChars(doc)
  return pages >= 4 && chars > 4000 ? chars / pages : null
}

/** Cached page counts per book, so reopening a book shows numbers straight away. */
const CACHE_PREFIX = 'pages:'
const CACHE_LAYOUTS_PER_BOOK = 3

function loadCachedPages(breakAt: number): string | null {
  try {
    const cached = JSON.parse(localStorage.getItem(CACHE_PREFIX + props.url) ?? '{}')
    return cached[breakAt] ?? null
  } catch {
    return null
  }
}

function saveCachedPages(breakAt: number, locations: string) {
  const key = CACHE_PREFIX + props.url
  try {
    const cached: Record<string, string> = JSON.parse(localStorage.getItem(key) ?? '{}')
    cached[breakAt] = locations
    // Keep only the latest few layouts (e.g. portrait and landscape).
    const keep = Object.keys(cached).slice(-CACHE_LAYOUTS_PER_BOOK)
    localStorage.setItem(key, JSON.stringify(Object.fromEntries(keep.map((k) => [k, cached[k]]))))
  } catch {
    // Storage full or unavailable: pages just get recounted next time.
  }
}

function layoutKey() {
  const el = viewer.value
  return `${props.fontSize}|${isSpread.value}|${el?.clientWidth}x${el?.clientHeight}`
}

/** Snap to 3% steps so small measurement noise reuses the same count (and cache entry). */
function snap(chars: number): number {
  const step = Math.round(Math.log(chars / 150) / Math.log(1.03))
  return Math.round(150 * 1.03 ** step)
}

function recountIfNeeded(location: Location) {
  if (!book) return
  const key = layoutKey()
  if (key === countedLayout && refined) return
  const all = rendition?.getContents() as unknown as Contents[] | undefined
  const doc = (all?.find((c) => c.sectionIndex === location.start.index) ?? all?.[0])?.document
  if (!doc) return
  const fromChapter = measureChapter(location, doc)
  const measured = fromChapter ?? measureCharsPerPage(doc)
  if (!measured) return
  const breakAt = snap(Math.min(Math.max(measured, 150), 6000))

  if (key === countedLayout) {
    // Same layout: once a real chapter is on screen, correct the estimate if it was off.
    if (!fromChapter) return
    refined = true
    if (Math.abs(breakAt - countedBreak) / countedBreak < 0.06) return
  } else {
    countedLayout = key
    refined = fromChapter !== null
    pageEnds = [] // a different layout: old numbers no longer apply
    reportProgress()
  }
  countedBreak = breakAt
  const token = ++countToken
  // Counts run one at a time; a newer request makes older queued ones skip. While a count
  // runs, the previous page numbers (if any) stay on screen.
  counting = counting.then(async () => {
    if (token !== countToken || !book) return
    const cached = loadCachedPages(breakAt)
    if (cached) {
      book.locations.load(cached)
    } else {
      locationList().length = 0 // epub.js appends to existing locations
      await book.locations.generate(breakAt)
      if (token !== countToken) return
      saveCachedPages(breakAt, book.locations.save())
    }
    pageEnds = [...locationList()]
    emit('toc', withPages(toc))
    reportProgress()
  })
}

/** 1-based page containing a position: the first page whose end is at or after it. */
function pageOf(position: string): number {
  let low = 0
  let high = pageEnds.length
  while (low < high) {
    const mid = (low + high) >> 1
    if (cfi.compare(pageEnds[mid]!, position) < 0) low = mid + 1
    else high = mid
  }
  return Math.min(low, pageEnds.length - 1) + 1
}

/** Page on which each contents entry's chapter starts. */
function withPages(items: TocItem[]): TocItem[] {
  if (!book || !pageEnds.length) return items
  const starts = pageEnds.map((end) => new EpubCFI(end).spinePos)
  return items.map((item) => {
    const section = book!.spine.get(String(item.target))
    if (!section) return item
    const index = starts.findIndex((spinePos) => spinePos >= section.index)
    return { ...item, page: (index === -1 ? starts.length - 1 : index) + 1 }
  })
}

function reportProgress() {
  if (!book || !lastLocation) return
  const { start } = lastLocation
  const chapter = book.navigation?.get(start.href)?.label?.trim()
  if (!pageEnds.length) {
    folios.value = []
    emit('progress', {
      fraction: null,
      label: [chapter, 'Counting pages…'].filter(Boolean).join(' · '),
    })
    return
  }
  const total = pageEnds.length
  const page = pageOf(start.cfi)
  folios.value = isSpread.value ? [page, Math.min(page + 1, total)] : [page]
  const pages = isSpread.value && page < total ? `Pages ${page}–${page + 1}` : `Page ${page}`
  emit('progress', {
    fraction: total > 1 ? (page - 1) / (total - 1) : 0,
    label: [chapter, `${pages} of ${total}`].filter(Boolean).join(' · '),
  })
}

function onRelocated(location: Location) {
  lastLocation = location
  isSpread.value = !props.singlePage && (viewer.value?.clientWidth ?? 0) >= MIN_SPREAD_WIDTH
  recountIfNeeded(location)
  reportProgress()
}

/** After a layout change (font size, rotation), recheck once epub.js has re-laid the page. */
let layoutTimer: ReturnType<typeof setTimeout> | undefined
function afterLayoutChange() {
  clearTimeout(layoutTimer)
  layoutTimer = setTimeout(() => {
    const location = rendition?.currentLocation() as unknown as Location | undefined
    if (location?.start) onRelocated(location)
  }, 400)
}

onMounted(async () => {
  try {
    const response = await fetch(props.url)
    if (!response.ok) throw new Error(`Could not load book (${response.status})`)
    book = ePub(await response.arrayBuffer())

    rendition = book.renderTo(viewer.value!, {
      width: '100%',
      height: '100%',
      flow: 'paginated',
      spread: props.singlePage ? 'none' : 'auto',
      minSpreadWidth: MIN_SPREAD_WIDTH,
      allowScriptedContent: false,
    })
    rendition.themes.default({
      body: {
        color: `${INK} !important`,
        background: 'transparent !important',
        'font-family': "'Literata', Georgia, 'Iowan Old Style', 'Palatino Linotype', serif",
        'line-height': '1.65',
      },
      p: { 'text-align': 'justify', hyphens: 'auto' },
      a: { color: '#7a4b1e' },
      img: { 'mix-blend-mode': 'multiply' },
    })
    rendition.themes.fontSize(`${props.fontSize}%`)
    rendition.on('relocated', onRelocated)
    rendition.on('resized', afterLayoutChange)
    // Key presses inside the book's iframe don't reach the window, so forward them.
    rendition.on('keydown', (event: KeyboardEvent) => emit('key', event))
    // Touches and clicks also happen inside the iframe; use them to turn pages.
    rendition.on('touchstart', swipe.start)
    rendition.on('touchend', swipe.end)
    rendition.on('click', onTap)

    await rendition.display()
    const navigation = await book.loaded.navigation
    toc = flattenToc(navigation.toc)
    emit('ready', withPages(toc))
  } catch (e) {
    emit('error', (e as Error).message || 'This EPUB could not be opened')
  }
})

watch(
  () => props.singlePage,
  (single) => {
    rendition?.spread(single ? 'none' : 'auto', MIN_SPREAD_WIDTH)
    afterLayoutChange()
  },
)

watch(
  () => props.fontSize,
  (size) => {
    rendition?.themes.fontSize(`${size}%`)
    afterLayoutChange()
  },
)

onBeforeUnmount(() => {
  clearTimeout(layoutTimer)
  countToken++ // stop any queued page count
  book?.destroy()
})

defineExpose<ReaderHandle>({
  next: () => rendition?.next(),
  prev: () => rendition?.prev(),
  goTo: (target) => rendition?.display(String(target)),
})
</script>

<template>
  <div class="epub">
    <div ref="viewer" class="epub-viewer"></div>
    <div class="folios" :class="{ spread: isSpread }">
      <span v-for="(page, i) in folios" :key="i">{{ page }}</span>
    </div>
  </div>
</template>

<style scoped>
.epub {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}
.epub-viewer {
  flex: 1;
  min-height: 0;
  width: 100%;
}
/* Printed-book style page numbers under each page. */
.folios {
  display: flex;
  height: 1.4rem;
  align-items: center;
  font-size: 0.8rem;
  font-variant-numeric: oldstyle-nums;
  color: #8a7a63;
}
.folios span {
  flex: 1;
  text-align: center;
}
</style>

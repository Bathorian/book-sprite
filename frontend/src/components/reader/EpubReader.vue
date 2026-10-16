<script setup lang="ts">
import { onBeforeUnmount, onMounted, useTemplateRef, watch } from 'vue'
import ePub, { type Book, type Location, type NavItem, type Rendition } from 'epubjs'
import { INK, type ReaderHandle, type ReaderProgress, type TocItem } from './types'

const props = defineProps<{ url: string; fontSize: number }>()
const emit = defineEmits<{
  ready: [toc: TocItem[]]
  progress: [progress: ReaderProgress]
  error: [message: string]
  key: [event: KeyboardEvent]
  pointer: [clientX: number, clientY: number]
}>()

const viewer = useTemplateRef<HTMLDivElement>('viewer')
let book: Book | null = null
let rendition: Rendition | null = null
let lastLocation: Location | null = null

function flattenToc(items: NavItem[], depth = 0): TocItem[] {
  return items.flatMap((item) => [
    { id: item.id || item.href, label: item.label.trim(), depth, target: item.href },
    ...flattenToc(item.subitems ?? [], depth + 1),
  ])
}

function reportProgress() {
  if (!book || !lastLocation) return
  const { start } = lastLocation
  const fraction = book.locations.length() ? book.locations.percentageFromCfi(start.cfi) : null
  const chapter = book.navigation?.get(start.href)?.label?.trim()
  const page = start.displayed ? `Page ${start.displayed.page} of ${start.displayed.total}` : ''
  emit('progress', { fraction, label: [chapter, page].filter(Boolean).join(' · ') })
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
      spread: 'auto',
      minSpreadWidth: 960,
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
    rendition.on('relocated', (location: Location) => {
      lastLocation = location
      reportProgress()
    })
    // Key presses inside the book's iframe don't reach the window, so forward them.
    rendition.on('keydown', (event: KeyboardEvent) => emit('key', event))
    // Same for mouse moves; translate iframe coordinates into the main window's.
    rendition.on('mousemove', (event: MouseEvent) => {
      const frame = (event.view as Window | null)?.frameElement?.getBoundingClientRect()
      emit('pointer', event.clientX + (frame?.left ?? 0), event.clientY + (frame?.top ?? 0))
    })

    await rendition.display()
    const navigation = await book.loaded.navigation
    emit('ready', flattenToc(navigation.toc))

    // Book-wide percentages need a full pass over the text; do it in the background.
    await book.locations.generate(1600)
    reportProgress()
  } catch (e) {
    emit('error', (e as Error).message || 'This EPUB could not be opened')
  }
})

watch(
  () => props.fontSize,
  (size) => rendition?.themes.fontSize(`${size}%`),
)

onBeforeUnmount(() => book?.destroy())

defineExpose<ReaderHandle>({
  next: () => rendition?.next(),
  prev: () => rendition?.prev(),
  goTo: (target) => rendition?.display(String(target)),
})
</script>

<template>
  <div ref="viewer" class="epub-viewer"></div>
</template>

<style scoped>
.epub-viewer {
  width: 100%;
  height: 100%;
}
</style>

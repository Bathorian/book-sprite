<script setup lang="ts">
import {
  computed,
  defineAsyncComponent,
  onBeforeUnmount,
  onMounted,
  ref,
  useTemplateRef,
  watch,
} from 'vue'
import { RouterLink } from 'vue-router'
import { fileUrl, getBook, type Book } from '@/api/books'
import type { ReaderHandle, ReaderProgress, TocItem } from '@/components/reader/types'
import ReadingCompanion from '@/components/reader/ReadingCompanion.vue'
import { warrior } from '@/companions'
import type { TurnDirection } from '@/components/reader/swipe'
import { useMediaQuery } from '@/composables/useMediaQuery'

// Each format's engine is large, so only download the one this book needs.
const EpubReader = defineAsyncComponent(() => import('@/components/reader/EpubReader.vue'))
const PdfReader = defineAsyncComponent(() => import('@/components/reader/PdfReader.vue'))

const props = defineProps<{ id: number }>()

const book = ref<Book | null>(null)
const error = ref<string | null>(null)
const ready = ref(false)
const toc = ref<TocItem[]>([])
const tocOpen = ref(false)
const progress = ref<ReaderProgress>({ fraction: null, label: '' })
const reader = useTemplateRef<ReaderHandle>('reader')
const companion = useTemplateRef<InstanceType<typeof ReadingCompanion>>('companion')

// Text size (EPUB, percent) and zoom (PDF), remembered between visits.
const FONT_SIZES = [80, 90, 100, 110, 120, 135, 150, 170, 200]
const ZOOMS = [1, 1.25, 1.5, 2, 2.5, 3]
const fontIndex = ref(loadSetting('reader.fontIndex', 2, FONT_SIZES.length))
const zoomIndex = ref(0)
const isPdf = computed(() => book.value?.format === 'pdf')

function loadSetting(key: string, fallback: number, length: number): number {
  try {
    const raw = localStorage.getItem(key)
    if (raw === null) return fallback
    const value = Number(raw)
    return Number.isInteger(value) && value >= 0 && value < length ? value : fallback
  } catch {
    return fallback
  }
}

watch(fontIndex, (value) => {
  try {
    localStorage.setItem('reader.fontIndex', String(value))
  } catch {
    // Storage unavailable (private mode); the setting just won't persist.
  }
})

function smaller() {
  if (isPdf.value) zoomIndex.value = Math.max(0, zoomIndex.value - 1)
  else fontIndex.value = Math.max(0, fontIndex.value - 1)
}

function larger() {
  if (isPdf.value) zoomIndex.value = Math.min(ZOOMS.length - 1, zoomIndex.value + 1)
  else fontIndex.value = Math.min(FONT_SIZES.length - 1, fontIndex.value + 1)
}

// Reading companion: on by default, remembered between visits.
const companionOn = ref(loadSetting('reader.companion', 1, 2) === 1)

// Screen-size rules, re-evaluated when a phone is rotated.
// Phones (narrow, or short when held sideways) always get one page at a time.
const singlePage = useMediaQuery('(max-width: 700px), (max-height: 500px)')
const shortScreen = useMediaQuery('(max-height: 500px)')
const smallScreen = useMediaQuery('(max-width: 640px), (max-height: 700px)')
const companionHeight = computed(() => (shortScreen.value ? 48 : smallScreen.value ? 72 : 96))

watch(companionOn, (on) => {
  try {
    localStorage.setItem('reader.companion', on ? '1' : '0')
  } catch {
    // Storage unavailable; the setting just won't persist.
  }
})

function next() {
  reader.value?.next()
  companion.value?.react()
}

function prev() {
  reader.value?.prev()
  companion.value?.react()
}

/** Swipes and edge taps from inside the book. */
function onTurn(direction: TurnDirection) {
  if (direction === 'next') next()
  else prev()
}

function onReady(items: TocItem[]) {
  toc.value = items
  ready.value = true
}

function jump(item: TocItem) {
  reader.value?.goTo(item.target)
  tocOpen.value = false
}

function onKey(event: KeyboardEvent) {
  if (event.target instanceof HTMLInputElement) return
  if (event.key === 'ArrowRight' || event.key === 'PageDown' || event.key === ' ') {
    event.preventDefault()
    next()
  } else if (event.key === 'ArrowLeft' || event.key === 'PageUp') {
    event.preventDefault()
    prev()
  } else if (event.key === 'Escape') {
    tocOpen.value = false
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  try {
    book.value = await getBook(props.id)
    document.title = `${book.value.title} · BookSprite`
  } catch (e) {
    error.value = (e as Error).message
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKey)
  document.title = 'BookSprite'
})
</script>

<template>
  <div class="reader">
    <header class="bar">
      <RouterLink to="/" class="icon-btn" aria-label="Back to library" title="Library">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
      </RouterLink>
      <button
        v-if="toc.length"
        class="icon-btn"
        aria-label="Table of contents"
        title="Contents"
        @click="tocOpen = !tocOpen"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h10" /></svg>
      </button>
      <div class="heading">
        <span class="title">{{ book?.title }}</span>
        <span v-if="book?.author" class="author">{{ book.author }}</span>
      </div>
      <button
        class="icon-btn"
        :class="{ active: companionOn }"
        :aria-pressed="companionOn"
        aria-label="Reading companion"
        :title="companionOn ? 'Hide companion' : 'Show companion'"
        @click="companionOn = !companionOn"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="6" r="2.5" />
          <path d="M12 9v7M8 12h8M12 16l-3 5M12 16l3 5M18 3v18" />
        </svg>
      </button>
      <div class="size">
        <button class="text-btn" :aria-label="isPdf ? 'Zoom out' : 'Smaller text'" @click="smaller">
          A<span class="small">−</span>
        </button>
        <button class="text-btn" :aria-label="isPdf ? 'Zoom in' : 'Larger text'" @click="larger">
          A<span class="small">+</span>
        </button>
      </div>
    </header>

    <main class="stage">
      <button class="turn prev" aria-label="Previous page" @click="prev">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
      </button>

      <div class="page">
        <p v-if="error" class="status">{{ error }}</p>
        <template v-else-if="book">
          <EpubReader
            v-if="book.format === 'epub'"
            ref="reader"
            :url="fileUrl(book.id)"
            :font-size="FONT_SIZES[fontIndex]!"
            :single-page="singlePage"
            @ready="onReady"
            @progress="progress = $event"
            @error="error = $event"
            @key="onKey"
            @turn="onTurn"
            @toc="toc = $event"
          />
          <PdfReader
            v-else
            ref="reader"
            :url="fileUrl(book.id)"
            :zoom="ZOOMS[zoomIndex]!"
            @ready="onReady"
            @progress="progress = $event"
            @error="error = $event"
            @turn="onTurn"
          />
        </template>
        <p v-if="!ready && !error" class="status loading">Opening book…</p>
      </div>

      <button class="turn next" aria-label="Next page" @click="next">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7" /></svg>
      </button>
    </main>

    <footer class="foot">
      <div v-if="companionOn" class="lane" :style="{ height: `${companionHeight}px` }">
        <ReadingCompanion ref="companion" :sprite="warrior" :height="companionHeight" />
      </div>
      <div class="track" aria-hidden="true">
        <div class="fill" :style="{ width: `${(progress.fraction ?? 0) * 100}%` }"></div>
      </div>
      <span class="where">{{ progress.label }}</span>
      <span v-if="progress.fraction !== null" class="percent">
        {{ Math.round(progress.fraction * 100) }}%
      </span>
    </footer>

    <div v-if="tocOpen" class="scrim" @click="tocOpen = false"></div>
    <nav class="toc" :class="{ open: tocOpen }" aria-label="Table of contents">
      <h2>Contents</h2>
      <ul>
        <li v-for="item in toc" :key="item.id">
          <button :style="{ paddingLeft: `${0.75 + item.depth * 1}rem` }" @click="jump(item)">
            <span class="toc-label">{{ item.label }}</span>
            <span v-if="item.page" class="toc-page">{{ item.page }}</span>
          </button>
        </li>
      </ul>
    </nav>
  </div>
</template>

<style scoped>
.reader {
  --paper: #f4ecd8;
  --paper-edge: #e9dec3;
  --ink: #3b3024;
  --ink-soft: #8a7a63;
  --rule: rgb(59 48 36 / 0.12);

  position: fixed;
  inset: 0;
  display: grid;
  grid-template-rows: auto 1fr auto;
  color: var(--ink);
  /* Warm paper with a faint darker edge, like a page under a lamp. */
  background:
    radial-gradient(ellipse at center, transparent 55%, rgb(120 90 40 / 0.1) 100%), var(--paper);
  font-family: 'Literata', Georgia, 'Iowan Old Style', 'Palatino Linotype', serif;
  color-scheme: light;
}

.bar {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0.75rem;
  padding-top: calc(0.5rem + env(safe-area-inset-top, 0px));
}
.heading {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.25;
  text-align: center;
}
.title {
  max-width: 100%;
  font-size: 0.95rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.author {
  font-size: 0.8rem;
  font-style: italic;
  color: var(--ink-soft);
}
.size {
  display: flex;
  gap: 0.15rem;
}

.icon-btn,
.text-btn,
.turn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--ink-soft);
  border-radius: 6px;
  cursor: pointer;
  text-decoration: none;
  transition:
    color 0.15s,
    background 0.15s;
}
.icon-btn:hover,
.text-btn:hover,
.turn:hover {
  color: var(--ink);
  background: rgb(59 48 36 / 0.06);
}
.icon-btn.active {
  color: var(--ink);
}
.icon-btn {
  width: 2.25rem;
  height: 2.25rem;
  padding: 0;
}
.text-btn {
  height: 2.25rem;
  padding: 0 0.6rem;
  font-family: inherit;
  font-size: 1rem;
}
.text-btn .small {
  font-size: 0.75em;
  margin-left: 1px;
}
svg {
  width: 1.3rem;
  height: 1.3rem;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.stage {
  display: grid;
  grid-template-columns: 3.5rem 1fr 3.5rem;
  min-height: 0;
}
.page {
  position: relative;
  min-width: 0;
  min-height: 0;
  width: 100%;
  max-width: 72rem;
  justify-self: center;
  padding-block: 1rem;
}
.turn {
  height: 100%;
  width: 100%;
  border-radius: 0;
  opacity: 0.55;
}
.turn:hover {
  opacity: 1;
}
.status {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0;
  padding: 2rem;
  text-align: center;
  font-style: italic;
  color: var(--ink-soft);
}
.loading {
  background: var(--paper);
}

.foot {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 0.35rem 1rem;
  padding: 0.4rem 1.25rem 0.75rem;
  padding-bottom: calc(0.75rem + env(safe-area-inset-bottom, 0px));
  font-size: 0.78rem;
  color: var(--ink-soft);
}
.where {
  /* Reserve the line even while empty, so the page doesn't resize when text appears. */
  min-height: 1.5em;
  line-height: 1.5;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.percent {
  font-variant-numeric: tabular-nums;
}
.lane {
  grid-column: 1 / -1;
  /* Let the companion stand right on the progress line. */
  margin-bottom: -0.35rem;
}
.track {
  grid-column: 1 / -1;
  height: 2px;
  background: var(--rule);
  border-radius: 1px;
}
.fill {
  height: 100%;
  background: var(--ink-soft);
  border-radius: 1px;
  transition: width 0.3s;
}

.scrim {
  position: fixed;
  inset: 0;
  background: rgb(40 30 15 / 0.2);
  z-index: 20;
}
.toc {
  position: fixed;
  top: 0;
  bottom: 0;
  left: 0;
  width: min(22rem, 85vw);
  padding: 1.25rem 0;
  padding-top: calc(1.25rem + env(safe-area-inset-top, 0px));
  background: var(--paper-edge);
  box-shadow: 2px 0 18px rgb(40 30 15 / 0.18);
  overflow-y: auto;
  transform: translateX(-105%);
  transition: transform 0.2s ease;
  z-index: 21;
}
.toc.open {
  transform: none;
}
.toc h2 {
  margin: 0 1.25rem 0.75rem;
  font-size: 1.05rem;
  font-weight: 600;
}
.toc ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.toc button {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  width: 100%;
  padding: 0.45rem 1.25rem;
  border: none;
  background: none;
  color: var(--ink);
  font-family: inherit;
  font-size: 0.92rem;
  text-align: left;
  cursor: pointer;
}
.toc button:hover {
  background: rgb(59 48 36 / 0.07);
}
/* Dotted leader between the title and its page number, as in a printed contents page. */
.toc-label {
  display: flex;
  flex: 1;
  min-width: 0;
  gap: 0.4rem;
}
.toc-label::after {
  content: '';
  flex: 1;
  min-width: 1rem;
  border-bottom: 1px dotted rgb(59 48 36 / 0.3);
  transform: translateY(-0.3em);
}
.toc-page {
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
  color: var(--ink-soft);
}

@media (max-width: 640px) {
  .stage {
    grid-template-columns: 2.25rem 1fr 2.25rem;
  }
  .page {
    padding-block: 0.5rem;
  }
}

/* Touch screens: pages turn by swiping or tapping the edges, so the arrow columns go and
   the text gets the full width. Buttons grow to comfortable tap size (44px). */
@media (hover: none) and (pointer: coarse) {
  .stage {
    grid-template-columns: 0.5rem 1fr 0.5rem;
  }
  .turn {
    visibility: hidden;
  }
  .icon-btn {
    width: 2.75rem;
    height: 2.75rem;
  }
  .text-btn {
    height: 2.75rem;
  }
}

/* Phones held sideways: very little height, so slim everything around the page. */
@media (max-height: 500px) {
  .bar {
    padding-block: 0.15rem;
    padding-top: calc(0.15rem + env(safe-area-inset-top, 0px));
  }
  .author {
    display: none;
  }
  .page {
    padding-block: 0.25rem;
  }
  .foot {
    gap: 0.15rem 1rem;
    padding-top: 0.15rem;
    padding-bottom: calc(0.3rem + env(safe-area-inset-bottom, 0px));
  }
}

/* Notched phones in landscape: keep the page clear of the notch. */
.reader {
  padding-left: env(safe-area-inset-left, 0px);
  padding-right: env(safe-area-inset-right, 0px);
}
</style>

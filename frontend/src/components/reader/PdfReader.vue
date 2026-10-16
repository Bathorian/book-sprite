<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue'
import * as pdfjs from 'pdfjs-dist'
import type { PDFDocumentLoadingTask, PDFDocumentProxy, RenderTask } from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import type { ReaderHandle, ReaderProgress, TocItem } from './types'

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl

const props = defineProps<{ url: string; zoom: number }>()
const emit = defineEmits<{
  ready: [toc: TocItem[]]
  progress: [progress: ReaderProgress]
  error: [message: string]
}>()

const container = useTemplateRef<HTMLDivElement>('container')
const canvas = useTemplateRef<HTMLCanvasElement>('canvas')
const pageNumber = ref(1)
const pageCount = ref(0)

let loadingTask: PDFDocumentLoadingTask | null = null
let doc: PDFDocumentProxy | null = null
let renderTask: RenderTask | null = null
let resizeObserver: ResizeObserver | null = null

type OutlineNode = Awaited<ReturnType<PDFDocumentProxy['getOutline']>>[number]

async function resolvePage(dest: OutlineNode['dest']): Promise<number | null> {
  if (!doc || !dest) return null
  try {
    const explicit = typeof dest === 'string' ? await doc.getDestination(dest) : dest
    const ref = explicit?.[0]
    if (ref == null) return null
    const index = typeof ref === 'number' ? ref : await doc.getPageIndex(ref)
    return index + 1
  } catch {
    return null
  }
}

async function buildToc(nodes: OutlineNode[], depth = 0): Promise<TocItem[]> {
  const items: TocItem[] = []
  for (const [i, node] of nodes.entries()) {
    const page = await resolvePage(node.dest)
    if (page) items.push({ id: `${depth}-${i}-${page}`, label: node.title, depth, target: page })
    items.push(...(await buildToc(node.items ?? [], depth + 1)))
  }
  return items
}

async function render() {
  if (!doc || !container.value || !canvas.value) return
  const page = await doc.getPage(pageNumber.value)
  const base = page.getViewport({ scale: 1 })
  const box = container.value.getBoundingClientRect()
  // Fit the whole page in view at zoom 1; larger zooms scroll.
  const fit = Math.min(box.width / base.width, box.height / base.height)
  const viewport = page.getViewport({ scale: fit * props.zoom })
  const ratio = window.devicePixelRatio || 1

  renderTask?.cancel()
  const el = canvas.value
  el.width = Math.floor(viewport.width * ratio)
  el.height = Math.floor(viewport.height * ratio)
  el.style.width = `${Math.floor(viewport.width)}px`
  el.style.height = `${Math.floor(viewport.height)}px`

  renderTask = page.render({
    canvas: el,
    viewport,
    transform: ratio === 1 ? undefined : [ratio, 0, 0, ratio, 0, 0],
  })
  try {
    await renderTask.promise
  } catch (e) {
    if ((e as Error).name !== 'RenderingCancelledException') throw e
  }
  emit('progress', {
    fraction: pageNumber.value / pageCount.value,
    label: `Page ${pageNumber.value} of ${pageCount.value}`,
  })
}

function goTo(target: string | number) {
  const page = Math.min(Math.max(1, Number(target)), pageCount.value)
  if (page !== pageNumber.value) {
    pageNumber.value = page
    container.value?.scrollTo(0, 0)
    render()
  }
}

onMounted(async () => {
  try {
    loadingTask = pdfjs.getDocument({ url: props.url })
    doc = await loadingTask.promise
    pageCount.value = doc.numPages
    await render()
    emit('ready', await buildToc((await doc.getOutline()) ?? []))
    resizeObserver = new ResizeObserver(() => render())
    resizeObserver.observe(container.value!)
  } catch (e) {
    emit('error', (e as Error).message || 'This PDF could not be opened')
  }
})

watch(() => props.zoom, render)

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  renderTask?.cancel()
  loadingTask?.destroy()
})

defineExpose<ReaderHandle>({
  next: () => goTo(pageNumber.value + 1),
  prev: () => goTo(pageNumber.value - 1),
  goTo,
})
</script>

<template>
  <div ref="container" class="pdf-viewer" :class="{ zoomed: zoom > 1 }">
    <canvas ref="canvas"></canvas>
  </div>
</template>

<style scoped>
.pdf-viewer {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.pdf-viewer.zoomed {
  overflow: auto;
  align-items: flex-start;
}
canvas {
  display: block;
  /* Blend the white PDF page into the paper colour behind it. */
  mix-blend-mode: multiply;
  box-shadow: 0 0 0 1px rgb(59 48 36 / 0.06);
}
</style>

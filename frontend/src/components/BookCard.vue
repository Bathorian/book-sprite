<script setup lang="ts">
import { ref } from 'vue'
import { RouterLink } from 'vue-router'
import { coverUrl, type Book } from '@/api/books'

const props = defineProps<{ book: Book }>()
const emit = defineEmits<{ edit: [book: Book]; delete: [book: Book] }>()

const coverFailed = ref(false)
const confirmingDelete = ref(false)

// Deterministic placeholder colour per book.
const hue = [...props.book.title].reduce((acc, ch) => (acc * 31 + ch.charCodeAt(0)) % 360, 7)

// Mouse-follow tilt. Written straight to CSS variables (not reactive state) and
// batched per animation frame, so moving the mouse never re-renders the component.
const MAX_TILT = 12 // degrees
let frame = 0

function onPointerMove(event: PointerEvent) {
  if (event.pointerType === 'touch') return
  const el = event.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  const x = (event.clientX - rect.left) / rect.width // 0..1
  const y = (event.clientY - rect.top) / rect.height
  cancelAnimationFrame(frame)
  frame = requestAnimationFrame(() => {
    el.classList.add('tilting')
    el.style.setProperty('--ry', `${(x - 0.5) * 2 * MAX_TILT}deg`)
    el.style.setProperty('--rx', `${(0.5 - y) * 2 * MAX_TILT}deg`)
    el.style.setProperty('--gx', `${x * 100}%`)
    el.style.setProperty('--gy', `${y * 100}%`)
  })
}

function onPointerLeave(event: PointerEvent) {
  cancelAnimationFrame(frame)
  const el = event.currentTarget as HTMLElement
  el.classList.remove('tilting')
  el.style.setProperty('--rx', '0deg')
  el.style.setProperty('--ry', '0deg')
}
</script>

<template>
  <article class="card">
    <RouterLink
      :to="{ name: 'reader', params: { id: book.id } }"
      class="open"
      :title="`Read ${book.title}`"
    >
      <div class="cover" @pointermove="onPointerMove" @pointerleave="onPointerLeave">
        <img
          v-if="book.has_cover && !coverFailed"
          :src="coverUrl(book.id)"
          :alt="`Cover of ${book.title}`"
          loading="lazy"
          @error="coverFailed = true"
        />
        <div v-else class="placeholder" :style="{ '--hue': hue }">
          <span>{{ book.title }}</span>
        </div>
        <span class="format">{{ book.format.toUpperCase() }}</span>
        <span class="glare" aria-hidden="true"></span>
      </div>

      <div class="info">
        <h3 class="title" :title="book.title">{{ book.title }}</h3>
        <p class="author">{{ book.author ?? 'Unknown author' }}</p>
      </div>
    </RouterLink>

    <div v-if="confirmingDelete" class="actions">
      <span>Delete?</span>
      <button class="danger" @click="emit('delete', book)">Yes</button>
      <button @click="confirmingDelete = false">No</button>
    </div>
    <div v-else class="actions">
      <button @click="emit('edit', book)">Edit</button>
      <button @click="confirmingDelete = true">Delete</button>
    </div>
  </article>
</template>

<style scoped>
.card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  min-width: 0;
}
.open {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  color: inherit;
  text-decoration: none;
}
.open:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
  border-radius: 6px;
}
.cover {
  --rx: 0deg;
  --ry: 0deg;
  --gx: 50%;
  --gy: 50%;
  position: relative;
  aspect-ratio: 2 / 3;
  border-radius: 6px;
  overflow: hidden;
  background: var(--surface);
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.15);
  transform: perspective(700px) rotateX(var(--rx)) rotateY(var(--ry));
  /* Slow ease back to flat when the mouse leaves. */
  transition:
    transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1),
    box-shadow 0.5s ease;
  will-change: transform;
}
.cover.tilting {
  /* Follow the mouse closely while hovering. */
  transition:
    transform 0.08s linear,
    box-shadow 0.2s ease;
  transform: perspective(700px) rotateX(var(--rx)) rotateY(var(--ry)) scale(1.04);
  /* Shadow falls away from the raised edge. */
  box-shadow:
    calc(var(--ry) * -0.8) calc(var(--rx) * 0.8 + 14px) 28px rgb(0 0 0 / 0.28),
    0 2px 6px rgb(0 0 0 / 0.12);
}
.glare {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(
    circle at var(--gx) var(--gy),
    rgb(255 255 255 / 0.38),
    rgb(255 255 255 / 0.08) 35%,
    transparent 65%
  );
  mix-blend-mode: soft-light;
  opacity: 0;
  transition: opacity 0.3s ease;
}
.cover.tilting .glare {
  opacity: 1;
}
@media (prefers-reduced-motion: reduce) {
  .cover,
  .cover.tilting {
    transform: none;
    transition: box-shadow 0.2s ease;
  }
}
.cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 1rem;
  text-align: center;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(160deg, hsl(var(--hue) 45% 45%), hsl(var(--hue) 45% 28%));
  overflow-wrap: anywhere;
}
.format {
  position: absolute;
  top: 0.4rem;
  right: 0.4rem;
  padding: 0.1rem 0.35rem;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  border-radius: 3px;
  color: #fff;
  background: rgb(0 0 0 / 0.55);
}
.info {
  min-width: 0;
}
.title {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.author {
  margin: 0.15rem 0 0;
  font-size: 0.85rem;
  color: var(--muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.actions {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.8rem;
}
.actions button {
  font-size: 0.8rem;
  padding: 0.2rem 0.55rem;
}
</style>

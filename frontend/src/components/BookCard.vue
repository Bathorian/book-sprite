<script setup lang="ts">
import { ref } from 'vue'
import { coverUrl, type Book } from '@/api/books'

const props = defineProps<{ book: Book }>()
const emit = defineEmits<{ edit: [book: Book]; delete: [book: Book] }>()

const coverFailed = ref(false)
const confirmingDelete = ref(false)

// Deterministic placeholder colour per book.
const hue = [...props.book.title].reduce((acc, ch) => (acc * 31 + ch.charCodeAt(0)) % 360, 7)
</script>

<template>
  <article class="card">
    <div class="cover">
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
    </div>

    <div class="info">
      <h3 class="title" :title="book.title">{{ book.title }}</h3>
      <p class="author">{{ book.author ?? 'Unknown author' }}</p>
    </div>

    <div v-if="confirmingDelete" class="actions confirm">
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
.cover {
  position: relative;
  aspect-ratio: 2 / 3;
  border-radius: 6px;
  overflow: hidden;
  background: var(--surface);
  box-shadow: 0 1px 3px rgb(0 0 0 / 0.15);
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

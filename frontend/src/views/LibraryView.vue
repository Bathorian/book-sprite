<script setup lang="ts">
import { onMounted, ref, useTemplateRef, watch } from 'vue'
import { storeToRefs } from 'pinia'
import type { Book } from '@/api/books'
import BookCard from '@/components/BookCard.vue'
import EditBookDialog from '@/components/EditBookDialog.vue'
import { ACCEPTED_EXTENSIONS, useLibraryStore } from '@/stores/library'

const library = useLibraryStore()
const { books, loading, error, query, sort, uploads } = storeToRefs(library)

const fileInput = useTemplateRef<HTMLInputElement>('fileInput')
const editing = ref<Book | null>(null)
const actionError = ref<string | null>(null)
const dragDepth = ref(0)

onMounted(library.fetchBooks)

let searchTimer: ReturnType<typeof setTimeout> | undefined
watch(query, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(library.fetchBooks, 250)
})
watch(sort, library.fetchBooks)

function onFilesPicked(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) library.uploadFiles(input.files)
  input.value = ''
}

function onDrop(event: DragEvent) {
  dragDepth.value = 0
  const files = event.dataTransfer?.files
  if (files?.length) library.uploadFiles(files)
}

async function onDelete(book: Book) {
  actionError.value = null
  try {
    await library.deleteBook(book.id)
  } catch (e) {
    actionError.value = `Could not delete "${book.title}": ${(e as Error).message}`
  }
}
</script>

<template>
  <section
    class="library"
    @dragenter.prevent="dragDepth++"
    @dragover.prevent
    @dragleave="dragDepth--"
    @drop.prevent="onDrop"
  >
    <div class="toolbar">
      <h2>Library</h2>
      <input
        v-model="query"
        class="search"
        type="search"
        placeholder="Search title or author"
        aria-label="Search books"
      />
      <select v-model="sort" aria-label="Sort books">
        <option value="added">Recently added</option>
        <option value="opened">Recently opened</option>
        <option value="title">Title</option>
        <option value="author">Author</option>
      </select>
      <button class="primary" @click="fileInput?.click()">Upload books</button>
      <input
        ref="fileInput"
        type="file"
        multiple
        :accept="[...ACCEPTED_EXTENSIONS, 'application/epub+zip', 'application/pdf'].join(',')"
        hidden
        @change="onFilesPicked"
      />
    </div>

    <ul v-if="uploads.length" class="uploads">
      <li v-for="u in uploads" :key="u.key" :data-status="u.status">
        <span class="name">{{ u.name }}</span>
        <span class="state">
          {{
            u.status === 'error'
              ? u.message
              : u.status === 'done'
                ? 'Added'
                : u.status === 'uploading'
                  ? 'Uploading…'
                  : 'Waiting…'
          }}
        </span>
      </li>
      <li class="clear"><button @click="library.clearFinishedUploads()">Dismiss</button></li>
    </ul>

    <p v-if="error" class="message error">Could not load library: {{ error }}</p>
    <p v-if="actionError" class="message error">{{ actionError }}</p>

    <div v-if="books.length" class="grid">
      <BookCard
        v-for="book in books"
        :key="book.id"
        :book="book"
        @edit="editing = $event"
        @delete="onDelete"
      />
    </div>
    <div v-else-if="!loading && !error" class="empty">
      <p v-if="query">No books match “{{ query }}”.</p>
      <template v-else>
        <p>Your library is empty.</p>
        <p class="hint">Drop EPUB or PDF files here, or use <strong>Upload books</strong>.</p>
      </template>
    </div>

    <div v-if="dragDepth > 0" class="drop-overlay">Drop EPUB or PDF files to upload</div>

    <EditBookDialog :book="editing" @close="editing = null" />
  </section>
</template>

<style scoped>
.library {
  position: relative;
  min-height: calc(100vh - 6rem);
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 1.25rem;
}
.toolbar h2 {
  margin: 0 auto 0 0;
  font-size: 1.4rem;
}
.search {
  flex: 1 1 14rem;
  max-width: 22rem;
}
.uploads {
  list-style: none;
  margin: 0 0 1.25rem;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  font-size: 0.85rem;
}
.uploads li {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.2rem 0;
}
.uploads .name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.uploads .state {
  flex-shrink: 0;
  color: var(--muted);
}
.uploads [data-status='done'] .state {
  color: var(--ok);
}
.uploads [data-status='error'] .state {
  color: var(--danger);
}
.uploads .clear {
  justify-content: flex-end;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(9.5rem, 1fr));
  gap: 1.5rem 1.25rem;
}
.empty {
  padding: 4rem 1rem;
  text-align: center;
  color: var(--muted);
  border: 2px dashed var(--border);
  border-radius: 10px;
}
.empty p {
  margin: 0.3rem 0;
}
.hint {
  font-size: 0.9rem;
}
.message.error {
  color: var(--danger);
}
.drop-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.3rem;
  font-weight: 600;
  color: var(--accent);
  background: color-mix(in srgb, var(--bg) 85%, transparent);
  border: 3px dashed var(--accent);
  pointer-events: none;
  z-index: 10;
}
</style>

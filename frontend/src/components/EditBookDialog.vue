<script setup lang="ts">
import { ref, watch, useTemplateRef } from 'vue'
import type { Book } from '@/api/books'
import { useLibraryStore } from '@/stores/library'

const props = defineProps<{ book: Book | null }>()
const emit = defineEmits<{ close: [] }>()

const library = useLibraryStore()
const dialog = useTemplateRef<HTMLDialogElement>('dialog')
const title = ref('')
const author = ref('')
const saving = ref(false)
const error = ref<string | null>(null)

watch(
  () => props.book,
  (book) => {
    if (book) {
      title.value = book.title
      author.value = book.author ?? ''
      error.value = null
      dialog.value?.showModal()
    } else {
      dialog.value?.close()
    }
  },
)

async function submit() {
  if (!props.book) return
  if (!title.value.trim()) {
    error.value = 'Title is required'
    return
  }
  saving.value = true
  error.value = null
  try {
    await library.updateBook(props.book.id, { title: title.value, author: author.value || null })
    emit('close')
  } catch (e) {
    error.value = (e as Error).message
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <dialog ref="dialog" class="dialog" @close="emit('close')">
    <form @submit.prevent="submit">
      <h2>Edit book</h2>
      <label>
        Title
        <input v-model="title" required maxlength="500" />
      </label>
      <label>
        Author
        <input v-model="author" maxlength="500" placeholder="Unknown author" />
      </label>
      <p v-if="error" class="error">{{ error }}</p>
      <div class="buttons">
        <button type="button" @click="emit('close')">Cancel</button>
        <button type="submit" class="primary" :disabled="saving">Save</button>
      </div>
    </form>
  </dialog>
</template>

<style scoped>
.dialog {
  width: min(26rem, calc(100vw - 2rem));
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1.25rem;
  background: var(--bg);
  color: var(--text);
}
.dialog::backdrop {
  background: rgb(0 0 0 / 0.4);
}
h2 {
  margin: 0 0 1rem;
  font-size: 1.1rem;
}
label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-bottom: 0.8rem;
  font-size: 0.85rem;
  color: var(--muted);
}
input {
  font: inherit;
  font-size: 0.95rem;
  padding: 0.45rem 0.6rem;
  border: 1px solid var(--border);
  border-radius: 5px;
  background: var(--surface);
  color: var(--text);
}
.error {
  color: var(--danger);
  font-size: 0.85rem;
  margin: 0 0 0.8rem;
}
.buttons {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
</style>

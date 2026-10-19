import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as api from '@/api/books'
import type { Book, BookSort, BookUpdate } from '@/api/books'

type UploadStatus = 'pending' | 'uploading' | 'done' | 'error'

interface UploadItem {
  key: number
  name: string
  status: UploadStatus
  message?: string
}

export const ACCEPTED_EXTENSIONS = ['.epub', '.pdf']

let nextUploadKey = 1

export const useLibraryStore = defineStore('library', () => {
  const books = ref<Book[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const query = ref('')
  const sort = ref<BookSort>('added')
  const uploads = ref<UploadItem[]>([])

  let fetchToken = 0

  async function fetchBooks() {
    const token = ++fetchToken
    loading.value = true
    error.value = null
    try {
      const result = await api.listBooks({ q: query.value.trim() || undefined, sort: sort.value })
      // Ignore responses that arrive after a newer request was started.
      if (token === fetchToken) books.value = result
    } catch (e) {
      if (token === fetchToken) error.value = (e as Error).message
    } finally {
      if (token === fetchToken) loading.value = false
    }
  }

  async function uploadFiles(files: Iterable<File>) {
    const queued = [...files].map((file) => {
      const item: UploadItem = { key: nextUploadKey++, name: file.name, status: 'pending' }
      const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
      if (!ACCEPTED_EXTENSIONS.includes(ext)) {
        item.status = 'error'
        item.message = 'Only EPUB and PDF files are supported'
      }
      uploads.value.push(item)
      return { file, item: uploads.value[uploads.value.length - 1]! }
    })

    let added = 0
    for (const { file, item } of queued) {
      if (item.status === 'error') continue
      item.status = 'uploading'
      try {
        await api.uploadBook(file)
        item.status = 'done'
        added++
      } catch (e) {
        item.status = 'error'
        item.message = (e as Error).message
      }
    }
    if (added) await fetchBooks()
  }

  function clearFinishedUploads() {
    uploads.value = uploads.value.filter((u) => u.status === 'pending' || u.status === 'uploading')
  }

  async function updateBook(id: number, changes: BookUpdate) {
    const updated = await api.updateBook(id, changes)
    const index = books.value.findIndex((b) => b.id === id)
    if (index !== -1) books.value[index] = updated
    return updated
  }

  async function deleteBook(id: number) {
    await api.deleteBook(id)
    books.value = books.value.filter((b) => b.id !== id)
  }

  return {
    books,
    loading,
    error,
    query,
    sort,
    uploads,
    fetchBooks,
    uploadFiles,
    clearFinishedUploads,
    updateBook,
    deleteBook,
  }
})

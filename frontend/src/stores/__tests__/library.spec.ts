import { beforeEach, describe, expect, it, vi, afterEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLibraryStore } from '@/stores/library'

const book = {
  id: 1,
  title: 'Dune',
  author: 'Frank Herbert',
  format: 'epub',
  original_filename: 'dune.epub',
  file_size: 100,
  has_cover: false,
  added_at: '2026-01-01T00:00:00Z',
  last_opened_at: null,
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status })
}

describe('library store', () => {
  beforeEach(() => setActivePinia(createPinia()))
  afterEach(() => vi.unstubAllGlobals())

  it('loads books with search and sort params', async () => {
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(json([book]))
    vi.stubGlobal('fetch', fetchMock)
    const store = useLibraryStore()
    store.query = ' dune '
    store.sort = 'title'
    await store.fetchBooks()
    expect(fetchMock).toHaveBeenCalledWith('/api/books?q=dune&sort=title', undefined)
    expect(store.books).toEqual([book])
  })

  it('rejects unsupported files without uploading them', async () => {
    const fetchMock = vi.fn<typeof fetch>()
    vi.stubGlobal('fetch', fetchMock)
    const store = useLibraryStore()
    await store.uploadFiles([new File(['x'], 'notes.txt')])
    expect(fetchMock).not.toHaveBeenCalled()
    expect(store.uploads[0]).toMatchObject({ status: 'error', name: 'notes.txt' })
  })

  it('uploads files, reports server errors, and refreshes the list', async () => {
    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValueOnce(json(book, 201))
      .mockResolvedValueOnce(
        json({ detail: { message: 'This book is already in your library', book_id: 1 } }, 409),
      )
      .mockResolvedValueOnce(json([book]))
    vi.stubGlobal('fetch', fetchMock)
    const store = useLibraryStore()
    await store.uploadFiles([new File(['a'], 'dune.epub'), new File(['a'], 'copy.EPUB')])
    expect(store.uploads.map((u) => u.status)).toEqual(['done', 'error'])
    expect(store.uploads[1]!.message).toBe('This book is already in your library')
    expect(store.books).toEqual([book])
  })

  it('removes a book after deleting it', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn<typeof fetch>().mockResolvedValue(new Response(null, { status: 204 })),
    )
    const store = useLibraryStore()
    store.books = [book as never]
    await store.deleteBook(1)
    expect(store.books).toEqual([])
  })
})

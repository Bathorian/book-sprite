import { apiFetch } from './client'

export type BookFormat = 'epub' | 'pdf'
export type BookSort = 'added' | 'title' | 'author' | 'opened'

export interface Book {
  id: number
  title: string
  author: string | null
  format: BookFormat
  original_filename: string
  file_size: number
  has_cover: boolean
  added_at: string
  last_opened_at: string | null
}

export interface BookUpdate {
  title?: string
  author?: string | null
}

export function listBooks(params: { q?: string; sort?: BookSort } = {}): Promise<Book[]> {
  const search = new URLSearchParams()
  if (params.q) search.set('q', params.q)
  if (params.sort) search.set('sort', params.sort)
  const qs = search.toString()
  return apiFetch(`/books${qs ? `?${qs}` : ''}`)
}

export function uploadBook(file: File): Promise<Book> {
  const body = new FormData()
  body.append('file', file)
  return apiFetch('/books', { method: 'POST', body })
}

export function updateBook(id: number, changes: BookUpdate): Promise<Book> {
  return apiFetch(`/books/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  })
}

export function deleteBook(id: number): Promise<void> {
  return apiFetch(`/books/${id}`, { method: 'DELETE' })
}

export const coverUrl = (id: number) => `/api/books/${id}/cover`
export const fileUrl = (id: number) => `/api/books/${id}/file`

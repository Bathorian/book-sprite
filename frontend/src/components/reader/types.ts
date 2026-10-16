export interface TocItem {
  id: string
  label: string
  depth: number
  /** EPUB: section href. PDF: 1-based page number. */
  target: string | number
}

export interface ReaderProgress {
  /** 0..1, or null while it is still being calculated. */
  fraction: number | null
  label: string
}

/** Methods every reader component exposes to ReaderView. */
export interface ReaderHandle {
  next(): void
  prev(): void
  goTo(target: string | number): void
}

export const INK = '#3b3024'

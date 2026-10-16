import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia } from 'pinia'
import LibraryView from '@/views/LibraryView.vue'

afterEach(() => vi.unstubAllGlobals())

function mountWith(books: unknown[]) {
  vi.stubGlobal(
    'fetch',
    vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(books))),
  )
  return mount(LibraryView, { global: { plugins: [createPinia()] } })
}

describe('LibraryView', () => {
  it('shows the empty state', async () => {
    const wrapper = mountWith([])
    await flushPromises()
    expect(wrapper.text()).toContain('Your library is empty.')
  })

  it('renders a card per book', async () => {
    const wrapper = mountWith([
      { id: 1, title: 'Dune', author: null, format: 'pdf', has_cover: false },
    ])
    await flushPromises()
    expect(wrapper.findAll('.card')).toHaveLength(1)
    expect(wrapper.text()).toContain('Dune')
    expect(wrapper.text()).toContain('Unknown author')
  })
})

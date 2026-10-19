import { onBeforeUnmount, ref, type Ref } from 'vue'

/** Reactive `matchMedia`: updates when the query starts or stops matching (e.g. on rotation). */
export function useMediaQuery(query: string): Ref<boolean> {
  const list = window.matchMedia?.(query)
  const matches = ref(list?.matches ?? false)
  const update = (event: MediaQueryListEvent) => (matches.value = event.matches)
  list?.addEventListener('change', update)
  onBeforeUnmount(() => list?.removeEventListener('change', update))
  return matches
}

import { onBeforeUnmount, ref, type Ref } from 'vue'

/** The root font size relative to 16px: 1 normally, more on large monitors (see main.css). */
export function useRootScale(): Ref<number> {
  const read = () => parseFloat(getComputedStyle(document.documentElement).fontSize) / 16 || 1
  const scale = ref(read())
  let timer: ReturnType<typeof setTimeout> | undefined
  const onResize = () => {
    clearTimeout(timer)
    timer = setTimeout(() => (scale.value = Math.round(read() * 20) / 20), 150)
  }
  window.addEventListener('resize', onResize)
  onBeforeUnmount(() => {
    clearTimeout(timer)
    window.removeEventListener('resize', onResize)
  })
  return scale
}

export type TurnDirection = 'next' | 'prev'

const MIN_DISTANCE = 50 // px
const MAX_DURATION = 800 // ms

/**
 * Detect a quick horizontal one-finger swipe: left = next page, right = previous.
 * Feed it touchstart/touchend events; vertical drags and multi-touch (pinch) are ignored.
 */
export function createSwipe(onSwipe: (direction: TurnDirection) => void) {
  let startX = 0
  let startY = 0
  let startTime = 0
  let tracking = false

  return {
    start(event: TouchEvent) {
      const touch = event.touches[0]
      tracking = event.touches.length === 1 && touch !== undefined
      if (!touch) return
      startX = touch.clientX
      startY = touch.clientY
      startTime = Date.now()
    },
    end(event: TouchEvent) {
      const touch = event.changedTouches[0]
      if (!tracking || !touch) return
      tracking = false
      const dx = touch.clientX - startX
      const dy = touch.clientY - startY
      const quick = Date.now() - startTime < MAX_DURATION
      if (quick && Math.abs(dx) > MIN_DISTANCE && Math.abs(dx) > Math.abs(dy) * 1.5) {
        onSwipe(dx < 0 ? 'next' : 'prev')
      }
    },
  }
}

/** Which page-turn zone a tap at viewport x falls in: the outer quarter on each side. */
export function tapZone(clientX: number, area: DOMRect): TurnDirection | null {
  const position = (clientX - area.left) / area.width
  if (position < 0.25) return 'prev'
  if (position > 0.75) return 'next'
  return null
}

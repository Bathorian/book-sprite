const DIRECTIONS = [
  'east',
  'south-east',
  'south',
  'south-west',
  'west',
  'north-west',
  'north',
  'north-east',
] as const

export type Direction = (typeof DIRECTIONS)[number]

/** A one-shot animation, drawn centred on the companion's standing frame. */
export interface CompanionAnimation {
  width: number
  height: number
  /** Milliseconds per frame. */
  durations: number[]
  frames: string[]
}

export interface Companion {
  name: string
  /** Native frame size in pixels. */
  width: number
  height: number
  /** Frame URL per direction it can face. */
  frames: Partial<Record<Direction, string>>
  animations: { page_turn?: CompanionAnimation }
}

function directionFrames(files: Record<string, string>): Partial<Record<Direction, string>> {
  const frames: Partial<Record<Direction, string>> = {}
  for (const [path, url] of Object.entries(files)) {
    const name = path.split('/').pop()!.replace('.png', '') as Direction
    if (DIRECTIONS.includes(name)) frames[name] = url
  }
  return frames
}

/** Files named 0.png, 1.png, … in playback order. */
function orderedFrames(files: Record<string, string>): string[] {
  const index = (path: string) => Number(path.split('/').pop()!.replace('.png', ''))
  return Object.entries(files)
    .sort(([a], [b]) => index(a) - index(b))
    .map(([, url]) => url)
}

export const warrior: Companion = {
  name: 'Warrior',
  width: 48,
  height: 48,
  // import.meta.glob options must be written inline; Vite ignores them otherwise.
  frames: directionFrames(
    import.meta.glob<string>('./warrior/*.png', { eager: true, query: '?url', import: 'default' }),
  ),
  animations: {
    page_turn: {
      width: 80,
      height: 80,
      durations: [200, 200, 200, 200, 200, 200],
      frames: orderedFrames(
        import.meta.glob<string>('./warrior/page-turn/*.png', {
          eager: true,
          query: '?url',
          import: 'default',
        }),
      ),
    },
  },
}

/**
 * Pick the frame to show for a direction when a companion lacks some of them:
 * the exact frame, else the plain east/west frame on the same side, else south.
 */
export function frameFor(
  frames: Partial<Record<Direction, string>>,
  direction: Direction,
): Direction {
  if (frames[direction]) return direction
  const side = direction.endsWith('east') ? 'east' : direction.endsWith('west') ? 'west' : null
  if (side && frames[side]) return side
  if (frames.south) return 'south'
  return Object.keys(frames)[0] as Direction
}

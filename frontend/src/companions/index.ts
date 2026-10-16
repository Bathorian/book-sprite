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

export interface Companion {
  id: string
  name: string
  /** Native sprite size in pixels (square). */
  size: number
  frames: Record<Direction, string>
}

function framesFrom(files: Record<string, string>): Record<Direction, string> {
  const frames = {} as Record<Direction, string>
  for (const [path, url] of Object.entries(files)) {
    const name = path.split('/').pop()!.replace('.png', '') as Direction
    if (DIRECTIONS.includes(name)) frames[name] = url
  }
  return frames
}

export const warrior: Companion = {
  id: 'warrior',
  name: 'Warrior',
  size: 48,
  frames: framesFrom(
    import.meta.glob<string>('./warrior/*.png', { eager: true, query: '?url', import: 'default' }),
  ),
}

/**
 * Map a screen-space vector (y grows downward) to the nearest of 8 directions.
 */
export function directionToward(dx: number, dy: number): Direction {
  const angle = Math.atan2(dy, dx) // 0 = east, +π/2 = south
  const sector = Math.round(angle / (Math.PI / 4))
  return DIRECTIONS[(sector + 8) % 8]!
}

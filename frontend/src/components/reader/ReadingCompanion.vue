<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue'
import { directionToward, type Companion, type Direction } from '@/companions'

const props = defineProps<{ companion: Companion; scale: number }>()

const ground = useTemplateRef<HTMLDivElement>('ground')
const x = ref(0) // centre of the sprite, px from the left of the ground
const facing = ref<Direction>('south')
const walking = ref(false)
const hop = ref<'next' | 'prev' | null>(null)

const WALK_SPEED = 170 // px per second
const START_DISTANCE = 36 // ignore small mouse moves so he doesn't fidget
const IDLE_LOOK_MS = 4000 // after this long without the mouse moving, look at the reader

const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
let pointer: { x: number; y: number } | null = null
let targetX = 0
let frame = 0
let lastTime = 0
let idleTimer: ReturnType<typeof setTimeout> | undefined
let hopTimer: ReturnType<typeof setTimeout> | undefined

const spriteSize = () => props.companion.size * props.scale

function bounds() {
  const width = ground.value?.clientWidth ?? 0
  const half = spriteSize() / 2
  return { min: half, max: Math.max(half, width - half) }
}

function faceCursor() {
  if (!pointer || !ground.value) return
  const rect = ground.value.getBoundingClientRect()
  // Aim from roughly the character's eyes.
  const eyeX = rect.left + x.value
  const eyeY = rect.bottom - spriteSize() * 0.75
  facing.value = directionToward(pointer.x - eyeX, pointer.y - eyeY)
}

function step(time: number) {
  const dt = Math.min((time - lastTime) / 1000, 0.05)
  lastTime = time
  const distance = targetX - x.value
  if (Math.abs(distance) <= 2) {
    x.value = targetX
    walking.value = false
    frame = 0
    faceCursor()
    return
  }
  walking.value = true
  facing.value = distance > 0 ? 'east' : 'west'
  x.value += Math.sign(distance) * Math.min(Math.abs(distance), WALK_SPEED * dt)
  frame = requestAnimationFrame(step)
}

function walkTo(target: number) {
  const { min, max } = bounds()
  targetX = Math.min(max, Math.max(min, target))
  if (reducedMotion) {
    x.value = targetX
    faceCursor()
    return
  }
  if (!frame) {
    lastTime = performance.now()
    frame = requestAnimationFrame(step)
  }
}

/** Called with viewport coordinates whenever the reader's mouse moves. */
function lookAt(clientX: number, clientY: number) {
  pointer = { x: clientX, y: clientY }
  clearTimeout(idleTimer)
  idleTimer = setTimeout(() => {
    if (!walking.value) facing.value = 'south'
  }, IDLE_LOOK_MS)

  const rect = ground.value?.getBoundingClientRect()
  if (!rect) return
  const wanted = clientX - rect.left
  if (walking.value || Math.abs(wanted - x.value) > START_DISTANCE) walkTo(wanted)
  else faceCursor()
}

/** A small hop toward the page that was turned to. */
function react(direction: 'next' | 'prev') {
  if (walking.value) return
  facing.value = direction === 'next' ? 'east' : 'west'
  hop.value = null
  clearTimeout(hopTimer)
  requestAnimationFrame(() => {
    hop.value = direction
    hopTimer = setTimeout(() => (hop.value = null), 450)
  })
}

function onPointerMove(event: PointerEvent) {
  if (event.pointerType !== 'touch') lookAt(event.clientX, event.clientY)
}

function onResize() {
  walkTo(targetX)
}

onMounted(() => {
  const { max } = bounds()
  x.value = targetX = max // start in the bottom-right corner
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  clearTimeout(idleTimer)
  clearTimeout(hopTimer)
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('resize', onResize)
})

defineExpose({ lookAt, react })
</script>

<template>
  <div ref="ground" class="ground" aria-hidden="true">
    <div
      class="companion"
      :class="{ walking, [`hop-${hop}`]: hop }"
      :style="{ '--size': `${spriteSize()}px`, transform: `translateX(${x - spriteSize() / 2}px)` }"
    >
      <div class="shadow"></div>
      <img
        v-for="(url, direction) in companion.frames"
        v-show="direction === facing"
        :key="direction"
        :src="url"
        :width="spriteSize()"
        :height="spriteSize()"
        alt=""
        draggable="false"
      />
    </div>
  </div>
</template>

<style scoped>
.ground {
  position: relative;
  height: 100%;
  pointer-events: none;
}
.companion {
  position: absolute;
  bottom: 0;
  left: 0;
  width: var(--size);
  height: var(--size);
  will-change: transform;
}
.companion img {
  position: absolute;
  inset: 0;
  image-rendering: pixelated;
  /* The faint blue-white spirit light from the character's description. */
  filter: drop-shadow(0 0 3px rgb(170 210 255 / 0.55));
  animation: breathe 2.4s steps(2, jump-none) infinite;
  transform-origin: 50% 100%;
}
.shadow {
  position: absolute;
  left: 22%;
  right: 22%;
  bottom: -3px;
  height: 8px;
  border-radius: 50%;
  background: rgb(59 48 36 / 0.22);
  filter: blur(1px);
}

/* No walk-cycle frames ship with this sprite, so suggest steps with a bob. */
.walking img {
  animation: stride 0.32s steps(2, jump-none) infinite;
}
.hop-next img,
.hop-prev img {
  animation: hop 0.45s ease-out;
}

@keyframes breathe {
  from {
    transform: translateY(0);
  }
  to {
    transform: translateY(-1px) scaleY(1.01);
  }
}
@keyframes stride {
  from {
    transform: translateY(0);
  }
  to {
    transform: translateY(-3px);
  }
}
@keyframes hop {
  0% {
    transform: translateY(0) scale(1, 1);
  }
  15% {
    transform: translateY(0) scale(1.06, 0.92);
  }
  45% {
    transform: translateY(-14px) scale(0.96, 1.05);
  }
  80% {
    transform: translateY(0) scale(1.04, 0.95);
  }
  100% {
    transform: translateY(0) scale(1, 1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .companion img,
  .walking img,
  .hop-next img,
  .hop-prev img {
    animation: none;
  }
}
</style>

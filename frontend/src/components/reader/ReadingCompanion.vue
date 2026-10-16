<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, useTemplateRef } from 'vue'
import { frameFor, type Companion, type Direction } from '@/companions'

/** `height` is the on-screen height in px; the width follows the sprite's aspect ratio. */
const props = defineProps<{ sprite: Companion; height: number }>()

const ground = useTemplateRef<HTMLDivElement>('ground')
const x = ref(0) // centre of the sprite, px from the left of the ground
const facing = ref<Direction>('south')
const shown = computed(() => frameFor(props.sprite.frames, facing.value))
const displayWidth = computed(() => (props.sprite.width * props.height) / props.sprite.height)
// Keep small pixel-art crisp; let larger artwork scale smoothly.
const pixelArt = computed(() => props.sprite.height <= 128)

// Page-turn animation, if the sprite has one. Its canvas may be larger than the standing
// frame (room for kicks and leaps); the two canvases are aligned on their centres.
const pageTurn = computed(() => props.sprite.animations.page_turn)
const actionFrame = ref<number | null>(null)
const actionStyle = computed(() => {
  const animation = pageTurn.value
  if (!animation) return {}
  const scale = props.height / props.sprite.height
  const width = animation.width * scale
  const height = animation.height * scale
  return {
    width: `${width}px`,
    height: `${height}px`,
    left: `${(displayWidth.value - width) / 2}px`,
    bottom: `${(props.height - height) / 2}px`,
  }
})

const WALK_SPEED = 60 // px per second: an unhurried patrol

const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
let heading: 1 | -1 = 1 // 1 = walking right (east), -1 = left (west)
let frame = 0
let lastTime = 0
let actionTimer: ReturnType<typeof setTimeout> | undefined

function bounds() {
  const width = ground.value?.clientWidth ?? 0
  const half = displayWidth.value / 2
  return { min: half, max: Math.max(half, width - half) }
}

/** Walk steadily back and forth along the ground, pausing only while an animation plays. */
function step(time: number) {
  const dt = Math.min((time - lastTime) / 1000, 0.05) // clamp so a background tab doesn't jump
  lastTime = time
  frame = requestAnimationFrame(step)
  if (actionFrame.value !== null) return

  const { min, max } = bounds()
  let next = x.value + heading * WALK_SPEED * dt
  if (next >= max || next <= min) {
    next = Math.min(max, Math.max(min, next))
    heading = heading === 1 ? -1 : 1
  }
  x.value = next
  facing.value = heading === 1 ? 'east' : 'west'
}

/** Play the page-turn animation once from the start (restarting it if it's already running). */
function playPageTurn(durations: number[]) {
  clearTimeout(actionTimer)
  const advance = (index: number) => {
    actionFrame.value = index
    actionTimer = setTimeout(() => {
      if (index + 1 < durations.length) advance(index + 1)
      else actionFrame.value = null
    }, durations[index])
  }
  advance(0)
}

/** React to a page turn with the sprite's page-turn animation. */
function react() {
  if (!reducedMotion && pageTurn.value) playPageTurn(pageTurn.value.durations)
}

onMounted(() => {
  x.value = bounds().min
  if (reducedMotion) return // stand still, facing the reader
  lastTime = performance.now()
  frame = requestAnimationFrame(step)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(frame)
  clearTimeout(actionTimer)
})

defineExpose({ react })
</script>

<template>
  <div ref="ground" class="ground" aria-hidden="true">
    <div
      class="companion"
      :class="{ walking: !reducedMotion && actionFrame === null, 'pixel-art': pixelArt }"
      :style="{
        width: `${displayWidth}px`,
        height: `${height}px`,
        transform: `translateX(${x - displayWidth / 2}px)`,
      }"
    >
      <div class="shadow"></div>
      <div v-show="actionFrame === null" class="pose">
        <img
          v-for="(url, direction) in sprite.frames"
          v-show="direction === shown"
          :key="direction"
          :src="url"
          alt=""
          draggable="false"
        />
      </div>
      <!-- Always rendered (hidden) so every frame is loaded before the first page turn. -->
      <div v-if="pageTurn" v-show="actionFrame !== null" class="action" :style="actionStyle">
        <img
          v-for="(url, index) in pageTurn.frames"
          v-show="index === actionFrame"
          :key="url"
          :src="url"
          alt=""
          draggable="false"
        />
      </div>
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
  will-change: transform;
}
.pose,
.action {
  position: absolute;
}
.pose {
  inset: 0;
}
.companion img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: bottom;
}
.pose img {
  animation: breathe 2.4s steps(2, jump-none) infinite;
  transform-origin: 50% 100%;
}
.pixel-art img {
  image-rendering: pixelated;
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

/* Sprites have no walk-cycle frames, so suggest steps with a bob. */
.walking .pose img {
  animation: stride 0.4s steps(2, jump-none) infinite;
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
@media (prefers-reduced-motion: reduce) {
  .pose img,
  .walking .pose img {
    animation: none;
  }
}
</style>

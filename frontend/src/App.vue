<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <RouterView v-if="route.meta.fullscreen" />
  <template v-else>
    <header class="app-header">
      <div class="container">
        <RouterLink to="/" class="brand">BookSprite</RouterLink>
      </div>
    </header>
    <main class="app-main container">
      <RouterView />
    </main>
  </template>
</template>

<style scoped>
/* Header and page share one centred column, capped on very wide screens. */
.container {
  max-width: 110rem;
  margin: 0 auto;
  padding-inline: clamp(1rem, 3vw, 1.5rem);
}
.app-header {
  padding-block: 0.75rem;
  border-bottom: 1px solid var(--border);
}
.brand {
  display: inline-block;
  padding-block: 0.25rem;
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text);
  text-decoration: none;
}
.app-main {
  padding-block: 1.5rem;
}
</style>

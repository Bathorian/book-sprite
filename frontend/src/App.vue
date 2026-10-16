<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
</script>

<template>
  <RouterView v-if="route.meta.fullscreen" />
  <template v-else>
    <header class="app-header">
      <RouterLink to="/" class="brand">BookSprite</RouterLink>
    </header>
    <main class="app-main">
      <RouterView />
    </main>
  </template>
</template>

<style scoped>
.app-header {
  padding: 0.75rem 1.5rem;
  border-bottom: 1px solid var(--border);
}
.brand {
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--text);
  text-decoration: none;
}
.app-main {
  padding: 1.5rem;
}
</style>

import { createRouter, createWebHistory } from 'vue-router'
import LibraryView from '@/views/LibraryView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    /** Hide the app header (used by the reader). */
    fullscreen?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'library', component: LibraryView },
    {
      path: '/read/:id(\\d+)',
      name: 'reader',
      // Loaded on demand so the PDF/EPUB libraries stay out of the library page bundle.
      component: () => import('@/views/ReaderView.vue'),
      props: (route) => ({ id: Number(route.params.id) }),
      meta: { fullscreen: true },
    },
  ],
})

export default router

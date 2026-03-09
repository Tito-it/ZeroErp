import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AppLayout from '../core/components/AppLayout.vue'
import HomeView from '../core/views/HomeView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    // Rotta login — senza layout (niente sidebar/topbar)
    {
      path: '/login',
      name: 'login',
      component: () => import('../core/views/LoginView.vue'),
      meta: { public: true }
    },

    // Rotte autenticate — con layout principale
    {
      path: '/',
      component: AppLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: HomeView,
          meta: { domain: 'home' }
        }
      ]
    }
  ]
})

// Navigation guard — protegge tutte le rotte non pubbliche
router.beforeEach((to) => {
  const auth = useAuthStore()

  if (!to.meta.public && !auth.isAuthenticated) {
    return {
      name: 'login',
      query: to.fullPath !== '/' ? { redirect: to.fullPath } : {}
    }
  }

  // Utente autenticato che va a /login → redirect a home
  if (to.name === 'login' && auth.isAuthenticated) {
    return { name: 'home' }
  }

  // Carica profilo utente se autenticato ma non ancora caricato
  if (auth.isAuthenticated && !auth.user) {
    auth.fetchProfile()
  }
})

export default router

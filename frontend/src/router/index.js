import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNavigationStore } from '../stores/navigation'
import { useTabsStore } from '../stores/tabs'
import { DOMAINS, resolveTabLabel } from '../core/navigation'
import i18n from '../core/i18n'
import AppLayout from '../core/components/AppLayout.vue'
import HomeView from '../core/views/HomeView.vue'

const t = i18n.global.t

// Genera rotte placeholder per domini senza pagine dedicate
function domainPlaceholderRoutes() {
  const domainsWithRoutes = new Set(['amm-software'])
  return DOMAINS
    .filter(d => !domainsWithRoutes.has(d.key))
    .map(d => ({
      path: d.key,
      name: d.key,
      component: () => import('../core/views/PlaceholderView.vue'),
      meta: { domain: d.key }
    }))
}

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
        },

        // --- Amm. Software ---
        {
          path: 'amm-software/operatori',
          name: 'amm-software-operatori',
          component: () => import('../core/views/PlaceholderView.vue'),
          meta: { domain: 'amm-software', menuKey: 'operatori' }
        },
        {
          path: 'amm-software/profili-reparto',
          name: 'amm-software-profili-reparto',
          component: () => import('../core/views/PlaceholderView.vue'),
          meta: { domain: 'amm-software', menuKey: 'profili-reparto' }
        },
        {
          path: 'amm-software/permessi',
          name: 'amm-software-permessi',
          component: () => import('../core/views/PlaceholderView.vue'),
          meta: { domain: 'amm-software', menuKey: 'permessi' }
        },
        {
          path: 'amm-software/audit-log',
          name: 'amm-software-audit-log',
          component: () => import('../core/views/PlaceholderView.vue'),
          meta: { domain: 'amm-software', menuKey: 'audit-log' }
        },

        // --- Rotte placeholder per domini senza pagine dedicate ---
        ...domainPlaceholderRoutes(),

        // --- Catch-all 403 per domini non autorizzati ---
        {
          path: 'forbidden',
          name: 'forbidden',
          component: () => import('../core/views/ErrorView.vue'),
          meta: { domain: 'home', errorKey: 'forbidden', errorIcon: 'pi pi-lock' }
        },

        // --- Catch-all 404 ---
        {
          path: ':pathMatch(.*)*',
          name: 'not-found',
          component: () => import('../core/views/ErrorView.vue'),
          meta: { domain: 'home', errorKey: 'not_found', errorIcon: 'pi pi-map' }
        }
      ]
    }
  ]
})

// Navigation guard — protegge rotte, imposta dominio, apre tab
router.beforeEach(async (to) => {
  const auth = useAuthStore()

  // Rotte pubbliche
  if (to.meta.public) {
    if (to.name === 'login' && auth.isAuthenticated) {
      return { name: 'home' }
    }
    return
  }

  // Utente non autenticato -> login
  if (!auth.isAuthenticated) {
    return {
      name: 'login',
      query: to.fullPath !== '/' ? { redirect: to.fullPath } : {}
    }
  }

  // Carica profilo se mancante — se fallisce, token non valido → login
  if (!auth.user) {
    try {
      await auth.fetchProfile()
    } catch {
      auth.clearTokens()
      return {
        name: 'login',
        query: to.fullPath !== '/' ? { redirect: to.fullPath } : {}
      }
    }
  }

  // Guard dominio admin: controlla permesso
  const domain = to.meta.domain
  if (domain === 'amm-software' && !auth.isAdmin) {
    return { name: 'forbidden' }
  }

  // Imposta dominio attivo nello store navigation
  const nav = useNavigationStore()
  if (domain && domain !== 'home') {
    nav.setDomain(domain)
  } else if (to.name === 'home') {
    nav.clearDomain()
  }

  // Apre tab (escluso home e pagine errore)
  if (domain && domain !== 'home' && to.name !== 'forbidden' && to.name !== 'not-found') {
    const tabs = useTabsStore()
    tabs.openTab({
      path: to.path,
      label: resolveTabLabel(to.meta, t) || to.path,
      domain: domain,
      icon: null
    })
  }
})

export default router

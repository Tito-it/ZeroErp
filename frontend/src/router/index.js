import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNavigationStore } from '../stores/navigation'
import { useTabsStore } from '../stores/tabs'
import { DOMAINS, resolveTabLabel, resolveTabIcon } from '../core/navigation'
import i18n from '../core/i18n'
import AppLayout from '../core/components/AppLayout.vue'
import HomeView from '../core/views/HomeView.vue'

const t = i18n.global.t

// Genera rotte placeholder per domini senza pagine dedicate
function domainPlaceholderRoutes() {
  const domainsWithRoutes = new Set(['amm-software', 'anagrafiche', 'catalogo', 'config', 'pratiche', 'vendite'])
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
    // Rotte pubbliche — senza layout (niente sidebar/topbar)
    {
      path: '/login',
      name: 'login',
      component: () => import('../core/views/LoginView.vue'),
      meta: { public: true }
    },
    {
      path: '/change-password',
      name: 'change-password',
      component: () => import('../core/views/ChangePasswordView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/password-reset',
      name: 'password-reset',
      component: () => import('../core/views/PasswordResetRequestView.vue'),
      meta: { public: true }
    },
    {
      path: '/reset-password/:token',
      name: 'password-reset-confirm',
      component: () => import('../core/views/PasswordResetConfirmView.vue'),
      meta: { public: true }
    },
    {
      path: '/attivazione/:token',
      name: 'attivazione',
      component: () => import('../core/views/AttivazioneView.vue'),
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
          component: () => import('../amministrazione/views/OperatoriListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'operatori' }
        },
        {
          path: 'amm-software/profili-reparto',
          name: 'amm-software-profili-reparto',
          component: () => import('../amministrazione/views/RepartiProfiloView.vue'),
          meta: { domain: 'amm-software', menuKey: 'profili-reparto' }
        },
        {
          path: 'amm-software/permessi',
          name: 'amm-software-permessi',
          component: () => import('../amministrazione/views/PermessiRiepilogoView.vue'),
          meta: { domain: 'amm-software', menuKey: 'permessi' }
        },
        {
          path: 'amm-software/audit-log',
          name: 'amm-software-audit-log',
          component: () => import('../amministrazione/views/AuditLogView.vue'),
          meta: { domain: 'amm-software', menuKey: 'audit-log' }
        },
        {
          path: 'amm-software/email-accounts',
          name: 'amm-software-email-accounts',
          component: () => import('../amministrazione/views/EmailAccountsListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'email-accounts' }
        },
        {
          path: 'amm-software/email-templates',
          name: 'amm-software-email-templates',
          component: () => import('../amministrazione/views/EmailTemplatesListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'email-templates' }
        },
        {
          path: 'amm-software/email-log',
          name: 'amm-software-email-log',
          component: () => import('../amministrazione/views/EmailLogsListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'email-log' }
        },

        // --- Anagrafiche ---
        {
          path: 'anagrafiche/soggetti',
          name: 'anagrafiche-soggetti',
          component: () => import('../anagrafiche/views/SoggettiView.vue'),
          meta: { domain: 'anagrafiche', menuKey: 'soggetti' }
        },
        {
          path: 'anagrafiche/clienti',
          name: 'anagrafiche-clienti',
          component: () => import('../anagrafiche/views/ClientiView.vue'),
          meta: { domain: 'anagrafiche', menuKey: 'clienti' }
        },
        {
          path: 'anagrafiche/fornitori',
          name: 'anagrafiche-fornitori',
          component: () => import('../anagrafiche/views/FornitoriView.vue'),
          meta: { domain: 'anagrafiche', menuKey: 'fornitori' }
        },
        {
          path: 'anagrafiche/indirizzi',
          name: 'anagrafiche-indirizzi',
          component: () => import('../anagrafiche/views/IndirizziView.vue'),
          meta: { domain: 'anagrafiche', menuKey: 'indirizzi' }
        },

        // --- Config ---
        {
          path: 'config/tabelle',
          name: 'config-tabelle',
          component: () => import('../config/views/ConfigView.vue'),
          meta: { domain: 'config', menuKey: 'tabelle' }
        },

        // --- Catalogo ---
        {
          path: 'catalogo/articoli',
          name: 'catalogo-articoli',
          component: () => import('../catalogo/views/ArticoliView.vue'),
          meta: { domain: 'catalogo', menuKey: 'articoli' }
        },
        {
          path: 'catalogo/unita-misura',
          name: 'catalogo-unita-misura',
          component: () => import('../catalogo/views/UnitaMisuraView.vue'),
          meta: { domain: 'catalogo', menuKey: 'unita-misura' }
        },

        // --- Vendite ---
        {
          path: 'vendite/listini',
          name: 'vendite-listini',
          component: () => import('../vendite/views/ListiniView.vue'),
          meta: { domain: 'vendite', menuKey: 'listini' }
        },

        // --- Pratiche ---
        {
          path: 'pratiche',
          name: 'pratiche-gestione',
          component: () => import('../pratiche/views/PraticheDashboard.vue'),
          meta: { domain: 'pratiche', menuKey: 'gestione' }
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

  // Rotte pubbliche (login, reset, attivazione)
  if (to.meta.public) {
    if (to.name === 'login' && auth.isAuthenticated) {
      return { name: 'home' }
    }
    return
  }

  // Utente non autenticato -> login (vale per requiresAuth e rotte layout)
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

  // Guard cambio password obbligatorio: redirect a /change-password
  if (auth.mustChangePassword && to.name !== 'change-password') {
    return { name: 'change-password' }
  }

  // Guard dominio admin: controlla permesso
  const domain = to.meta.domain
  if (domain === 'amm-software' && !auth.isAdmin) {
    return { name: 'forbidden' }
  }

  // Guard livello BLOCCATO: l'utente non ha accesso a questo dominio.
  // I domini adminOnly hanno gia' il loro guard sopra — non applicare.
  if (domain) {
    const domainConfig = DOMAINS.find(d => d.key === domain)
    if (domainConfig && !domainConfig.adminOnly
        && domainConfig.schemaDb && auth.isAreaBlocked(domainConfig.schemaDb)) {
      return { name: 'forbidden' }
    }
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
    const opened = tabs.openTab({
      path: to.path,
      label: resolveTabLabel(to.meta, t) || to.path,
      domain: domain,
      icon: resolveTabIcon(to.meta)
    })
    // Limite raggiunto — blocca navigazione
    if (!opened) return false
  }
})

export default router

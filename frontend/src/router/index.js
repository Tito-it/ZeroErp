import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNavigationStore } from '../stores/navigation'
import { useTabsStore } from '../stores/tabs'
import { DOMAINS, resolveTabLabel, resolveTabIcon } from '../core/navigation'
import { FE_NAMESPACE, resolveRuoloFeConfig } from '../core/constants'
import i18n from '../core/i18n'
import AppLayout from '../core/components/AppLayout.vue'
import HomeView from '../core/views/HomeView.vue'

const t = i18n.global.t

// Rotte autenticate universali: accessibili a tutte le vesti, non
// passano per il check namespace. Include la pagina cambio password
// (tipicamente forzata post-invito) e le pagine d'errore.
const UNIVERSAL_ROUTE_NAMES = new Set([
  'change-password',
  'forbidden',
  'not-found'
])

// Tabella statica path → namespace. Definita come array ordinato per
// match prefisso con separator "/" esplicito (evita che `/portale-debug`
// sia matchato come namespace `portale`). Il fallback `admin` copre tutte
// le rotte autenticate non /portale e non /shop.
const PATH_NAMESPACE_PREFIXES = [
  { prefix: '/portale', namespace: FE_NAMESPACE.PORTALE },
  { prefix: '/shop', namespace: FE_NAMESPACE.SHOP }
]

// Scopo: Dato un path, ritorna a quale namespace FE appartiene.
// Match esatto sul segmento (`/portale` o `/portale/...`) per evitare
// falsi positivi su path che iniziano per lo stesso prefisso ma con
// caratteri non-slash subito dopo.
function resolvePathNamespace(path) {
  for (const { prefix, namespace } of PATH_NAMESPACE_PREFIXES) {
    if (path === prefix || path.startsWith(`${prefix}/`)) return namespace
  }
  return FE_NAMESPACE.ADMIN
}

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
    {
      path: '/attivazione-portale/:token',
      name: 'attivazione-portale',
      component: () => import('../portale/views/AttivazionePortaleView.vue'),
      meta: { public: true }
    },
    // B1 §13.7: pagina attivazione account shop customer.
    // Branching INVITO (form password) vs CROSS (one-click) deciso
    // dal BE via /shop/attivazione/validate/<token>/. Pubblica (no JWT)
    // perche' il consumer del link email non e' ancora autenticato.
    // Path coerente con /attivazione-portale/:token (single pattern
    // delle pagine public di attivazione, link emesso dal BE con
    // `link_path='/attivazione-shop'` in InvitoPortaleService).
    {
      path: '/attivazione-shop/:token',
      name: 'attivazione-shop',
      component: () => import('../shop/views/AttivazioneShopView.vue'),
      meta: { public: true, domain: 'shop', menuKey: 'attivazione' }
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
          path: 'amm-software/emittenti-fiscali',
          name: 'amm-software-emittenti-fiscali',
          component: () => import('../amministrazione/views/EmittentiFiscaliListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'emittenti-fiscali' }
        },
        {
          path: 'amm-software/matrici',
          name: 'amm-software-matrici',
          component: () => import('../amministrazione/views/MatriciListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'matrici' }
        },
        {
          path: 'amm-software/matrice-utilities-ruoli',
          name: 'amm-software-matrice-utilities-ruoli',
          component: () => import('../amministrazione/views/UtilitiesTipiRuoloListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'matrice-utilities-ruoli' }
        },
        {
          path: 'amm-software/matrice-indirizzi-ruoli',
          name: 'amm-software-matrice-indirizzi-ruoli',
          component: () => import('../amministrazione/views/TipiRuoloTipiIndirizzoListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'matrice-indirizzi-ruoli' }
        },
        {
          path: 'amm-software/categorie-clienti',
          name: 'amm-software-categorie-clienti',
          component: () => import('../amministrazione/views/CategorieClientiListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'categorie-clienti' }
        },
        {
          path: 'amm-software/matrice-categorie-listini',
          name: 'amm-software-matrice-categorie-listini',
          component: () => import('../amministrazione/views/CategorieClientiListiniListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'matrice-categorie-listini' }
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
        {
          path: 'amm-software/personalizzazioni-liste-tecniche',
          name: 'amm-software-personalizzazioni-liste-tecniche',
          component: () => import('../ui/views/PersonalizzazioniListeTecnicheView.vue'),
          meta: { domain: 'amm-software', menuKey: 'personalizzazioni-liste-tecniche' }
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
        {
          path: 'config/impostazioni',
          name: 'config-impostazioni',
          component: () => import('../config/views/ImpostazioniView.vue'),
          meta: { domain: 'config', menuKey: 'impostazioni' }
        },
        {
          path: 'config/documenti',
          name: 'config-documenti',
          component: () => import('../config/views/ConfigurazioneDocumentiView.vue'),
          meta: { domain: 'config', menuKey: 'config-documenti' }
        },
        {
          path: 'config/personalizzazioni-liste',
          name: 'config-personalizzazioni-liste',
          component: () => import('../ui/views/GestionePersonalizzazioniListeView.vue'),
          meta: { domain: 'config', menuKey: 'personalizzazioni-liste' }
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
        {
          path: 'catalogo/conversioni-uom',
          name: 'catalogo-conversioni-uom',
          component: () => import('../catalogo/views/ConversioniUomView.vue'),
          meta: { domain: 'catalogo', menuKey: 'conversioni-uom' }
        },
        {
          path: 'catalogo/uom-tipi',
          name: 'catalogo-uom-tipi',
          component: () => import('../catalogo/views/UomTipiView.vue'),
          meta: { domain: 'catalogo', menuKey: 'uom-tipi' }
        },

        // --- Vendite ---
        {
          path: 'vendite/preventivi',
          name: 'vendite-preventivi',
          component: () => import('../vendite/preventivi/views/PreventiviView.vue'),
          meta: { domain: 'vendite', menuKey: 'preventivi' }
        },
        {
          path: 'vendite/offerte',
          name: 'vendite-offerte',
          component: () => import('../vendite/offerte/views/OfferteView.vue'),
          meta: { domain: 'vendite', menuKey: 'offerte' }
        },
        {
          path: 'vendite/ordini',
          name: 'vendite-ordini',
          component: () => import('../vendite/ordini/views/OrdiniView.vue'),
          meta: { domain: 'vendite', menuKey: 'ordini' }
        },
        {
          path: 'vendite/listini',
          name: 'vendite-listini',
          component: () => import('../vendite/views/ListiniView.vue'),
          meta: { domain: 'vendite', menuKey: 'listini' }
        },
        {
          path: 'vendite/contratti',
          name: 'vendite-contratti',
          component: () => import('../vendite/views/ContrattiListView.vue'),
          meta: { domain: 'vendite', menuKey: 'contratti' }
        },
        {
          path: 'vendite/promo-articoli',
          name: 'vendite-promo-articoli',
          component: () => import('../vendite/views/PromoArticoliListView.vue'),
          meta: { domain: 'vendite', menuKey: 'promo-articoli' }
        },
        {
          path: 'vendite/approvazioni-prezzo',
          name: 'vendite-approvazioni-prezzo',
          component: () => import('../vendite/views/ApprovazioniPrezzoListView.vue'),
          meta: { domain: 'vendite', menuKey: 'approvazioni-prezzo' }
        },

        // --- Pratiche ---
        {
          // Atterraggio dominio = home launcher (comincia/continua); la
          // dashboard-lista (consultazione/ricerca) vive su /pratiche/gestione.
          path: 'pratiche',
          name: 'pratiche-home',
          component: () => import('../pratiche/views/PraticheHome.vue'),
          meta: { domain: 'pratiche', menuKey: 'home' }
        },
        {
          path: 'pratiche/gestione',
          name: 'pratiche-gestione',
          component: () => import('../pratiche/views/PraticheDashboard.vue'),
          meta: { domain: 'pratiche', menuKey: 'gestione' }
        },

        // --- Rotte placeholder per domini senza pagine dedicate ---
        ...domainPlaceholderRoutes(),

        // --- Namespace portale (clienti/fornitori) — §8.5.6 + §8.6 ---
        // Il namespace e' derivato dinamicamente dal path nel guard
        // (`resolvePathNamespace`), quindi le rotte non devono
        // ridichiararlo in meta — `domain`+`menuKey` bastano a PlaceholderView
        // per risolvere la chiave i18n.
        {
          path: 'portale',
          name: 'portale-home',
          component: () => import('../core/views/PlaceholderView.vue'),
          meta: { domain: 'portale', menuKey: 'home' }
        },
        // §8.6.3: profilo portale (anagrafica + stato accessi + pulsante
        // activate-shop). Accessibile solo a vesti CLIENTE/FORNITORE_PORTALE
        // via namespace guard router (§8.5.4).
        {
          path: 'portale/profile',
          name: 'portale-profile',
          component: () => import('../portale/views/ProfileView.vue'),
          meta: { domain: 'portale', menuKey: 'profile' }
        },
        {
          path: 'portale/:pathMatch(.*)*',
          name: 'portale-catchall',
          component: () => import('../core/views/PlaceholderView.vue'),
          meta: { domain: 'portale', menuKey: 'home' }
        },

        // --- Namespace shop — §8.5.6 stub ---
        // MVP arriva con PR-C. Per ora placeholder "Shop in arrivo".
        {
          path: 'shop',
          name: 'shop-home',
          component: () => import('../core/views/PlaceholderView.vue'),
          meta: { domain: 'shop', menuKey: 'home' }
        },
        {
          path: 'shop/:pathMatch(.*)*',
          name: 'shop-catchall',
          component: () => import('../core/views/PlaceholderView.vue'),
          meta: { domain: 'shop', menuKey: 'home' }
        },

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

  // Utente non autenticato -> login (vale per requiresAuth e rotte layout).
  // `isAuthenticated` ora considera scaduto sia access che refresh: se entrambi
  // morti, l'utente NON puo' navigare (prima poteva, perche' il check era solo
  // sulla presenza dell'access token in localStorage, anche scaduto).
  if (!auth.isAuthenticated) {
    const query = { reason: 'session_expired' }
    if (to.fullPath !== '/') query.redirect = to.fullPath
    return { name: 'login', query }
  }

  // Refresh proattivo: access scaduto ma refresh ancora valido. Evitiamo la
  // chiamata 401 di troppo che farebbe poi scattare l'interceptor — qui
  // preveniamo il problema prima che la pagina monti i suoi store. Se il
  // refresh fallisce (es. refresh revocato server-side) il guard rimanda al
  // login con reason=session_expired.
  if (!auth.accessTokenValid && auth.refreshTokenValid) {
    const ok = await auth.tryRefreshToken()
    if (!ok) {
      const query = { reason: 'session_expired' }
      if (to.fullPath !== '/') query.redirect = to.fullPath
      return { name: 'login', query }
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

  // §8.5.4/§8.5.5 — Namespace multi-canale. Un utente autenticato puo'
  // navigare solo dentro il proprio namespace (`admin` per operatori,
  // `portale` per CLIENTE/FORNITORE_PORTALE, `shop` per SHOP_CUSTOMER).
  // Regole:
  //   - rotte universali (cambio password, forbidden, 404) esentate;
  //   - veste senza namespace FE (API_CLIENT, DISABILITATO) → forbidden;
  //   - path in namespace diverso dalla veste → grace redirect alla home
  //     namespace (UX: utente portale che digita / → /portale, non 403).
  // La mappa ruolo→config e' in `constants.RUOLO_FE_NAMESPACE` — single
  // source di verita' condivisa con eventuali altri consumer UI.
  if (!UNIVERSAL_ROUTE_NAMES.has(to.name)) {
    const ruoloConfig = resolveRuoloFeConfig(auth.ruoloApplicativo)
    if (!ruoloConfig) {
      return { name: 'forbidden' }
    }
    const pathNs = resolvePathNamespace(to.path)
    if (pathNs !== ruoloConfig.namespace) {
      // Usa homeRouteName (se definito dalla config) per evitare redirect
      // loop su rotte child di AppLayout; altrimenti path string.
      if (ruoloConfig.homeRouteName) return { name: ruoloConfig.homeRouteName }
      return ruoloConfig.homePath
    }
  }

  // Guard dominio admin: controlla permesso (solo namespace operatore)
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
      menuKey: to.meta.menuKey || null,
      icon: resolveTabIcon(to.meta)
    })
    // Limite raggiunto — blocca navigazione
    if (!opened) return false
  }
})

export default router

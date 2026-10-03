import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useNavigationStore } from '../stores/navigation'
import { useTabsStore } from '../stores/tabs'
import { DOMAINS, findMenuItem, isMenuItemAllowed, resolveTabLabel, resolveTabIcon } from '../core/navigation'
import { FE_NAMESPACE, STATUS_ICONS, resolveRuoloFeConfig } from '../core/constants'
import { MOTIVO_USCITA, sessioneDichiarataChiusa } from '../core/sessione'
import { caricaMisurePagina } from '../core/misurePagina'
import i18n from '../core/i18n'
import { chiudiTuttiIDrawer } from '../core/composables/useDrawerChiusuraGlobale'
import { CODE } from '../pagamenti/vocabolari'
import { FAMIGLIA } from '../magazzino/vocabolari'
import { UOM_TABS } from '../catalogo/constants'
import { ACCESSI_TABS } from '../amministrazione/constants'
import AppLayout from '../core/components/AppLayout.vue'
import HomeView from '../core/views/HomeView.vue'

const t = i18n.global.t

// Rotte autenticate universali: accessibili a tutte le vesti, non
// passano per il check namespace. Include la pagina cambio password
// (tipicamente forzata post-invito) e le pagine d'errore.
const ROTTA_AVVIO_NON_RIUSCITO = 'avvio-non-riuscito'

const UNIVERSAL_ROUTE_NAMES = new Set([
  'change-password',
  'sicurezza',
  'forbidden',
  'not-found',
  ROTTA_AVVIO_NON_RIUSCITO
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
  const domainsWithRoutes = new Set(['amm-software', 'anagrafiche', 'catalogo', 'config', 'magazzino', 'pagamenti', 'pratiche', 'strumenti', 'vendite'])
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
    // «Sicurezza dell'accesso» (secondo fattore): fuori dal layout come il
    // cambio password, perche' con l'obbligo pendente il backend apre solo i
    // suoi endpoint — dentro il layout l'avvio chiamerebbe API che rispondono
    // 403 (brief sicurezza §3.4-bis, T-4).
    {
      path: '/sicurezza',
      name: 'sicurezza',
      component: () => import('../core/views/SicurezzaView.vue'),
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

    // Configurazione globale non letta (le misure di pagina, BB
    // `core/misurePagina`): la apre il guard. ⛔ FUORI da `AppLayout`, ed e' il
    // punto: il layout monta componenti che le misure le leggono, quindi una
    // pagina d'errore dentro il layout cadrebbe per la stessa causa che deve
    // mostrare. «Torna alla home» ripassa dal guard e riprova.
    {
      path: '/avvio-non-riuscito',
      name: ROTTA_AVVIO_NON_RIUSCITO,
      component: () => import('../core/views/ErrorView.vue'),
      meta: { errorKey: 'avvio_non_riuscito', errorIcon: STATUS_ICONS.ERRORE }
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
        // L'area «Accessi» (brief-db-be-fe-area-accessi, A-1): tre schede che
        // censiscono tutte le credenziali. La voce «Operatori» e' diventata la
        // prima scheda.
        {
          path: 'amm-software/accessi',
          name: 'amm-software-accessi',
          component: () => import('../amministrazione/views/AccessiView.vue'),
          meta: { domain: 'amm-software', menuKey: 'accessi' }
        },
        // ⛔ Il vecchio indirizzo resta come redirect: i PREFERITI sono path
        //    salvati (`useNavigationFavorites`), e un link rotto non lo vede
        //    nessun test. Porta sulla scheda «Operatori».
        {
          path: 'amm-software/operatori',
          name: 'amm-software-operatori',
          redirect: { name: 'amm-software-accessi', query: { tab: ACCESSI_TABS.OPERATORI } }
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
          // Famiglie di documento: il catalogo GLOBALE della regola che i
          // registri di numerazione applicano. Vive qui e non dentro i
          // registri — che stanno nel drawer di UN emittente — perche' una
          // famiglia vale per tutti gli emittenti insieme (decisione di Tid,
          // 2026-09-02).
          path: 'amm-software/famiglie-documento',
          name: 'amm-software-famiglie-documento',
          component: () => import('../amministrazione/views/FamiglieDocumentoListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'famiglie-documento' }
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
          path: 'amm-software/definizioni-workflow',
          name: 'amm-software-definizioni-workflow',
          component: () => import('../amministrazione/views/DefinizioniWorkflowListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'definizioni-workflow' }
        },
        {
          // Editor/ispettore di una singola edizione (rotta dedicata: il dettaglio
          // strutturale e' troppo ricco per un drawer). menuKey = parent, per tenere
          // evidenziata la voce "Definizioni workflow" nella sidebar.
          path: 'amm-software/definizioni-workflow/:id',
          name: 'amm-software-definizione-editor',
          component: () => import('../amministrazione/views/DefinizioneEditorView.vue'),
          meta: { domain: 'amm-software', menuKey: 'definizioni-workflow' }
        },
        {
          path: 'amm-software/matrice-categorie-listini',
          name: 'amm-software-matrice-categorie-listini',
          component: () => import('../amministrazione/views/CategorieClientiListiniListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'matrice-categorie-listini' }
        },
        {
          path: 'amm-software/processi-automatici',
          name: 'amm-software-processi-automatici',
          component: () => import('../amministrazione/views/ProcessiAutomaticiListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'processi-automatici' }
        },
        {
          path: 'amm-software/audit-log',
          name: 'amm-software-audit-log',
          component: () => import('../amministrazione/views/AuditLogView.vue'),
          meta: { domain: 'amm-software', menuKey: 'audit-log' }
        },
        {
          path: 'amm-software/error-log',
          name: 'amm-software-error-log',
          component: () => import('../amministrazione/views/ErrorLogListView.vue'),
          meta: { domain: 'amm-software', menuKey: 'error-log' }
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
        {
          path: 'anagrafiche/titoli-iva-sfondati',
          name: 'anagrafiche-titoli-iva-sfondati',
          component: () => import('../anagrafiche/views/TitoliIvaSfondatiView.vue'),
          meta: { domain: 'anagrafiche', menuKey: 'titoli-iva-sfondati' }
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
        // Conversioni e Tipi UdM sono diventati due SCHEDE di
        // `catalogo/unita-misura` il 2026-09-04 (le tre tabelle sono un
        // soggetto solo). ⛔ I due indirizzi restano come redirect, e non e'
        // cortesia verso i vecchi link: i PREFERITI dell'operatore sono path
        // salvati in localStorage (`useNavigationFavorites`) — chi aveva messo
        // «Tipi UdM» fra i preferiti se lo ritroverebbe rotto, e nessun test lo
        // vedrebbe. Il `?tab=` porta sulla scheda giusta.
        {
          path: 'catalogo/conversioni-uom',
          name: 'catalogo-conversioni-uom',
          redirect: { name: 'catalogo-unita-misura', query: { tab: UOM_TABS.CONVERSIONI } }
        },
        {
          path: 'catalogo/uom-tipi',
          name: 'catalogo-uom-tipi',
          redirect: { name: 'catalogo-unita-misura', query: { tab: UOM_TABS.TIPI } }
        },

        // --- Vendite ---
        {
          path: 'vendite/situazione-aperta',
          name: 'vendite-situazione-aperta',
          component: () => import('../vendite/views/SituazioneApertaView.vue'),
          meta: { domain: 'vendite', menuKey: 'situazione-aperta' }
        },
        {
          path: 'vendite/dashboard-competenza',
          name: 'vendite-dashboard-competenza',
          component: () => import('../vendite/views/DashboardCompetenzaView.vue'),
          meta: { domain: 'vendite', menuKey: 'dashboard-competenza' }
        },
        {
          path: 'vendite/dashboard-backlog',
          name: 'vendite-dashboard-backlog',
          component: () => import('../vendite/views/DashboardBacklogView.vue'),
          meta: { domain: 'vendite', menuKey: 'dashboard-backlog' }
        },
        {
          path: 'vendite/lotti',
          name: 'vendite-lotti',
          component: () => import('../vendite/views/LottiListView.vue'),
          meta: { domain: 'vendite', menuKey: 'lotti' }
        },
        {
          // Tool della fatturazione: contenitore a tab degli elenchi che il
          // giro automatico lascia a una persona. Prima voce: i fondi fattura
          // da decidere. Sta sotto `vendite` e non sotto `strumenti` perche' i
          // dati sono di area vendite (RLS + perimetro emittente): la voce di
          // menu e i suoi cancelli devono stare nella stessa area.
          path: 'vendite/tool-fatturazione',
          name: 'vendite-tool-fatturazione',
          component: () => import('../vendite/views/ToolFatturazioneView.vue'),
          meta: { domain: 'vendite', menuKey: 'tool-fatturazione' }
        },
        {
          // Strumenti → Code di lavoro: vista completa a due tab (coda lavori
          // generica + coda stampa). Accesso primario dal badge top bar.
          path: 'strumenti/code-lavoro',
          name: 'strumenti-code-lavoro',
          component: () => import('../strumenti/views/CodeLavoroView.vue'),
          meta: { domain: 'strumenti', menuKey: 'code-lavoro' }
        },
        {
          // Strumenti → Giornale eventi: la vista e il client restano in
          // `vendite/` perche' dati ed endpoint sono di area vendite; qui sta
          // solo la porta di menu (cancello: `requireArea` sulla voce).
          path: 'strumenti/giornale',
          name: 'strumenti-giornale',
          component: () => import('../vendite/views/GiornaleListView.vue'),
          meta: { domain: 'strumenti', menuKey: 'giornale' }
        },
        {
          // Strumenti → Email: le mail dell'operatore, voce senza area
          // (`skip_area_check` BE): la vede ogni operatore.
          path: 'strumenti/email',
          name: 'strumenti-email',
          component: () => import('../strumenti/views/EmailLogView.vue'),
          meta: { domain: 'strumenti', menuKey: 'email' }
        },
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
          path: 'vendite/fatture',
          name: 'vendite-fatture',
          component: () => import('../vendite/views/FattureListView.vue'),
          meta: { domain: 'vendite', menuKey: 'fatture' }
        },
        // ── Incassi ───────────────────────────────────────────────
        {
          path: 'pagamenti/distinte',
          name: 'pagamenti-distinte',
          component: () => import('../pagamenti/views/DistinteListView.vue'),
          meta: { domain: 'pagamenti', menuKey: 'distinte' }
        },
        // ⭐ Due rotte, UNA vista: la coda che si apre la dice `meta.coda`
        // (Q-4 -> c). Cosi' le due porte sono deep-linkabili e distinguibili
        // nel tab, pur essendo la stessa lista con un filtro diverso.
        {
          path: 'pagamenti/righe/da-abbinare',
          name: 'pagamenti-coda-abbinare',
          component: () => import('../pagamenti/views/CodaRigheView.vue'),
          meta: { domain: 'pagamenti', menuKey: 'coda-abbinare', coda: CODE.DA_ABBINARE }
        },
        {
          path: 'pagamenti/righe/sospese',
          name: 'pagamenti-coda-sospese',
          component: () => import('../pagamenti/views/CodaRigheView.vue'),
          meta: { domain: 'pagamenti', menuKey: 'coda-sospese', coda: CODE.SOSPESE }
        },
        {
          path: 'pagamenti/rate-fuori-capienza',
          name: 'pagamenti-rate-fuori-capienza',
          component: () => import('../pagamenti/views/RateFuoriCapienzaView.vue'),
          meta: { domain: 'pagamenti', menuKey: 'rate-fuori-capienza' }
        },
        {
          path: 'pagamenti/eccedenze',
          name: 'pagamenti-eccedenze',
          component: () => import('../pagamenti/views/EccedenzeView.vue'),
          meta: { domain: 'pagamenti', menuKey: 'eccedenze' }
        },
        {
          path: 'pagamenti/canali-incasso',
          name: 'pagamenti-canali-incasso',
          component: () => import('../pagamenti/views/CanaliIncassoView.vue'),
          meta: { domain: 'pagamenti', menuKey: 'canali-incasso' }
        },
        // ── Magazzino ─────────────────────────────────────────────
        // ⭐ Due rotte, UNA vista per il documento interno: la famiglia che si
        //    apre la dice `meta.famiglia` (Q-1: inventario e rettifica sono una
        //    implementazione con due configurazioni, `FAMIGLIE` di
        //    `magazzino/vocabolari.js`). Le due porte restano deep-linkabili e
        //    distinguibili nel tab, come le due code degli incassi.
        // L'anagrafica dei magazzini (2026-09-21, piano anagrafiche-fuori-dal-
        // pannello-config): prima voce del dominio, le anagrafiche precedono
        // i documenti (Q-4).
        {
          path: 'magazzino/magazzini',
          name: 'magazzino-magazzini',
          component: () => import('../magazzino/views/MagazziniListView.vue'),
          meta: { domain: 'magazzino', menuKey: 'magazzini' }
        },
        {
          path: 'magazzino/inventari',
          name: 'magazzino-inventari',
          component: () => import('../magazzino/views/DocumentiInterniListView.vue'),
          meta: { domain: 'magazzino', menuKey: 'inventari', famiglia: FAMIGLIA.INVENTARI }
        },
        {
          path: 'magazzino/rettifiche',
          name: 'magazzino-rettifiche',
          component: () => import('../magazzino/views/DocumentiInterniListView.vue'),
          meta: { domain: 'magazzino', menuKey: 'rettifiche', famiglia: FAMIGLIA.RETTIFICHE }
        },
        {
          path: 'magazzino/disponibilita',
          name: 'magazzino-disponibilita',
          component: () => import('../magazzino/views/DisponibilitaView.vue'),
          meta: { domain: 'magazzino', menuKey: 'disponibilita' }
        },
        {
          // Il registro: sola lettura per costruzione (la porta e' la primitiva
          // del DB). Accetta il deep-link `?inventario_id=` / `?rettifica_id=`
          // dal documento POSTED.
          path: 'magazzino/movimenti',
          name: 'magazzino-movimenti',
          component: () => import('../magazzino/views/MovimentiView.vue'),
          meta: { domain: 'magazzino', menuKey: 'movimenti' }
        },
        {
          path: 'vendite/ddt',
          name: 'vendite-ddt',
          component: () => import('../vendite/ddt/views/DdtView.vue'),
          meta: { domain: 'vendite', menuKey: 'ddt' }
        },
        {
          path: 'vendite/resi',
          name: 'vendite-resi',
          component: () => import('../vendite/resi/views/ResiView.vue'),
          meta: { domain: 'vendite', menuKey: 'resi' }
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
          meta: { domain: 'home', errorKey: 'forbidden', errorIcon: STATUS_ICONS.VIETATO }
        },

        // --- Catch-all 404 ---
        {
          path: ':pathMatch(.*)*',
          name: 'not-found',
          component: () => import('../core/views/ErrorView.vue'),
          meta: { domain: 'home', errorKey: 'not_found', errorIcon: STATUS_ICONS.NON_TROVATO }
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
    // ⛔ «Sei già dentro, torna alla home» NON vale quando è l'applicazione
    //    stessa a dichiarare la sessione morta (`reason=` con un motivo di
    //    `MOTIVO_USCITA`: lo mandano l'interceptor 401, il logout di un'altra
    //    scheda e questo guard). Un access in memoria può
    //    essere non scaduto e già rifiutato dal server (sessione revocata),
    //    quindi il rimbalzo scattava e il login diventava irraggiungibile —
    //    l'operatore restava su una home che rispondeva 401 a ogni gesto e ne
    //    usciva solo ricaricando (rilievo di Tid, 2026-09-04).
    // ⚠️ È la seconda metà della correzione, non un doppione: la prima azzera
    //    lo stato nello store (`redirectToLogin` in `core/uscitaSessione.js`), questa
    //    impedisce che una sessione creduta viva per qualunque ALTRA ragione
    //    ci rimandi indietro. Chi ha una sessione viva e digita /login
    //    continua a essere riportato alla home.
    const sessioneDichiarataMorta = sessioneDichiarataChiusa(to.query.reason)
    // ⭐ Dal 2026-09-28 l'access sta solo in memoria: al ricaricamento non c'è
    //    mai, e se la sessione è viva lo si sa solo chiedendolo al backend
    //    (rinnovo dal cookie HttpOnly). Si chiede solo per il login: le altre
    //    rotte pubbliche (reset, attivazione) non ne hanno bisogno.
    if (
      to.name === 'login' &&
      !sessioneDichiarataMorta &&
      (await auth.ripristinaSessione())
    ) {
      return { name: 'home' }
    }
    return
  }

  // Sessione assente o morta -> login (vale per requiresAuth e rotte layout).
  // `ripristinaSessione` usa l'access in memoria se è valido, altrimenti
  // rinnova dal cookie del refresh: al ricaricamento della pagina, o dopo i
  // 10 minuti dell'access, è qui che la sessione si ritrova. Se il rinnovo
  // fallisce (cookie assente, scaduto, revocato) si va al login con
  // reason=session_expired (`MOTIVO_USCITA.SESSIONE_SCADUTA`). Sostituisce il vecchio «refresh proattivo», che
  // guardava la scadenza del refresh in localStorage.
  if (!(await auth.ripristinaSessione())) {
    const query = { reason: MOTIVO_USCITA.SESSIONE_SCADUTA }
    if (to.fullPath !== '/') query.redirect = to.fullPath
    return { name: 'login', query }
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

  // Guard secondo fattore obbligatorio e non configurato: dopo la password,
  // nell'ordine del cancello degli obblighi del backend (`obblighi_pendenti`
  // di `/core/me/`). La destinazione resta in `redirect`.
  if (auth.mustConfigureSecondFactor && to.name !== 'sicurezza') {
    const query = to.fullPath !== '/' ? { redirect: to.fullPath } : {}
    return { name: 'sicurezza', query }
  }

  // §8.5.4/§8.5.5 — Namespace multi-canale. Un utente autenticato puo'
  // navigare solo dentro il proprio namespace (`admin` per operatori,
  // `portale` per CLIENTE/FORNITORE_PORTALE, `shop` per SHOP_CUSTOMER).
  // Regole:
  //   - rotte universali (cambio password, forbidden, 404) esentate;
  //   - veste senza namespace FE (API_CLIENT) → forbidden;
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

  // ⭐ Le misure «righe per pagina» (catalogo DB, BB `core/misurePagina`):
  //    una volta per sessione, ATTESE, prima di qualunque rotta sotto
  //    `AppLayout` — anche 404 e forbidden, perche' e' il LAYOUT a leggerle
  //    (la ricerca della topbar), non solo le liste. Solo per l'operatore: e'
  //    la veste di quel layout, e l'endpoint e' della sua API.
  //    ⛔ Nessun ripiego se la chiamata fallisce (sarebbe una copia del
  //    catalogo): si apre la pagina d'errore, fuori dal layout.
  if (
    to.matched.some((r) => r.components?.default === AppLayout) &&
    resolveRuoloFeConfig(auth.ruoloApplicativo)?.namespace === FE_NAMESPACE.ADMIN
  ) {
    try {
      await caricaMisurePagina()
    } catch {
      return { name: ROTTA_AVVIO_NON_RIUSCITO }
    }
  }

  // Guard dominio admin: controlla permesso (solo namespace operatore)
  const domain = to.meta.domain
  if (domain === 'amm-software' && !auth.isSuperAdmin) {
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

  // Guard di VOCE: i cancelli `requireArea`/`requireAnyAction` della voce di
  // menu, con la stessa regola della sidebar (BB `isMenuItemAllowed`). Serve ai
  // domini che portano l'area sulle voci e non su di se' (Strumenti): senza,
  // la pagina si aprirebbe dall'indirizzo e il backend risponderebbe 403.
  // Una rotta senza voce di menu (dettagli, pagine errore) non ha cancello qui.
  const menuItem = findMenuItem(domain, to.meta.menuKey)
  if (menuItem && !isMenuItemAllowed(menuItem, auth)) {
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
  // ⭐ E' L'UNICO PUNTO CHE APRE LE SCHEDE: sidebar, preferiti e widget fanno
  //    solo `router.push`. Fino al 2026-09-30 aprivano anche loro, prima del
  //    push, e il guard riapriva: con una conferma in mezzo sarebbero state
  //    due dialog per un clic. Oltre il limite si sostituisce l'ultima in fila,
  //    se l'operatore conferma; «Annulla» lo lascia dov'era.
  if (domain && domain !== 'home' && to.name !== 'forbidden' && to.name !== 'not-found') {
    const tabs = useTabsStore()
    const daSostituire = tabs.schedaDaSostituire(to.path)
    if (daSostituire) {
      const conferma = await tabs.chiediSostituzione(daSostituire)
      if (!conferma) return false
      tabs.removeTab(daSostituire.id)
    }
    const opened = tabs.openTab({
      path: to.path,
      label: resolveTabLabel(to.meta, t) || to.path,
      domain: domain,
      menuKey: to.meta.menuKey || null,
      icon: resolveTabIcon(to.meta)
    })
    if (!opened) return false
  }
})

// ⭐ CHIUSURA GLOBALE DEI DRAWER a ogni cambio di PAGINA.
// I drawer sono teleportati sul body e le view vivono sotto KeepAlive: senza
// questo, cambiare rotta lascia la pila di pannelli aperta DAVANTI alla pagina
// d'arrivo — misurato in-app il 2026-08-19 partendo dal «apri la coda filtrata»
// del pannello merce, con ordine e DDT ancora impilati sopra la coda.
//
// ⚠️ `afterEach` e non `beforeEach`: si chiude solo quando la navigazione e'
// davvero avvenuta. Il guard sopra puo' ancora rifiutarla (limite tab
// raggiunto, area bloccata, redirect al login) e chiudere i drawer di una
// navigazione poi annullata significherebbe far sparire il pannello su cui
// l'utente sta lavorando senza che si sia mosso nulla.
//
// ⚠️ Solo sul PATH, mai sulla query: le liste sincronizzano filtri e ripuliscono
// i deep-link con `router.replace` sulla stessa pagina (es. la coda accrediti
// che toglie `ddt_id` dall'URL). Chiudere li' sarebbe un drawer che si chiude
// da solo mentre si filtra.
router.afterEach((to, from) => {
  if (to.path !== from.path) chiudiTuttiIDrawer()
})

export default router

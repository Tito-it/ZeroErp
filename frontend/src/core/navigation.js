// Configurazione centralizzata della navigazione per dominio.
// Sidebar, HomeView e store navigation leggono da qui — un'unica fonte di verita'.

import { READONLY_DOMAINS } from './constants'

export const NAV_ICONS = Object.freeze({
  ANAGRAFICHE: 'pi pi-users',
  CATALOGO: 'pi pi-box',
  VENDITE: 'pi pi-shopping-cart',
  ACQUISTI: 'pi pi-shopping-bag',
  MAGAZZINO: 'pi pi-warehouse',
  PAGAMENTI: 'pi pi-credit-card',
  CONTABILITA: 'pi pi-calculator',
  PRATICHE: 'pi pi-folder',
  CONFIG: 'pi pi-cog',
  AMM_SOFTWARE: 'pi pi-lock',

  TABELLE: 'pi pi-table',
  IMPOSTAZIONI: 'pi pi-sliders-h',
  CONFIG_DOCUMENTI: 'app-nav-icon app-nav-icon-documenti',
  PREVENTIVI: 'app-nav-icon app-nav-icon-preventivi',
  OFFERTE: 'app-nav-icon app-nav-icon-offerte',
  ORDINI: 'app-nav-icon app-nav-icon-ordini',
  CONTRATTI: 'app-nav-icon app-nav-icon-contratti',
  DDT: 'app-nav-icon app-nav-icon-ddt',
  RESI: 'app-nav-icon app-nav-icon-resi',
  FATTURE: 'app-nav-icon app-nav-icon-fatture',
  LISTINI: 'app-nav-icon app-nav-icon-listini',
  APPROVAZIONI_PREZZO: 'app-nav-icon app-nav-icon-approvazioni-prezzo',
  SITUAZIONE_APERTA: 'pi pi-chart-pie',
  DASHBOARD_COMPETENZA: 'pi pi-chart-bar',
  DASHBOARD_BACKLOG: 'pi pi-inbox',
  LOTTI: 'pi pi-server',
  PROMO_ARTICOLI: 'app-nav-icon app-nav-icon-promo-articoli',
  PERSONALIZZAZIONI_LISTE: 'pi pi-th-large',
  HOME: 'pi pi-home',
  BACK: 'pi pi-arrow-left',

  KEY: 'pi pi-key',
  SEARCH: 'pi pi-search',
  SITEMAP: 'pi pi-sitemap',
  SHIELD: 'pi pi-shield',
  ID_CARD: 'pi pi-id-card',
  TAGS: 'pi pi-tags',
  HISTORY: 'pi pi-history',
  AT: 'pi pi-at',
  FILE_EDIT: 'pi pi-file-edit',
  ENVELOPE: 'pi pi-envelope',
  // Anagrafiche: icone dedicate per le 3 liste root del modulo.
  // Soggetti = pi pi-users (omini, "anagrafe generale").
  // Clienti = icona composta receipt+user ("chi riceve fattura").
  // Fornitori = icona composta building+user ("azienda + persona di riferimento").
  CLIENTI: 'app-nav-icon app-nav-icon-clienti',
  FORNITORI: 'app-nav-icon app-nav-icon-fornitori',
  // Amministrazione operatori (singolo utente tecnico, distinto da
  // ANAGRAFICHE che usa pi-users per la rubrica multi-soggetto).
  OPERATORE: 'pi pi-user',
  // Toponomastica / gestione indirizzi (drawer dedicati in core/components).
  // pi-building per il comune (edificio civico, distinto dal fornitore
  // che usa l'icona composta building+user). pi-globe condiviso tra
  // provincia/regione/stato (gerarchia geografica omogenea).
  INDIRIZZO: 'pi pi-map-marker',
  TOPONOMASTICA: 'pi pi-directions',
  COMUNE: 'pi pi-building',
  CAP: 'pi pi-inbox',
  PROVINCIA: 'pi pi-globe',
  REGIONE: 'pi pi-globe',
  STATO: 'pi pi-globe',
  MAP_MARKER: 'pi pi-map-marker',
  ARROWS_H: 'pi pi-arrows-h',
  SYNC: 'pi pi-sync',
  FILE: 'pi pi-file',
  TAG: 'pi pi-tag',
  PERCENTAGE: 'pi pi-percentage',
  CHECK_CIRCLE: 'pi pi-check-circle',
  FOLDER_OPEN: 'pi pi-folder-open',
})
//
// --- Convenzioni route meta ---
// Ogni route autenticata DEVE avere meta.domain (stringa, es. 'vendite').
// Meta fields riconosciuti:
//   domain    (string, obbligatorio)  — identifica il dominio; guida sidebar, breadcrumb, tab label
//   menuKey   (string, opzionale)     — voce L2 del dominio; usato per tab label e breadcrumb secondo segmento
//   errorKey  (string, opzionale)     — solo pagine errore: 'not_found' | 'forbidden'; risolve errors.${errorKey}_title
//   errorIcon (string, opzionale)     — icona PrimeIcon per pagine errore
//   public    (boolean, opzionale)    — true solo su /login; salta il guard autenticazione
//
// --- Aggiungere un nuovo dominio ---
// 1. Aggiungere entry in DOMAINS (key, icon, to)
// 2. Aggiungere array voci in DOMAIN_MENUS (anche vuoto)
// 3. Aggiungere chiavi i18n: nav.<domainKey> e nav_menu.<domainKey>.<itemKey>
// 4. Aggiungere route in router/index.js con meta { domain, menuKey }
//    - Per placeholder: usa PlaceholderView.vue (chiave i18n derivata da domain_menuKey con hyphen→underscore)
//    - Per pagine reali: importa il componente specifico
// 5. Se il dominio ha voci L2, aggiungerlo a domainsWithRoutes nel router

export const DOMAINS = [
  { key: 'anagrafiche', icon: NAV_ICONS.ANAGRAFICHE, to: '/anagrafiche', schemaDb: 'anagrafiche' },
  { key: 'catalogo', icon: NAV_ICONS.CATALOGO, to: '/catalogo', schemaDb: 'catalogo' },
  { key: 'vendite', icon: NAV_ICONS.VENDITE, to: '/vendite', schemaDb: 'vendite' },
  { key: 'acquisti', icon: NAV_ICONS.ACQUISTI, to: '/acquisti', schemaDb: 'acquisti' },
  { key: 'magazzino', icon: NAV_ICONS.MAGAZZINO, to: '/magazzino', schemaDb: 'magazzino' },
  { key: 'pagamenti', icon: NAV_ICONS.PAGAMENTI, to: '/pagamenti', schemaDb: 'pagamenti' },
  { key: 'contabilita', icon: NAV_ICONS.CONTABILITA, to: '/contabilita', schemaDb: 'contabilita' },
  { key: 'pratiche', icon: NAV_ICONS.PRATICHE, to: '/pratiche', schemaDb: 'pratiche' },
  { key: 'config', icon: NAV_ICONS.CONFIG, to: '/config', schemaDb: 'config' },
  { key: 'amm-software', icon: NAV_ICONS.AMM_SOFTWARE, to: '/amm-software', adminOnly: true, schemaDb: 'amm_software' }
]

// Voci menu L2 per ogni dominio (sidebar stato DOMINIO).
// La label viene da i18n `nav_menu.<domainKey>.<itemKey>`
//
// Campi voce:
//   key, icon, to, children   — vedi commenti sopra
//   requireArea (opzionale)   — schema_db dell'area BE che deve NON essere
//                               BLOCCATA per rendere visibile la voce. Serve
//                               quando una voce di menu sotto un dominio
//                               punta a entita' di un altro schema/area
//                               (es. "Configurazione documenti" sotto
//                               dominio config ma area BE `documenti`).
//                               Senza questo, la voce resta visibile a chi
//                               accede al dominio padre ma non ha l'area
//                               della voce, generando 403 al click.
//                               Filter applicato lato sidebar.
//   requireAnyAction (opzionale, array stringhe) — codename azioni di
//                               processo. La voce e' visibile se utente
//                               admin o se almeno una delle azioni e'
//                               abilitata. Filter applicato lato sidebar.
export const DOMAIN_MENUS = {
  'amm-software': [
    { key: 'operatori', icon: NAV_ICONS.KEY, to: '/amm-software/operatori' },
    { key: 'profili-reparto', icon: NAV_ICONS.SITEMAP, to: '/amm-software/profili-reparto' },
    { key: 'permessi', icon: NAV_ICONS.SHIELD, to: '/amm-software/permessi' },
    { key: 'emittenti-fiscali', icon: NAV_ICONS.ID_CARD, to: '/amm-software/emittenti-fiscali' },
    { key: 'categorie-clienti', icon: NAV_ICONS.TAGS, to: '/amm-software/categorie-clienti' },
    { key: 'definizioni-workflow', icon: NAV_ICONS.SITEMAP, to: '/amm-software/definizioni-workflow' },
    { key: 'matrici', icon: NAV_ICONS.TABELLE, to: '/amm-software/matrici' },
    { key: 'audit-log', icon: NAV_ICONS.HISTORY, to: '/amm-software/audit-log' },
    { key: 'email-accounts', icon: NAV_ICONS.AT, to: '/amm-software/email-accounts' },
    { key: 'email-templates', icon: NAV_ICONS.FILE_EDIT, to: '/amm-software/email-templates' },
    { key: 'email-log', icon: NAV_ICONS.ENVELOPE, to: '/amm-software/email-log' },
    {
      key: 'personalizzazioni-liste-tecniche',
      icon: NAV_ICONS.PERSONALIZZAZIONI_LISTE,
      to: '/amm-software/personalizzazioni-liste-tecniche',
      // Pagina tecnica SUPER_ADMIN-only: voce visibile solo per admin
      // (BE: AdminAPIView bocca chi non e' SUPER_ADMIN). Coerente con il
      // dominio amm-software gia' marcato adminOnly nei DOMAINS.
    }
  ],
  'anagrafiche': [
    { key: 'soggetti', icon: NAV_ICONS.ANAGRAFICHE, to: '/anagrafiche/soggetti' },
    { key: 'clienti', icon: NAV_ICONS.CLIENTI, to: '/anagrafiche/clienti' },
    { key: 'fornitori', icon: NAV_ICONS.FORNITORI, to: '/anagrafiche/fornitori' },
    { key: 'indirizzi', icon: NAV_ICONS.MAP_MARKER, to: '/anagrafiche/indirizzi' }
  ],
  'catalogo': [
    { key: 'articoli', icon: NAV_ICONS.CATALOGO, to: '/catalogo/articoli' },
    { key: 'unita-misura', icon: NAV_ICONS.ARROWS_H, to: '/catalogo/unita-misura' },
    { key: 'conversioni-uom', icon: NAV_ICONS.SYNC, to: '/catalogo/conversioni-uom' },
    { key: 'uom-tipi', icon: NAV_ICONS.TAGS, to: '/catalogo/uom-tipi' }
  ],
  'vendite': [
    { key: 'situazione-aperta', icon: NAV_ICONS.SITUAZIONE_APERTA, to: '/vendite/situazione-aperta' },
    { key: 'dashboard-competenza', icon: NAV_ICONS.DASHBOARD_COMPETENZA, to: '/vendite/dashboard-competenza' },
    { key: 'dashboard-backlog', icon: NAV_ICONS.DASHBOARD_BACKLOG, to: '/vendite/dashboard-backlog' },
    { key: 'lotti', icon: NAV_ICONS.LOTTI, to: '/vendite/lotti' },
    { key: 'preventivi', icon: NAV_ICONS.PREVENTIVI, to: '/vendite/preventivi' },
    { key: 'offerte', icon: NAV_ICONS.OFFERTE, to: '/vendite/offerte' },
    { key: 'ordini', icon: NAV_ICONS.ORDINI, to: '/vendite/ordini' },
    { key: 'ddt', icon: NAV_ICONS.DDT, to: '/vendite/ddt' },
    { key: 'resi', icon: NAV_ICONS.RESI, to: '/vendite/resi' },
    { key: 'contratti', icon: NAV_ICONS.CONTRATTI, to: '/vendite/contratti' },
    { key: 'listini', icon: NAV_ICONS.LISTINI, to: '/vendite/listini' },
    { key: 'promo-articoli', icon: NAV_ICONS.PROMO_ARTICOLI, to: '/vendite/promo-articoli' },
    { key: 'approvazioni-prezzo', icon: NAV_ICONS.APPROVAZIONI_PREZZO, to: '/vendite/approvazioni-prezzo' }
  ],
  'acquisti': [],
  'magazzino': [],
  'pagamenti': [],
  'contabilita': [],
  'pratiche': [
    { key: 'home', icon: NAV_ICONS.HOME, to: '/pratiche' },
    { key: 'gestione', icon: NAV_ICONS.FOLDER_OPEN, to: '/pratiche/gestione' }
  ],
  'config': [
    { key: 'tabelle', icon: NAV_ICONS.TABELLE, to: '/config/tabelle' },
    { key: 'impostazioni', icon: NAV_ICONS.IMPOSTAZIONI, to: '/config/impostazioni' },
    {
      key: 'config-documenti',
      icon: NAV_ICONS.CONFIG_DOCUMENTI,
      to: '/config/documenti',
      // Le entita' gestite (template_documenti, template_asset) sono in
      // schema/area `documenti`; la voce sta sotto config solo per UX.
      requireArea: READONLY_DOMAINS.DOCUMENTI,
    },
    {
      key: 'personalizzazioni-liste',
      icon: NAV_ICONS.PERSONALIZZAZIONI_LISTE,
      to: '/config/personalizzazioni-liste',
      // La voce e' visibile solo a chi ha almeno una delle 2 azioni di
      // processo Blocco F (oppure all'admin che bypassa). Tenant admin
      // non autorizzati non la vedono nemmeno (defense-in-depth UI).
      requireAnyAction: ['ui_preset_manage', 'ui_permesso_manage'],
    }
  ]
}

// Voce sidebar home (usata dal SidebarDomain per il pulsante indietro)
export const HOME_ITEM = { key: 'home', icon: NAV_ICONS.HOME, to: '/' }

// Risolve la label tab/breadcrumb dalla route meta usando i18n.
// Usato da router guard e AppBreadcrumb per evitare duplicazione.
export function resolveNavigationLabel({ domain, menuKey }, t, te = null) {
  if (menuKey && domain) {
    const key = `nav_menu.${domain}.${menuKey}`
    if (!te || te(key)) return t(key)
  }
  if (domain && domain !== 'home') {
    const key = `nav.${domain}`
    if (!te || te(key)) return t(key)
  }
  return null
}

// Risolve la label tab/breadcrumb dalla route meta usando i18n.
// Usato da router guard, AppBreadcrumb, SidebarDomain e ContentTabs per
// mantenere le label allineate alla sidebar.
export function resolveTabLabel(meta, t, te = null) {
  return resolveNavigationLabel(meta, t, te)
}

// Risolve l'icona tab dalla route meta.
// Cerca prima nelle voci L2 (DOMAIN_MENUS), poi nel dominio (DOMAINS).
export function resolveTabIcon(meta) {
  const { domain, menuKey } = meta
  if (menuKey && DOMAIN_MENUS[domain]) {
    const item = DOMAIN_MENUS[domain]
      .flatMap(m => m.children ? [m, ...m.children] : [m])
      .find(m => m.key === menuKey)
    if (item) return item.icon
  }
  if (domain) {
    const d = DOMAINS.find(d => d.key === domain)
    if (d) return d.icon
  }
  return null
}

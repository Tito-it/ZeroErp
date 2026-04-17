// Configurazione centralizzata della navigazione per dominio.
// Sidebar, HomeView e store navigation leggono da qui — un'unica fonte di verita'.
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
  { key: 'anagrafiche', icon: 'pi pi-users', to: '/anagrafiche', schemaDb: 'anagrafiche' },
  { key: 'catalogo', icon: 'pi pi-box', to: '/catalogo', schemaDb: 'catalogo' },
  { key: 'vendite', icon: 'pi pi-shopping-cart', to: '/vendite', schemaDb: 'vendite' },
  { key: 'acquisti', icon: 'pi pi-shopping-bag', to: '/acquisti', schemaDb: 'acquisti' },
  { key: 'magazzino', icon: 'pi pi-warehouse', to: '/magazzino', schemaDb: 'magazzino' },
  { key: 'pagamenti', icon: 'pi pi-credit-card', to: '/pagamenti', schemaDb: 'pagamenti' },
  { key: 'contabilita', icon: 'pi pi-calculator', to: '/contabilita', schemaDb: 'contabilita' },
  { key: 'pratiche', icon: 'pi pi-folder', to: '/pratiche', schemaDb: 'pratiche' },
  { key: 'config', icon: 'pi pi-cog', to: '/config', schemaDb: 'config' },
  { key: 'amm-software', icon: 'pi pi-lock', to: '/amm-software', adminOnly: true, schemaDb: 'amm_software' }
]

// Voci menu L2 per ogni dominio (sidebar stato DOMINIO).
// La label viene da i18n `nav_menu.<domainKey>.<itemKey>`
export const DOMAIN_MENUS = {
  'amm-software': [
    { key: 'operatori', icon: 'pi pi-key', to: '/amm-software/operatori' },
    { key: 'profili-reparto', icon: 'pi pi-sitemap', to: '/amm-software/profili-reparto' },
    { key: 'permessi', icon: 'pi pi-shield', to: '/amm-software/permessi' },
    { key: 'emittenti-fiscali', icon: 'pi pi-id-card', to: '/amm-software/emittenti-fiscali' },
    { key: 'matrice-utilities-ruoli', icon: 'pi pi-table', to: '/amm-software/matrice-utilities-ruoli' },
    { key: 'matrice-indirizzi-ruoli', icon: 'pi pi-map', to: '/amm-software/matrice-indirizzi-ruoli' },
    { key: 'categorie-clienti', icon: 'pi pi-tags', to: '/amm-software/categorie-clienti' },
    { key: 'matrice-categorie-listini', icon: 'pi pi-th-large', to: '/amm-software/matrice-categorie-listini' },
    { key: 'audit-log', icon: 'pi pi-history', to: '/amm-software/audit-log' },
    { key: 'email-accounts', icon: 'pi pi-at', to: '/amm-software/email-accounts' },
    { key: 'email-templates', icon: 'pi pi-file-edit', to: '/amm-software/email-templates' },
    { key: 'email-log', icon: 'pi pi-envelope', to: '/amm-software/email-log' }
  ],
  'anagrafiche': [
    { key: 'soggetti', icon: 'pi pi-users', to: '/anagrafiche/soggetti' },
    { key: 'clienti', icon: 'pi pi-briefcase', to: '/anagrafiche/clienti' },
    { key: 'fornitori', icon: 'pi pi-clipboard', to: '/anagrafiche/fornitori' },
    { key: 'indirizzi', icon: 'pi pi-map-marker', to: '/anagrafiche/indirizzi' }
  ],
  'catalogo': [
    { key: 'articoli', icon: 'pi pi-box', to: '/catalogo/articoli' },
    { key: 'unita-misura', icon: 'pi pi-arrows-h', to: '/catalogo/unita-misura' },
    { key: 'conversioni-uom', icon: 'pi pi-sync', to: '/catalogo/conversioni-uom' }
  ],
  'vendite': [
    { key: 'preventivi', icon: 'pi pi-file', to: '/vendite/preventivi' },
    { key: 'listini', icon: 'pi pi-tag', to: '/vendite/listini' },
    { key: 'contratti', icon: 'pi pi-file-edit', to: '/vendite/contratti' },
    { key: 'promo-articoli', icon: 'pi pi-percentage', to: '/vendite/promo-articoli' }
  ],
  'acquisti': [],
  'magazzino': [],
  'pagamenti': [],
  'contabilita': [],
  'pratiche': [
    { key: 'gestione', icon: 'pi pi-folder-open', to: '/pratiche' }
  ],
  'config': [
    { key: 'tabelle', icon: 'pi pi-table', to: '/config/tabelle' },
    { key: 'impostazioni', icon: 'pi pi-sliders-h', to: '/config/impostazioni' }
  ]
}

// Voce sidebar home (usata dal SidebarDomain per il pulsante indietro)
export const HOME_ITEM = { key: 'home', icon: 'pi pi-home', to: '/' }

// Risolve la label tab/breadcrumb dalla route meta usando i18n.
// Usato da router guard e AppBreadcrumb per evitare duplicazione.
export function resolveTabLabel(meta, t) {
  const { domain, menuKey } = meta
  if (menuKey) return t(`nav_menu.${domain}.${menuKey}`)
  if (domain && domain !== 'home') return t(`nav.${domain}`)
  return null
}

// Risolve l'icona tab dalla route meta.
// Cerca prima nelle voci L2 (DOMAIN_MENUS), poi nel dominio (DOMAINS).
export function resolveTabIcon(meta) {
  const { domain, menuKey } = meta
  if (menuKey && DOMAIN_MENUS[domain]) {
    const item = DOMAIN_MENUS[domain].find(m => m.key === menuKey)
    if (item) return item.icon
  }
  if (domain) {
    const d = DOMAINS.find(d => d.key === domain)
    if (d) return d.icon
  }
  return null
}

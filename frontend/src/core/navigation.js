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
  { key: 'anagrafiche', icon: 'pi pi-users', to: '/anagrafiche' },
  { key: 'catalogo', icon: 'pi pi-box', to: '/catalogo' },
  { key: 'vendite', icon: 'pi pi-shopping-cart', to: '/vendite' },
  { key: 'acquisti', icon: 'pi pi-shopping-bag', to: '/acquisti' },
  { key: 'magazzino', icon: 'pi pi-warehouse', to: '/magazzino' },
  { key: 'pagamenti', icon: 'pi pi-credit-card', to: '/pagamenti' },
  { key: 'contabilita', icon: 'pi pi-calculator', to: '/contabilita' },
  { key: 'pratiche', icon: 'pi pi-folder', to: '/pratiche' },
  { key: 'config', icon: 'pi pi-cog', to: '/config' },
  { key: 'amm-software', icon: 'pi pi-lock', to: '/amm-software', adminOnly: true }
]

// Voci menu L2 per ogni dominio (sidebar stato DOMINIO).
// La label viene da i18n `nav_menu.<domainKey>.<itemKey>`
export const DOMAIN_MENUS = {
  'amm-software': [
    { key: 'operatori', icon: 'pi pi-wrench', to: '/amm-software/operatori' },
    { key: 'profili-reparto', icon: 'pi pi-wrench', to: '/amm-software/profili-reparto' },
    { key: 'permessi', icon: 'pi pi-wrench', to: '/amm-software/permessi' },
    { key: 'audit-log', icon: 'pi pi-wrench', to: '/amm-software/audit-log' }
  ],
  'anagrafiche': [],
  'catalogo': [],
  'vendite': [],
  'acquisti': [],
  'magazzino': [],
  'pagamenti': [],
  'contabilita': [],
  'pratiche': [],
  'config': []
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

// Configurazione centralizzata della navigazione per dominio.
// Sidebar e HomeView leggono da qui — un'unica fonte di verita'.

export const DOMAINS = [
  { key: 'anagrafiche', icon: 'pi pi-users', to: '/anagrafiche' },
  { key: 'catalogo', icon: 'pi pi-box', to: '/catalogo' },
  { key: 'vendite', icon: 'pi pi-shopping-cart', to: '/vendite' },
  { key: 'acquisti', icon: 'pi pi-shopping-bag', to: '/acquisti' },
  { key: 'magazzino', icon: 'pi pi-warehouse', to: '/magazzino' },
  { key: 'pagamenti', icon: 'pi pi-credit-card', to: '/pagamenti' },
  { key: 'contabilita', icon: 'pi pi-calculator', to: '/contabilita' },
  { key: 'pratiche', icon: 'pi pi-folder', to: '/pratiche' },
  { key: 'config', icon: 'pi pi-cog', to: '/config' }
]

// Voci sidebar: home + domini
export const SIDEBAR_ITEMS = [
  { key: 'home', icon: 'pi pi-home', to: '/' },
  ...DOMAINS
]

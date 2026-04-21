// Larghezze drawer per tipologia di form
export const DRAWER_WIDTH = {
  SIMPLE: '480px',    // tabelle di lookup, config
  STANDARD: '640px',  // anagrafiche, catalogo
  COMPLEX: '800px',   // pratiche, contratti
  WIDE: '960px',      // ricerca universale, liste con dettaglio
  XLARGE: '1360px'    // matrici parametri-per-entita' (utility, slot/override)
}

// Durata toast in millisecondi
export const TOAST_DURATION = {
  SUCCESS: 3000,
  WARN: 4000,
  ERROR: 5000,
  SYSTEM_ERROR: 0  // 0 = persistente, chiusura manuale
}

// Codici interni tipi ruolo (codice_interno da config.tipi_ruoli — fissi e immutabili)
export const TIPO_RUOLO = {
  CLIENTE: 'CL',
  FORNITORE: 'FO',
  GESTORE: 'GE',
  VENDITORE: 'VE',
  DISTRIBUTORE: 'DI',
  RESELLER: 'RE',
  VETTORE: 'VT',
  EMITTENTE_FISCALE: 'EF',
  BANCA: 'BANK_B',
  RISORSA_UMANA: 'RIS_UMANA',
  PSP: 'PSP',
}

// Paginazione default
export const PAGINATION = {
  DEFAULT_ROWS: 25,
  ROWS_OPTIONS: [10, 25, 50, 100]
}

// Formato data (PrimeVue DatePicker dateFormat)
// dd/mm/yy = GG/MM/YYYY in PrimeVue ('yy' = anno a 4 cifre)
// Centralizzato: cambiare qui per aggiornare tutte le date del sistema.
export const DATE_FORMAT = 'dd/mm/yy'

// Content tabs
export const TABS = {
  MAX_OPEN: 10
}

// Breakpoint responsive (valori fissi usati nei @media e nello store ui)
export const BREAKPOINTS = {
  MOBILE: 768,
  TABLET: 1024,
  DESKTOP_SPLIT: 1280  // soglia minima per split view tab affiancate
}

// Lunghezze campo standard
export const FIELD_LENGTH = {
  IBAN_MAX: 34  // ISO 13616: max 34 caratteri alfanumerici
}

// Enum ruolo sistema LEGACY (allineato a config.ruolo_sistema nel DB).
// Mantenuto per retrocompat FE non ancora migrati al nuovo modello
// multi-face auth. Nuovi consumer usino RUOLO_APPLICATIVO + is_super_admin
// letti dal profilo /me/.
export const RUOLO_SISTEMA = {
  ADMIN: 'ADMIN',
  OPERATIVO: 'OPERATIVO',
  DISABILITATO: 'DISABILITATO'
}

// Enum ruolo applicativo (allineato a config.ruolo_applicativo nel DB).
// Categoria dell'identita' digitale dell'utente. Letto da
// anagrafiche.identita_digitali.ruolo_applicativo via GUC app.ruolo_applicativo
// e ricostruito a Python da PermissionResolver.get_ruolo_applicativo.
export const RUOLO_APPLICATIVO = {
  OPERATORE: 'OPERATORE',
  CLIENTE_PORTALE: 'CLIENTE_PORTALE',
  FORNITORE_PORTALE: 'FORNITORE_PORTALE',
  SHOP_CUSTOMER: 'SHOP_CUSTOMER',
  API_CLIENT: 'API_CLIENT',
  DISABILITATO: 'DISABILITATO'
}

// Canali di login (§8.5.1 multi-face auth). Il login dell'utente e' per
// "canale": a seconda del canale scelto il BE emette il JWT con la veste
// `ruolo_applicativo` corretta (OPERATORE / CLIENTE_PORTALE+FORNITORE_PORTALE /
// SHOP_CUSTOMER) e il FE naviga sul namespace appropriato.
//
// Ogni canale espone:
//   - `key`       identificativo interno (usato come valore v-model del radio)
//   - `tokenPath` path dell'endpoint token REST (`/admin/token/`, ...)
//   - `i18n`      chiave i18n per la label radio
//
// Il default del LoginView e' ADMIN per retrocompat (operatore interno).
// Consumer tipici: `ChannelSelector` + `useAuthStore.login(..., canale)`.
export const CANALE_LOGIN = {
  ADMIN: {
    key: 'ADMIN',
    tokenPath: '/admin/token/',
    refreshPath: '/admin/token/refresh/',
    i18n: 'auth.canale.admin'
  },
  PORTALE: {
    key: 'PORTALE',
    tokenPath: '/portale/token/',
    refreshPath: '/portale/token/refresh/',
    i18n: 'auth.canale.portale'
  },
  SHOP: {
    key: 'SHOP',
    tokenPath: '/shop/token/',
    refreshPath: '/shop/token/refresh/',
    i18n: 'auth.canale.shop'
  }
}

// Lista ordinata dei canali (ordine di visualizzazione nel radio).
// Il default del LoginView corrisponde al primo elemento.
export const CANALE_LOGIN_LIST = [
  CANALE_LOGIN.ADMIN,
  CANALE_LOGIN.PORTALE,
  CANALE_LOGIN.SHOP
]

// Scopo: Risolve un canale dalla sua key (es. 'ADMIN'). Ritorna il canale
// ADMIN come fallback se la key e' sconosciuta — scelta conservativa:
// un valore non riconosciuto non deve rompere il login, ridirige sul
// namespace operatore (piu' restrittivo a livello di permessi DB).
export function resolveCanaleLogin(key) {
  return CANALE_LOGIN[key] || CANALE_LOGIN.ADMIN
}

// Namespace FE per il routing multi-canale (§8.5.4/§8.5.5). Identifica
// il "canale di navigazione" di una rotta FE, distinto (ma allineato)
// ai namespace API BE (`/api/v1/{admin,portale,shop}/*`).
export const FE_NAMESPACE = {
  ADMIN: 'admin',
  PORTALE: 'portale',
  SHOP: 'shop'
}

// Mapping `ruolo_applicativo → config FE namespace`. Single source of
// truth usato dal router guard per determinare:
//   - quale namespace il ruolo puo' navigare (`namespace`)
//   - dove ridirigere il ruolo se approda su un namespace estraneo
//     (`homePath` + opzionale `homeRouteName` per evitare child-path
//     non gia' risolti come route name).
// Aggiungendo un ruolo qui, il guard del router lo supporta automaticamente
// senza toccare la logica di navigazione.
export const RUOLO_FE_NAMESPACE = {
  [RUOLO_APPLICATIVO.OPERATORE]: {
    namespace: FE_NAMESPACE.ADMIN,
    homePath: '/',
    homeRouteName: 'home'
  },
  [RUOLO_APPLICATIVO.CLIENTE_PORTALE]: {
    namespace: FE_NAMESPACE.PORTALE,
    homePath: '/portale'
  },
  [RUOLO_APPLICATIVO.FORNITORE_PORTALE]: {
    namespace: FE_NAMESPACE.PORTALE,
    homePath: '/portale'
  },
  [RUOLO_APPLICATIVO.SHOP_CUSTOMER]: {
    namespace: FE_NAMESPACE.SHOP,
    homePath: '/shop'
  }
}

// Scopo: Config FE namespace della veste corrente. Ritorna null per le
// vesti senza namespace FE (API_CLIENT, DISABILITATO, assente): il caller
// tipicamente traduce in `forbidden`.
export function resolveRuoloFeConfig(ruoloApplicativo) {
  return RUOLO_FE_NAMESPACE[ruoloApplicativo] || null
}

// Enum tipo profilo accesso (allineato a config.tipo_profilo_accesso nel DB).
// Usato dai profili accesso generalizzati (sostituiscono i vecchi profili reparto).
export const TIPO_PROFILO_ACCESSO = {
  REPARTO: 'REPARTO',
  PORTALE: 'PORTALE',
  AD_HOC: 'AD_HOC',
  SUPER_ADMIN: 'SUPER_ADMIN'
}

// Enum livello accesso (allineato a config.livello_accesso nel DB)
export const LIVELLO_ACCESSO = {
  TUTTO: 'TUTTO',
  LETTURA: 'LETTURA',
  BLOCCATO: 'BLOCCATO'
}

// Codici interni stati pratica (codice_interno da config.stati_pratiche — fissi e immutabili)
export const STATO_PRATICA = {
  BOZZA: 'BOZZA',
  APERTA: 'APERTA',
  SOSPESA: 'SOSPESA',
  CHIUSA: 'CHIUSA',
  ANNULLATA: 'ANNULLATA',
}

// Codici interni stati flusso pratica (codice_interno da config.stati_flussi_pratiche)
export const STATO_FLUSSO = {
  DA_ESEGUIRE: 'DA_ESEGUIRE',
  IN_CORSO: 'IN_CORSO',
  COMPLETATO: 'COMPLETATO',
  SOSPESO: 'SOSPESO',
  ANNULLATO: 'ANNULLATO',
  ERRORE: 'ERRORE',
}

// Codici interni stati preventivo vendita (codice_interno da config.stati_doc_preventivi)
export const STATO_PREVENTIVO = {
  BOZZA: 'DRAFT',
  EMESSO: 'EMESSO',
  ACCETTATO: 'ACCETTATO',
  RIFIUTATO: 'RIFIUTATO',
  SCADUTO: 'SCADUTO',
  ANNULLATO: 'ANNULLATO',
}

// Icone gestione riga — centralizzate per coerenza cross-dominio.
// Uso: <Button :icon="MANAGE_ICONS.CONTATTI" class="app-manage-btn" />
export const MANAGE_ICONS = {
  // Anagrafiche
  CONTATTI: 'pi pi-id-card',
  INDIRIZZI: 'pi pi-map-marker',
  CONTI_BANCARI: 'pi pi-wallet',
  // Catalogo
  UOM: 'pi pi-box',
  BOM: 'pi pi-sitemap',
  NOTE: 'pi pi-file-edit',
  CONVERSIONI: 'pi pi-sync',
  // Vendite
  VERSIONI: 'pi pi-history',
  ASSOCIAZIONI: 'pi pi-link',
  CONTRATTI: 'pi pi-file-edit',
  // Trasversali
  KEBAB: 'pi pi-ellipsis-v',
}

// Keyboard shortcuts
export const SHORTCUTS = {
  SEARCH: { key: 'k', ctrl: true, shift: false },
  NEXT_TAB: { key: 'Tab', ctrl: true, shift: false },
  PREV_TAB: { key: 'Tab', ctrl: true, shift: true },
  CLOSE_TAB: { key: 'w', ctrl: true, shift: false },
  TOGGLE_SIDEBAR: { key: 'b', ctrl: true, shift: false },
  GO_HOME: { key: 'Home', ctrl: true, shift: false },
  SPLIT_SWAP: { key: 'ArrowRight', ctrl: true, shift: true },
  SPLIT_CLOSE: { key: 'w', ctrl: true, shift: true },
  AI_ASSISTANT: { key: '.', ctrl: true, shift: false }
}

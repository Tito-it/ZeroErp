// Larghezze drawer per tipologia di form
export const DRAWER_WIDTH = {
  SIMPLE: '480px',    // tabelle di lookup, config
  STANDARD: '640px',  // anagrafiche, catalogo
  COMPLEX: '800px',   // pratiche, contratti
  WIDE: '960px',      // ricerca universale, liste con dettaglio
  WIDE_PLUS: '1100px', // master-detail con sub-tabella expansion (righe + componenti BoM)
  XLARGE: '1360px'    // matrici parametri-per-entita' (utility, slot/override) e
                      // liste a molte colonne dentro un drawer (attivita' di
                      // commessa: 11 colonne + selezione + azioni)
}

// Larghezze Dialog modali "azione" (conferma, form one-shot). Scala usata
// dal building block AppDialog via prop `width` (sm|md|lg|xl). Centralizza i
// px hardcoded sparsi (420/480/500/520/560/700/1200) in 4 taglie coerenti.
export const DIALOG_WIDTH = {
  sm: '480px',   // conferme brevi, form a 1-2 campi (emissione, export, chiusura)
  md: '560px',   // form standard (push, esito, attivazione, approvazioni)
  lg: '720px',   // preview/tabelle (variazione massa)
  xl: 'min(92vw, 1200px)'  // tabelle larghe responsive (componenti BoM compositi)
}

// Durata toast in millisecondi
export const TOAST_DURATION = {
  SUCCESS: 3000,
  WARN: 4000,
  ERROR: 5000,
  SYSTEM_ERROR: 0,  // 0 = persistente, chiusura manuale
  // ⭐ L'errore che porta un GESTO: persistente per la stessa ragione tecnica
  // (0 = chiusura manuale) ma per un motivo diverso — non «e' grave», bensi'
  // «c'e' un pulsante da premere», e un pulsante che sparisce dopo cinque
  // secondi non e' un gesto. Nome suo perche' i due possano divergere senza
  // che nessuno debba indovinare quale dei due stava cambiando.
  AZIONI: 0
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
  COMPACT_ROWS: 10,
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

// Stati terminali della pratica: nessuna transizione in uscita, nulla di
// modificabile (scheda + flussi in sola lettura, niente creazione step).
export const STATI_PRATICA_TERMINALI = [STATO_PRATICA.CHIUSA, STATO_PRATICA.ANNULLATA]

// Natura del documento fiscale (config.nature_doc_fiscale.codice_interno).
// È un asse DIVERSO dal tipo documento (front/back office) e dal registro: le
// tre cose insieme dicono su quale sezionale il documento è numerato.
// `FATTURA` è il default della colonna a DB, quindi una testata senza natura è
// una fattura — non un dato mancante.
export const NATURA_DOC = Object.freeze({
  FATTURA: 'FATTURA',
  NOTA_CREDITO: 'NOTA_CREDITO',
  NOTA_DEBITO: 'NOTA_DEBITO',
})

// Codici interni stati flusso pratica (codice_interno da config.stati_flussi_pratiche)
export const STATO_FLUSSO = {
  DA_ESEGUIRE: 'DA_ESEGUIRE',
  IN_CORSO: 'IN_CORSO',
  COMPLETATO: 'COMPLETATO',
  SOSPESO: 'SOSPESO',
  ANNULLATO: 'ANNULLATO',
  ERRORE: 'ERRORE',
}

// Stato edizione workflow versionata (pratiche.workflow_definizioni.stato).
export const STATO_DEFINIZIONE = {
  BOZZA: 'BOZZA',
  PUBBLICATA: 'PUBBLICATA',
  RITIRATA: 'RITIRATA',
}

// Enum degli step di workflow (CHECK DB `pratiche.template_flussi`). Il FE li usa
// per popolare i Select del form step; il DB resta l'autorita' (CHECK + guard di
// coerenza `trgfn_template_flussi_guard_modalita_esito`).
export const STEP_DIREZIONE = ['ENTRATA', 'USCITA', 'INTERNA']
export const STEP_MODALITA_ESITO = ['MANUALE', 'AUTOMATICO', 'CONTESTUALE', 'DOMINIO']
// modalita_esito che ESIGONO un esito_default (Inv1) e ammettono solo verdetti
// (Inv4). Su DOMINIO l'esito_default e' VIETATO (Inv3) → campo nascosto.
export const STEP_MODALITA_CON_ESITO_DEFAULT = ['AUTOMATICO', 'CONTESTUALE']

// Enum figli step (CHECK DB). `evento` (template_flussi_handler_eventi) e
// `esito_richiesto` (vocabolario fisso `chk_flussi_esito`, condiviso con i
// prerequisiti). NB: distinto dal catalogo config.esiti_flussi_pratiche
// (codice_interno) usato da step.esito_default.
export const STEP_HANDLER_EVENTO = ['IN_CORSO', 'COMPLETATO']
export const ESITO_RICHIESTO = ['POSITIVO', 'NEGATIVO', 'PARZIALE', 'NON_APPLICABILE']
// Enum esito_richiesto delle REGOLE di generazione (CHECK diverso: POSITIVO,
// NEGATIVO, QUALSIASI; NULL = qualsiasi esito). NON confondere con ESITO_RICHIESTO
// (4 valori) usato da prerequisiti/handler-eventi.
export const ESITO_REGOLA = ['POSITIVO', 'NEGATIVO', 'QUALSIASI']

// Stato del ramo nel percorso pratica (workflow v2 D4, campo `ramo` del
// GET /pratiche/<id>/percorso/ — vedi api_percorso.md).
export const RAMO_STEP = {
  COMPLETATO: 'COMPLETATO',
  PERCORRIBILE: 'PERCORRIBILE',
  FUTURO: 'FUTURO',
  RAMO_CHIUSO: 'RAMO_CHIUSO',
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
  // SOGGETTO: stessa icona usata in navigazione per la lista Soggetti
  // (NAV_ICONS.ANAGRAFICHE = pi pi-users). Centralizzata qui per le azioni
  // di riga che aprono il drawer soggetto dalle liste figlie (clienti/fornitori).
  SOGGETTO: 'pi pi-users',
  CONTATTI: 'pi pi-id-card',
  INDIRIZZI: 'pi pi-map-marker',
  CONTI_BANCARI: 'pi pi-wallet',
  // Catalogo
  // UOM: icona composta box+cog (definita in main.css `.app-nav-icon-uom`).
  // Differenzia visivamente le unita' di misura operative dall'articolo
  // base (NAV_ICONS.CATALOGO = pi-box semplice). Semantica "quantita' +
  // conversione operativa".
  UOM: 'app-nav-icon app-nav-icon-uom',
  BOM: 'pi pi-sitemap',
  NOTE: 'pi pi-file-edit',
  CONVERSIONI: 'pi pi-sync',
  // Vendite
  VERSIONI: 'pi pi-history',
  CONTRATTI: 'app-nav-icon app-nav-icon-contratti',
  // Commessa: non ha voce di navigazione (nessuna lista/CRUD propria), quindi
  // vive qui e non in NAV_ICONS. Centralizzata 2026-07-25 alla 2a occorrenza:
  // era hardcoded `pi pi-briefcase` nell'azione «Apri commessa» del drill-down
  // Competenza, e serve ora anche all'«apri documento» del drill-down Backlog.
  COMMESSA: 'pi pi-briefcase',
  LISTINI: 'app-nav-icon app-nav-icon-listini',
  RIGHE: 'pi pi-list',
  // Trasversali
  EDIT: 'pi pi-pencil',
  ADD: 'pi pi-plus',
  CONFIRM: 'pi pi-check',
  CANCEL: 'pi pi-times',
  // BACK: usato dal pulsante "Annulla" di FormFooter — la chiusura di un
  // drawer di form torna alla lista, semantica "indietro" piu' chiara di un
  // semplice "X". Distinto da CANCEL (close-without-saving generico) e da
  // NAV_ICONS.BACK (header sidebar "Torna alla Home").
  BACK: 'pi pi-arrow-left',
  PLAY: 'pi pi-play',
  PUBLISH: 'pi pi-check-circle',
  // Invio/push verso valle (push a commessa). Centralizzata: usata
  // dall'azione "Invia a commessa" del drawer ordini; stessa semantica del
  // pulsante push di PreventiviIntegrazione (oggi ancora `pi pi-send` inline).
  SEND: 'pi pi-send',
  CLONE: 'pi pi-copy',
  CLOSE: 'pi pi-lock',
  CLOSE_DATE: 'pi pi-calendar-times',
  PERMISSIONS: 'pi pi-shield',
  BILLING_ACCOUNT: 'pi pi-credit-card',
  UTILITY: 'pi pi-bolt',
  LIST: 'pi pi-list',
  BUILDING: 'pi pi-building',
  RELOAD: 'pi pi-refresh',
  DOWNLOAD: 'pi pi-download',
  DELETE: 'pi pi-trash',
  // Storno di un fatto GIA' REGISTRATO (annulla l'accredito di una riga di
  // reso, e i suoi futuri gemelli). ⚠️ NON e' DELETE: in variante desktop le
  // azioni di riga sono bottoni icon-only, e col cestino l'annullo era
  // indistinguibile da «elimina la riga» — misurato in-app il 2026-08-19, dove
  // per di piu' l'unica azione a video ERA questa e veniva letta come il
  // cestino di eliminazione. Elimina toglie una riga; questo disfa un effetto.
  UNDO: 'pi pi-undo',
  KEBAB: 'pi pi-ellipsis-v',
  // Documenti PDF (lista/anteprima/scarica). Centralizzata 2026-05-30:
  // usata da GeneraPdfButton + EntityPdfButton (BB documenti) e dai
  // buildRowActions delle liste vendite (preventivi/contratti/offerte).
  PDF: 'pi pi-file-pdf',
  // Personalizzazione lista (DEF-8): apre la modale "Personalizza colonne"
  // di `<ListaConfigurabile>`. Centralizzata 2026-05-11 dopo audit DEF-8
  // soggetti (era hardcoded in ClientiSearchTable + SoggettiSearchTable).
  PERSONALIZZA: 'pi pi-cog',
  // Toggle collassa/espandi (accordion, expansion row, tree).
  // Standard PrimeVue/Material: chevron-down sta nello stato collassato
  // (invita ad aprire), chevron-up nello stato espanso (invita a chiudere).
  // Usare sempre dinamicamente: `icon: isExpanded ? COLLAPSE : EXPAND`.
  EXPAND: 'pi pi-chevron-down',
  COLLAPSE: 'pi pi-chevron-up',
  // Workflow approvazione prezzi (Sprint E listini v5).
  APPROVE: 'pi pi-check',
  REJECT: 'pi pi-times',
  // Assegnazione / presa in carico (pratiche): assegna flusso a operatore/reparto
  // (FlussoDrawer) e "prendi in carico" dalla coda lavoro (PraticheCodaLavoro).
  // Centralizzata: era hardcoded inline come `pi pi-user-plus` nei due punti.
  ASSIGN: 'pi pi-user-plus',
  // Ispezione read-only (apre un dettaglio in sola lettura). Distinta da EDIT
  // (modifica) — usata dalle azioni "Ispeziona" quando l'entita' non e' editabile.
  INSPECT: 'pi pi-eye',
  // Archivio documenti generati (dialog PdfDocumentiSorgenteDialog): lista
  // stampe + allegati di una sorgente. Regola del 2: era hardcoded
  // `pi pi-folder-open` in LottoDrawer e FatturaDrawer.
  ARCHIVE: 'pi pi-folder-open',
}

// Scope readonly — area (schema DB) passata come primo arg a useReadonlyMode.
// Unico punto dove compaiono i nomi degli schemi DB lato FE. Cambiare qui =
// cambiare ovunque senza rompere il refresh cross-tab o il matching permessi.
export const READONLY_DOMAINS = {
  AMM_SOFTWARE: 'amm_software',
  ANAGRAFICHE: 'anagrafiche',
  CATALOGO: 'catalogo',
  CONFIG: 'config',
  DOCUMENTI: 'documenti',
  // Area dedicata del dominio Strumenti (code di lavoro; l'area `core` resta
  // all'infra tracciamento, non si apre agli operatori per le code).
  STRUMENTI: 'strumenti',
  PRATICHE: 'pratiche',
  VENDITE: 'vendite',
}

// Scope readonly — model specifico (secondo arg opzionale a useReadonlyMode).
// Richiede che la view BE dichiari `model_permission = (app_label, model_name)`
// perche' il permesso livello oggetto abbia effetto.
export const READONLY_MODELS = {
  ARTICOLO: 'articolo',
  CLIENTE: 'cliente',
  CONTO_BANCARIO: 'conto_bancario',
  CONTRATTO: 'contratto',
  DDT: 'ddt',
  FATTURA: 'fattura',
  RESO: 'reso',
  FORNITORE: 'fornitore',
  OFFERTA_COMMERCIALE: 'offerta_commerciale',
  ORDINE: 'ordine',
  PROMO_ARTICOLO: 'promo_articolo',
  SOGGETTO: 'soggetto',
  UOM_TIPI: 'uom_tipi',
  UNITA_MISURA: 'unita_misura',
}

// Entita' usate come chiave cross-tab per emitDataChanged / useTabFreshness.
// Il producer (store.create/update/delete) emette la chiave; i consumer
// (SearchTable delle altre tab) ricaricano se la stessa chiave arriva.
// I nomi DEVONO matchare bit-by-bit tra emit e ascolto: l'enum evita typo
// silenziosi.
//
// Pattern consumer:
//  - useTabFreshness(store, TAB_ENTITIES.X)          # standard lista paginata
//  - useTabEvents().onDataChanged('X', handler)      # hook custom (es. RepartiProfiloView)
//
// Nota: `PROMO_ARTICOLI` (plurale, chiave tab/DB) e `promo_articolo`
// (singolare, READONLY_MODELS per model_permission BE) sono volutamente
// distinti: il primo e' la tabella/feature, il secondo e' il nome del
// model Django utilizzato dalla risoluzione permessi oggetto.
export const TAB_ENTITIES = {
  ARTICOLO: 'articolo',
  CATEGORIE_CLIENTI: 'categorie_clienti',
  CATEGORIE_CLIENTI_LISTINI: 'categorie_clienti_listini',
  CLIENTE: 'cliente',
  CODICE_POSTALE: 'codice_postale',
  COMUNE: 'comune',
  CONTRATTO: 'contratto',
  CONVERSIONI_UOM: 'conversioni_uom',
  DDT: 'ddt',
  RESO: 'reso',
  EMAIL_ACCOUNTS: 'email-accounts',
  EMAIL_TEMPLATES: 'email-templates',
  EMITTENTE_FISCALE: 'emittente-fiscale',
  FORNITORE: 'fornitore',
  INDIRIZZO: 'indirizzo',
  LISTINO: 'listino',
  OFFERTA_COMMERCIALE: 'offerta_commerciale',
  OPERATORE: 'operatore',
  ORDINE: 'ordine',
  PRATICA: 'pratica',
  PREVENTIVO: 'preventivo',
  PROFILO_REPARTO: 'profilo-reparto',
  PROMO_ARTICOLI: 'promo_articoli',
  PROVINCIA: 'provincia',
  REGIONE: 'regione',
  SOGGETTO: 'soggetto',
  STATO: 'stato',
  TEMPLATE_ASSET_DOCUMENTI: 'template_asset_documenti',
  TEMPLATE_DOCUMENTI: 'template_documenti',
  TEMPLATE_VERSIONI: 'template_versioni',
  TIPI_RUOLO_TIPI_INDIRIZZO: 'tipi_ruolo_tipi_indirizzo',
  TOPONOMASTICA: 'toponomastica',
  UI_COLONNA: 'ui_colonna',
  UI_DEFINIZIONE: 'ui_definizione',
  UI_PERMESSO: 'ui_permesso',
  UI_PRESET: 'ui_preset',
  UOM_TIPI: 'uom_tipi',
  UNITA_MISURA: 'unita_misura',
  UTILITIES_TIPI_RUOLO: 'utilities_tipi_ruolo',
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

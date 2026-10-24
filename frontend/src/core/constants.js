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

// Chrome delle dialog modali — LA sede unica (decisione di Tid, 2026-09-18).
// La leggono `AppDialog` (default delle prop) e il tag `<ConfirmDialog>` di
// `App.vue`: un cambio di layout e' una riga qui, non un giro sui 48 dialog.
//   · closable false  — niente X in alto: il footer di un dialog e' SEMPRE
//                       visibile (max-height 90%, footer in coda), quindi ogni
//                       dialog ha gia' Annulla o Chiudi e la X era un doppione
//                       con una semantica sua (chiudeva senza `cancel`). Nel
//                       DRAWER la X resta, per la ragione opposta: il footer di
//                       un form lungo sta sotto il fold.
//   · closeOnEscape   — ESC = Annulla, la direzione sicura resta aperta da
//                       tastiera (AppDialog la spegne mentre `loading`).
//                       ⭐ E chiude SOLO il dialog in cima: gestita sulla
//                       radice del dialog, non col listener `document` di
//                       PrimeVue che convive con quello del Drawer sotto
//                       (`core/utils/escapeSoloInCima`).
//   · dismissableMask — il clic fuori non chiude: terza uscita accidentale,
//                       stessa ragione della X.
// ⚠️ `closable` NON e' un'opzione di `confirm.require` (PrimeVue 4 non la
//    inoltra al Dialog): per la ConfirmDialog va sul tag, in App.vue.
export const DIALOG_CHROME = Object.freeze({
  modal: true,
  closable: false,
  closeOnEscape: true,
  dismissableMask: false,
})

// Durata toast in millisecondi
export const TOAST_DURATION = {
  SUCCESS: 3000,
  // ⭐ L'informativo dura come il successo, e non come l'avviso: dice che una
  // cosa È SUCCESSA («il lavoro è in coda», «lo stava già facendo un altro
  // giro»), non che c'è qualcosa da guardare. Voce propria perché i due
  // possano divergere senza che nessuno debba scegliere quale «riusare».
  INFO: 3000,
  WARN: 4000,
  ERROR: 5000,
  // ⭐ L'errore che porta anche la SOLUZIONE (2026-09-09): il `hint` che il team
  // DB scrive a catalogo — «Numerare prima i documenti che questo rettifica,
  // poi ripetere» — e che dal 2026-09-09 il toast rende sotto il messaggio.
  // ⚠️ Dura di piu' perche' il TESTO E' IL DOPPIO, non perche' e' piu' grave:
  // la durata di un toast si calibra su quanto c'e' da leggere, e qui le frasi
  // sono due — cosa e' successo e cosa fare adesso.
  // ⛔ E NON e' persistente come `AZIONI`: la soluzione e' a catalogo per ogni
  // codice, quindi `life: 0` qui farebbe di OGNI errore di dominio un toast da
  // chiudere a mano. Un gesto ha un pulsante da premere e puo' aspettare; una
  // frase si legge e se ne va.
  ERROR_CON_SOLUZIONE: 9000,
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

// ⛔ Le misure «righe per pagina» NON stanno qui: fino al 2026-09-30 c'era
//    `PAGINATION`, una copia del catalogo DB `ui.misure_pagina`. Si leggono dal
//    BB `core/misurePagina.js` (`USO_MISURA`, `misuraDefault`, `misureOpzioni`).

// Ricerca libera delle liste: la soglia del termine, sotto la quale NON si
// manda (la lista resta quella di prima mentre si digita).
// ⭐ Specchio di `RICERCA_MIN_CARATTERI` del backend (`core/db/_helpers.py`), la
//    soglia di default del BB `add_ricerca_full_condition`. Una sede sola nel
//    frontend (2026-09-24, regola del 2 — ok Tid): prima lo stesso `3` era
//    scritto in sei store e due volte in `useListaEmptyStateFetch`.
// ⚠️ E' il RIPIEGO: la soglia di una lista configurabile e' un fatto della
//    lista (`ricerca_min_caratteri` nella sua configurazione, brief-db-be-fe-
//    ricerca-soglia-per-lista), che lo store tiene in `ricercaMinCaratteri`.
//    Questo numero vale solo finche' la configurazione non e' arrivata
//    (`null`), e per le ricerche che non sono una lista a catalogo.
//    Chi la legge passa sempre da `paramsRicerca` / `termineCorto`
//    (`core/utils/listParams.js`), mai da un confronto scritto sul posto.
export const RICERCA = {
  MIN_CARATTERI: 3,
}

// Formato data (PrimeVue DatePicker dateFormat)
// dd/mm/yy = GG/MM/YYYY in PrimeVue ('yy' = anno a 4 cifre)
// Centralizzato: cambiare qui per aggiornare tutte le date del sistema.
export const DATE_FORMAT = 'dd/mm/yy'

// Formato MESE (DatePicker con `view="month"`): MM/YYYY. ⭐ Regola del 2
// (2026-10-04): due selettori del mese, uno con 'mm/yy' scritto sul posto
// (lista contratti) e uno con DATE_FORMAT (accettazione preventivo), che
// mostrava un giorno su un campo che non ne ha.
export const MONTH_FORMAT = 'mm/yy'

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
  IBAN_MAX: 34,  // ISO 13616: max 34 caratteri alfanumerici
  // Sigla dell'emittente fiscale: specchio del CHECK DB
  // `chk_emittenti_fiscali_codice_forma` (`^[A-Z0-9]{2,10}$`, 2026-08-31).
  // ⚠️ I due numeri stanno QUI e non nel drawer perche' servono in tre punti —
  // il `maxlength`, la regex di `canSave` e la frase dell'hint — e tre copie di
  // un vincolo si allineano a mano finche' qualcuno se ne dimentica.
  // ⛔ Non e' una regola di business duplicata: e' la validazione UX che evita
  // un giro fino al database. Il rifiuto autorevole resta del DB.
  EMITTENTE_CODICE_MIN: 2,
  EMITTENTE_CODICE_MAX: 10,
  // Registri di numerazione: le lunghezze REALI delle colonne, lette da
  // `information_schema` il 2026-09-01 e non dedotte dall'auto-gen (che
  // stampa «character varying» senza la lunghezza).
  // ⛔ SERVONO DAVVERO, e la prova e' stata un errore vero: `prefisso` e'
  //    `varchar(4)`, e senza `maxlength` un prefisso di cinque caratteri non
  //    diventa un 400 parlante — diventa un `DataError`, che NON e' un
  //    `IntegrityError` e quindi non passa da `map_integrity_error`: arriva
  //    all'operatore come errore generico di database.
  // `varchar(80)` dal 2026-10-20 (era 16): il codice di un registro provvisionato
  // e' il codice della famiglia piu' l'id dell'emittente (`ORDINE_VENDITA-31848`),
  // L2c-1 di brief-db-grammatica-unica-documenti.
  REGISTRO_CODICE_MAX: 80,
  REGISTRO_DESCRIZIONE_MAX: 120,
  // Famiglie di documento: le `varchar` della tabella, verificate sul
  // database il 2026-09-02. ⛔ Stanno qui e non nel template per la ragione di
  // sempre — un `maxlength` scritto a mano non e' un limite dichiarato, e' un
  // numero che nessuno ricontrolla il giorno che la colonna cambia.
  // ⭐ Il `codice_interno` non ha piu' un limite qui: dal 2026-10-20 si SCEGLIE
  //    fra le sorgenti (G-5 di brief-db-grammatica-unica-documenti), non si scrive.
  // Il `codice` dell'operatore (dal 2026-09-24): `varchar(32)`, come i codici
  // di `config.*` (changeSet `20260924-03`).
  FAMIGLIA_CODICE_OPERATORE_MAX: 32,
  FAMIGLIA_DESCRIZIONE_MAX: 120,
  FAMIGLIA_PREFISSO_MAX: 8,
  REGISTRO_PREFISSO_MAX: 4,
  REGISTRO_SUFFISSO_MAX: 4,
  REGISTRO_SERIE_MAX: 8
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
}
// ⛔ Niente piu' `DISABILITATO` (2026-10-02, brief-db-be-fe-area-accessi
//    R-DB-1): una veste spenta TIENE il suo tipo e ha `attivo = false`, e la
//    tabella rifiuta il valore, che resta nell'enum del DB solo come voce
//    storica. «Disabilitato» si legge dallo stato della veste, non dal ruolo.

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
    // Il secondo passo del login (secondo fattore): sotto /token/, quindi
    // l'interceptor non prova a rinnovare la sessione su un suo 401.
    secondoFattorePath: '/admin/token/secondo-fattore/',
    // La chiave d'ingresso della porta, cioè il campo del corpo del login
    // (L-4, D-9): il nome utente per l'operatore, l'email per portale e shop.
    campoIngresso: 'username',
    i18n: 'auth.canale.admin'
  },
  PORTALE: {
    key: 'PORTALE',
    tokenPath: '/portale/token/',
    refreshPath: '/portale/token/refresh/',
    secondoFattorePath: '/portale/token/secondo-fattore/',
    campoIngresso: 'email',
    i18n: 'auth.canale.portale'
  },
  SHOP: {
    key: 'SHOP',
    tokenPath: '/shop/token/',
    refreshPath: '/shop/token/refresh/',
    secondoFattorePath: '/shop/token/secondo-fattore/',
    campoIngresso: 'email',
    i18n: 'auth.canale.shop'
  }
}

// Gli obblighi della credenziale che il backend fa rispettare (cancello degli
// obblighi): arrivano da `/core/me/` in `obblighi_pendenti`, nell'ordine in cui
// si chiudono. Il guard del router porta alla pagina che chiude il primo.
export const OBBLIGO_CREDENZIALE = {
  CAMBIO_PASSWORD: 'CAMBIO_PASSWORD',
  SECONDO_FATTORE: 'SECONDO_FATTORE'
}

// Lo stato del device del secondo fattore, come lo dice il backend
// (`STATI_DEVICE` di `apps/core/db/secondo_fattore_repository.py`).
export const STATO_SECONDO_FATTORE = {
  ASSENTE: 'ASSENTE',
  DA_CONFERMARE: 'DA_CONFERMARE',
  ATTIVO: 'ATTIVO'
}

// Lo stato di una VESTE d'accesso: i quattro di `script.fn_stato_veste` (A-7,
// calcolati SOLO a DB) piu' NESSUNO, la veste che non esiste — lo dichiarano
// la scheda accessi del soggetto e `vw_accessi_altri.stato_accesso`. ⭐ Il
// vocabolario sta qui, non nelle chiavi della mappa dei colori (`STATO_VESTE_MAP`):
// un filtro costruito dai colori perderebbe in silenzio uno stato senza colore.
// Regola del 2 (ok Tid 2026-10-02): `PortaleAccessoPanel`, `WebAccessiBadge`,
// `AccessiAltriTab`.
export const STATO_VESTE = Object.freeze({
  ATTIVO: 'ATTIVO',
  PENDING: 'PENDING',
  NON_SPEDITO: 'NON_SPEDITO',
  DISATTIVO: 'DISATTIVO',
  NESSUNO: 'NESSUNO',
})

// Da dove viene l'obbligo del secondo fattore (`motivo` dello stato).
export const MOTIVO_OBBLIGO_SECONDO_FATTORE = {
  CREDENZIALE: 'CREDENZIALE',
  PROFILO: 'PROFILO'
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
// vesti senza namespace FE (API_CLIENT, assente): il caller
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
  // INDIRIZZI ripete `NAV_ICONS.INDIRIZZO` (la voce di menu Indirizzi), per la
  // stessa ragione di SOGGETTO: il drawer che si apre e' «quella li'».
  INDIRIZZI: 'pi pi-map-marker',
  CONTI_BANCARI: 'pi pi-wallet',
  // Titolo IVA del soggetto (I7/D10): un documento REGISTRATO che sostituisce
  // l'aliquota ordinaria. L'icona dice «documentato», non «percentuale»: il
  // punto del modello e' che l'agevolazione passa da una prova, non da un flag.
  TITOLI_IVA: 'pi pi-verified',
  // Catalogo
  // UOM: le unita' di misura (anche quelle operative di un articolo). Ripete
  // `NAV_ICONS.UNITA_MISURA`, la voce di menu (Tid 2026-09-27): prima era
  // l'icona composta box+cog, e lo stesso concetto portava due segni.
  UOM: 'pi pi-arrows-h',
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
  // NUMERAZIONE: i registri di numerazione (sezionali) di un emittente. Come
  // COMMESSA non hanno una voce di navigazione — si aprono dal kebab
  // dell'emittente — quindi l'icona vive qui e non in NAV_ICONS.
  // ⭐ Il cancelletto e' il segno del NUMERO, ed e' cio' che quei registri
  // decidono. ⛔ Non la matita: quella dice «modifica questa riga», mentre
  // l'azione apre un ELENCO (`feedback_row_actions_menu`). Centralizzata
  // 2026-09-02 alla 3a occorrenza: l'azione di riga e i due drawer che apre —
  // e devono portare lo stesso segno, o chi ha cliccato non lo ritrova.
  NUMERAZIONE: 'pi pi-hashtag',
  // FAMIGLIA_DOCUMENTO: la regola che il registro applica. Ha una voce di
  // navigazione (Amministrazione -> Famiglie di documento), quindi ripete la
  // sua icona — `NAV_ICONS.FAMIGLIE_DOCUMENTO = pi pi-file` — per la stessa ragione di
  // SOGGETTO e FATTURE: il drawer che si apre dev'essere riconoscibile come
  // «quella li'», non come una funzione nuova.
  // ⚠️ Il valore si RIPETE invece di importarlo: `NAV_ICONS` vive in
  // `core/navigation.js` e importarlo qui legherebbe le costanti alla
  // navigazione. E' la stessa scelta gia' fatta per SOGGETTO e FATTURE.
  FAMIGLIA_DOCUMENTO: 'pi pi-file',
  RIGHE: 'pi pi-list',
  // FATTURE: la stessa icona della voce di navigazione (NAV_ICONS.FATTURE) —
  // le azioni di riga che PORTANO alla lista fatture devono essere
  // riconoscibili come «quella lì», non come una funzione nuova.
  // Centralizzata 2026-08-24 alla 2a occorrenza: il collegamento nasce
  // insieme sulle liste soggetti e clienti.
  FATTURE: 'app-nav-icon app-nav-icon-fatture',
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
  // Inviare: il verbo `emetti` dei documenti (D-1 di Tid, 2026-09-27) e
  // l'invio di un messaggio (assistente AI).
  // ⛔ Non il push a commessa: quello e' `INVIA_A_COMMESSA` (Tid 2026-09-27),
  //    perche' nel preventivo `emetti` e il push stanno nello stesso drawer.
  SEND: 'pi pi-send',
  // Mandare righe a valle verso la commessa: il push (preventivo, ordine,
  // DDT), lo smistamento del preventivo e le attivita' di pratica che li
  // aprono. Icona composta: valigetta della commessa + freccia verso valle
  // (main.css). ⛔ Non `COMMESSA` nuda, che e' «apri la commessa»: il posto,
  // non il gesto.
  INVIA_A_COMMESSA: 'app-nav-icon app-nav-icon-invia-commessa',
  CLONE: 'pi pi-copy',
  CLOSE: 'pi pi-lock',
  CLOSE_DATE: 'pi pi-calendar-times',
  // La promessa di consegna di una riga (data di consegna confermata), che si
  // cambia anche dopo la conferma dell'ordine.
  PROMESSA_CONSEGNA: 'pi pi-calendar-clock',
  PERMISSIONS: 'pi pi-shield',
  // La sicurezza dell'accesso: il secondo fattore (pagina «Sicurezza», sezione
  // del drawer operatore).
  SICUREZZA_ACCESSO: 'pi pi-key',
  // Il cambio della PROPRIA password (scheda utente della topbar).
  CAMBIO_PASSWORD: 'pi pi-user-edit',
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
  // La REGISTRAZIONE di un incasso — il gesto irreversibile che scrive un
  // movimento. Era un letterale nel solo «Registra» del drawer della distinta;
  // dal 2026-09-19 lo legge anche «Abbina e registra» (la tardiva per riga,
  // D20-b), e due lettori vogliono un nome (frontend-standards §«dove vive il
  // nome di un'icona»).
  REGISTRA: 'pi pi-lock',
  // RISERVARE merce a qualcuno: il blocco manuale di magazzino (Lotto 3 R-5,
  // «Blocca merce» sulla disponibilita'), che FERMA gli scarichi degli altri
  // finche' non lo si libera — la pausa. ⛔ Non il lucchetto, che e' gia' CLOSE
  // e REGISTRA (un blocco e' una promessa che si libera, non un atto chiuso),
  // ne' il segnalibro, che e' IMPOSTA_CONTESTO.
  BLOCCA_MERCE: 'pi pi-pause-circle',
  // ⛔ ANNULLA — si DISFA un atto che resta e viene dichiarato nullo: annulla
  //    il lotto, annulla la riga manuale, annulla la pratica.
  // 🔴 NON È UN ERRORE (`STATUS_ICONS.ERRORE`, il triangolo), ed è la
  //    confusione che la coppia esiste per togliere: sul cruscotto Competenza il
  //    conteggio degli ERRORI portava proprio questo segno — cioè il gesto per
  //    cancellarli — e il triangolo stava sul lavoro ancora da fare (rilievo di
  //    Tid, 2026-09-09).
  // ⚠️ E non è nemmeno `CANCEL` (`pi-times`: chiudere senza salvare) né
  //    `DELETE` (`pi-trash`: togliere la riga). Tre gesti vicini, tre segni.
  ANNULLA: 'pi pi-times-circle',
  //
  // ⚠️ LOTTO — il giro di fatturazione, quando serve NOMINARLO in una riga
  //    d'altro dominio: sul cruscotto Competenza dice chi sta trattenendo un
  //    documento. ⛔ Ripete il valore di `NAV_ICONS.LOTTI` invece di importarlo,
  //    come già fanno `SOGGETTO`, `FATTURE` e `FAMIGLIA_DOCUMENTO`: legare le
  //    costanti alla navigazione per un glifo non vale la dipendenza.
  // 🔴 Nasce da un difetto di segni: il documento trattenuto portava lo STESSO
  //    lucchetto della testata non emittibile — due blocchi con due vie
  //    d'uscita diverse e un solo simbolo, e su una riga che li ha entrambi
  //    comparivano due icone identiche affiancate.
  LOTTO: 'pi pi-server',
  // Le anagrafiche di MAGAZZINO (2026-09-21, piano anagrafiche-fuori-dal-
  // pannello-config): le ubicazioni sono la MAPPA del deposito (scaffali,
  // corsie), il lotto di magazzino e' la PARTITA di merce di un articolo —
  // ⚠️ non il `LOTTO` qui sopra, che e' il giro di fatturazione: due cose,
  // due glifi, o una riga con entrambi li confonderebbe.
  // ⭐ UBICAZIONI e' la mappa, e il glifo lo dice (`pi-map`, 2026-09-27): prima
  //    portava `pi-th-large`, che e' la voce «Personalizzazioni liste».
  //    La pagina 404 (`STATUS_ICONS.NON_TROVATO`) ha lasciato la mappa per
  //    questo.
  UBICAZIONI: 'pi pi-map',
  // ⭐ La partita di merce e' cio' che si legge dal codice a barre dell'etichetta
  //    (2026-09-27). ⛔ Non `pi-tags`: quelle sono le categorie clienti
  //    (`NAV_ICONS.CATEGORIE_CLIENTI`), due concetti che non si toccano.
  LOTTO_MAGAZZINO: 'pi pi-barcode',
  // Spegnere/riaccendere un'anagrafica (`attivo`): due gesti, due glifi, e
  // il secondo non e' la spunta di `CONFIRM` — riattivare non e' confermare.
  // ⭐ E' un CONCETTO (lo stesso senso in magazzini, ubicazioni, lotti e
  // famiglie di documento): chi spegne/riaccende una riga passa da qui, non
  // da `CANCEL`/`RELOAD`, che dicono «annulla» e «ricarica».
  // ⛔ RIATTIVA non e' `pi-replay` (lo era fino al 2026-09-27): quello e'
  //    `CORREZIONE`, e due gesti non portano lo stesso segno. L'interruttore
  //    dice «riaccendi», che e' esattamente il gesto.
  DISATTIVA: 'pi pi-ban',
  RIATTIVA: 'pi pi-power-off',
  KEBAB: 'pi pi-ellipsis-v',
  // Documenti PDF (lista/anteprima/scarica). Centralizzata 2026-05-30:
  // usata da EntityPdfButton (BB documenti) e dai
  // buildRowActions delle liste vendite (preventivi/contratti/offerte).
  PDF: 'pi pi-file-pdf',
  // Personalizzazione lista (DEF-8): apre la modale "Personalizza colonne"
  // di `<ListaConfigurabile>`. Centralizzata 2026-05-11 dopo audit DEF-8
  // soggetti (era hardcoded in ClientiSearchTable + SoggettiSearchTable).
  PERSONALIZZA: 'pi pi-cog',
  // I FILTRI di una lista: apre il drawer dal basso in modalita' compatta
  // (`FiltriLista`, D1/D4 di Tid 2026-09-22). ⛔ Non `pi-search`: quella e' la
  // RICERCA, che nella stessa barra sta accanto e resta sempre a video —
  // due gesti diversi non possono portare lo stesso segno.
  FILTRI: 'pi pi-filter',
  // Togliere i filtri, non «annullare»: `CANCEL` (pi-times) dice «chiudi» e
  // sta gia' sul footer di ogni form. Il glifo barrato dice che cosa smette
  // di valere.
  FILTRI_PULISCI: 'pi pi-filter-slash',
  // Toggle collassa/espandi (accordion, expansion row, tree).
  // Standard PrimeVue/Material: chevron-down sta nello stato collassato
  // (invita ad aprire), chevron-up nello stato espanso (invita a chiudere).
  // Usare sempre dinamicamente: `icon: isExpanded ? COLLAPSE : EXPAND`.
  EXPAND: 'pi pi-chevron-down',
  COLLAPSE: 'pi pi-chevron-up',
  // Toggle delle EXPANSION ROW di una DataTable: la stessa coppia del toggler
  // di riga PrimeVue (chevron-right = chiusa, chevron-down = aperta), cosi'
  // «espandi tutte» nella barra della lista porta lo stesso segno della riga.
  // Usare dinamicamente: `icon: isExpanded ? ROW_COLLAPSE : ROW_EXPAND`.
  ROW_EXPAND: 'pi pi-chevron-right',
  ROW_COLLAPSE: 'pi pi-chevron-down',
  // Il segno «questa voce di menu contiene altre voci» (Tid 2026-10-24): il
  // gruppo a sidebar chiusa (SidebarItem, prop `gruppo`), il gruppo a sidebar
  // aperta (SidebarDomain: chiuso / aperto) e le voci con sottomenu di un
  // TieredMenu (slot `#submenuicon`, kebab utente della topbar). Sempre con
  // la classe `app-sottomenu-icon` (main.css): prende il colore dell'icona
  // della sua voce. Caret PIENO: piccolo com'e', un chevron filiforme non si
  // vedeva. ⛔ Non `ROW_EXPAND`: e' il toggle delle righe di tabella, fino a
  // quel giorno prestato alla sidebar.
  SOTTOMENU: 'pi pi-caret-right',
  SOTTOMENU_APERTO: 'pi pi-caret-down',
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
  // Correzione di un documento registrato: si apre un documento NUOVO che
  // rovescia il primo. ⛔ Non `CONVERSIONI` (`pi-sync`), che nel progetto
  // significa un'altra cosa — la conversione fra unita' di misura: prendere in
  // prestito il nome di un'altra idea e' il modo in cui due gesti diversi
  // finiscono per sembrare lo stesso.
  CORREZIONE: 'pi pi-replay',
  // Il GIORNALE degli eventi (osservabilita', 2026-09-19): l'azione «Giornale
  // di questa transazione» dal registro degli errori tecnici e la «Storia» di
  // un'entita' dal giornale trasversale. Stessa icona della voce di
  // navigazione `NAV_ICONS.GIORNALE`, ripetuta per la stessa ragione di
  // FATTURE e FAMIGLIA_DOCUMENTO: chi clicca deve ritrovare «quella li'».
  GIORNALE: 'pi pi-book',
  // Copia negli appunti (un identificativo tecnico: `tx_id`, `correlation_id`).
  // ⛔ Non CLONE (`pi-copy`): quello nel progetto duplica un RECORD.
  COPIA: 'pi pi-clipboard',
  // Il cambio di stato di un oggetto (evento di giornale: pratica, flusso).
  // ⛔ Non `pi-sync`, che e' `CONVERSIONI` (unita' di misura), ne' `AVANZA`,
  // che e' il passo della pipeline del lotto: qui si dice solo «e' passato
  // ad altro stato».
  CAMBIO_STATO: 'pi pi-arrow-right',
  // La tab tenuta ferma a sinistra nella vista divisa. ⛔ Non `pi-thumbtack`,
  // che e' `PREDEFINITO` (il valore che vale quando non si dice altro).
  TAB_FISSATA: 'pi pi-circle-fill',
  // Maniglia di trascinamento per riordinare una voce. ⛔ Non `pi-bars`, che
  // e' `MENU`; ne' `SPOSTA_SU`/`SPOSTA_GIU`, che sono i pulsanti a scatto.
  TRASCINA: 'pi pi-arrows-v',
  // L'operatore super-amministratore (scheda utente; in topbar, dal
  // 2026-10-18, solo su mobile accanto alle iniziali). ⛔ Non `pi-shield`,
  // che e' `PERMISSIONS`: il chip dice CHI sei, non che cosa puoi fare.
  SUPER_ADMIN: 'pi pi-crown',
  //
  // ═══ Censimento icone per significato (2026-09-27, approvato da Tid) ══════
  // docs/it/dev/work-done/censimento-icone-per-significato.md. Il nome
  // dice il SIGNIFICATO, non il disegno: due gesti diversi non portano lo
  // stesso segno, e lo stesso significato ne porta uno solo.
  //
  // ─── Cercare, andare, aprire ───────────────────────────────────────────────
  // Cercare: apre un resolver, la ricerca globale, l'invito «esegui una
  // ricerca». E' la RICERCA che `FILTRI` nomina come vicina di barra. Assorbe
  // l'ex `NAV_ICONS.SEARCH` (stesso valore, nome di disegno).
  RICERCA: 'pi pi-search',
  // Portare a un'altra vista. ⚠️ Solo RIPIEGO: dove la destinazione ha
  // un'icona sua vale quella (regola di `bersaglioGesto`).
  VAI_A: 'pi pi-external-link',
  // Transizione BOZZA→APERTA (pratica). Coppia simmetrica di `CLOSE` (il
  // lucchetto chiuso). ⛔ Non e' SBLOCCA, che toglie un blocco.
  APRI: 'pi pi-lock-open',
  // Togliere un blocco. ⛔ Non il lucchetto aperto: su un bottone si legge
  // come STATO «aperto» (e il lucchetto aperto e' `APRI`).
  SBLOCCA: 'pi pi-key',
  // Bloccare l'ACCESSO di una persona: la credenziale non entra piu' da
  // nessuna porta, per decisione dell'amministratore (brief-db-be-fe-area-
  // accessi). Coppia di `SBLOCCA`. ⛔ Non il lucchetto (`CLOSE`, `REGISTRA`,
  // `VIETATO`) ne' `DISATTIVA` (`pi-ban`, spegne una veste): qui si toglie
  // l'ingresso alla persona, su tutte le sue vesti.
  BLOCCA_ACCESSO: 'pi pi-user-minus',
  //
  // ─── Pipeline e lavori ─────────────────────────────────────────────────────
  // Avanzare di uno step la pipeline del lotto. Coppia di `RIPORTA_A_BOZZA`.
  AVANZA: 'pi pi-forward',
  // Riportare un lotto in bozza (ritorno in lavorazione). ⛔ Non `UNDO`, che
  // storna un fatto registrato: qui la pipeline torna indietro di stato.
  RIPORTA_A_BOZZA: 'pi pi-backward',
  // Rilanciare lo stesso passo fallito: riprova, rilancia, rimetti in coda.
  // ⛔ Non `PLAY` (avvia la prima volta) ne' `CORREZIONE` (`pi-replay`).
  RIPROVA: 'pi pi-play-circle',
  // Rifare da capo la bozza (scarta il calcolo e ne nasce uno nuovo).
  // ⛔ Non `RELOAD` (rilegge i dati) ne' `RIPROVA` (rilancia lo stesso passo).
  RIGENERA: 'pi pi-file-plus',
  // «Avvia e completa» un passo automatico in un colpo solo. ⛔ Non `PLAY`,
  // che avvia soltanto.
  ESEGUI: 'pi pi-fast-forward',
  // Mettere da parte in attesa di risoluzione (pratica, riga contabile,
  // evento di giornale). Coppia naturale di `PLAY`. Ripete
  // `NAV_ICONS.CODA_SOSPESE`: e' la porta della stessa coda.
  SOSPENDI: 'pi pi-pause',
  // Stampare: la coda di stampa e il gesto che vi finisce dentro (ristampa).
  STAMPA: 'pi pi-print',
  // Togliere una riga dalla coda viva mettendola in archivio. Coppia di
  // `ARCHIVE` (apre l'archivio). ⛔ Non `pi-inbox`: quella e' la coda.
  ARCHIVIA: 'pi pi-folder-plus',
  //
  // ─── Documenti e fatturazione ──────────────────────────────────────────────
  // Il verbo «Fattura» (gruppo, mese, selezionati). ⛔ Non `FATTURE`: quella
  // e' la lista, un posto; questo e' un gesto.
  FATTURA_GENERA: 'pi pi-file-export',
  // Generare un documento a valle (es. la riconsegna di un reso). ⭐ Stesso
  // segno di `FATTURA_GENERA` di proposito: e' lo stesso gesto, un documento
  // che nasce da un altro.
  GENERA_DOCUMENTO: 'pi pi-file-export',
  // Il verbo «numera» dei lotti: rende definitivi i documenti assegnando il
  // numero. ⭐ Stesso cancelletto di `NUMERAZIONE` (T4, Tid 2026-09-27): il
  // numero e' cio' che il gesto da'. Dal 2026-09-27 il DB non manda piu'
  // glifi: il segno del verbo lo da' `core/aspettoAzioni.js`.
  NUMERA: 'pi pi-hashtag',
  //
  // ─── Verbi di stato dei documenti (core/aspettoAzioni.js) ─────────────────
  // Nati il 2026-09-27 col brief-db-icone-azioni-per-significato: i verbi che
  // non avevano gia' una costante col loro significato.
  // Affidare la merce al trasporto (DDT). ⚠️ Ripete `NAV_ICONS.VETTORE`: chi
  // spedisce la consegna al vettore. ⛔ Non `SEND`, che e' `emetti` (D-1 di
  // Tid) e sta nello stesso drawer.
  SPEDISCI: 'pi pi-truck',
  // La merce e' arrivata al destinatario (DDT). ⛔ Non `pi-check-circle`, che
  // e' `PUBLISH` e lo stato `OK`.
  CONSEGNA: 'pi pi-flag-fill',
  // La commessa e' pronta per la fatturazione. ⛔ Non `PUBLISH` ne'
  // `FATTURA_GENERA`: non pubblica e non genera niente, dichiara «si puo'».
  RENDI_PRONTA: 'pi pi-thumbs-up',
  // Nuova revisione di un'offerta/preventivo. ⭐ Stesso segno di `VERSIONI` di
  // proposito: la revisione e' una versione in piu'. ⛔ Non `pi-clone`
  // (`STATUS_ICONS.MULTIPLI`) ne' `CLONE` (duplica un record).
  NUOVA_REVISIONE: 'pi pi-history',
  // Allegare file a un documento / evento «allegato aggiunto» / file caricato
  // in attesa.
  ALLEGATI: 'pi pi-paperclip',
  // Direzione di un collegamento nella lineage (← origine, → destinazione).
  // ⛔ Non `BACK` (`pi-arrow-left`, torna indietro). Il ramo inverso e'
  // `CORREZIONE`.
  DOC_ORIGINE: 'pi pi-arrow-circle-left',
  DOC_DESTINAZIONE: 'pi pi-arrow-circle-right',
  // Pannello esiti del giro di fatturazione. ⛔ Non `pi-chart-bar`, che e' la
  // voce Dashboard competenza.
  ESITI: 'pi pi-chart-line',
  // Formati di export. ⛔ Il CSV non porta `pi-file`, che e'
  // `FAMIGLIA_DOCUMENTO`.
  FORMATO_XLSX: 'pi pi-file-excel',
  FORMATO_CSV: 'pi pi-file-o',
  //
  // ─── Prezzi e listini ──────────────────────────────────────────────────────
  // Strumento diagnostico «quale prezzo colpisce questo contesto»: apertura
  // ed esecuzione portano lo stesso segno. ⛔ Non `pi-search` (RICERCA).
  TEST_PREZZO: 'pi pi-bullseye',
  // Variazione percentuale dei prezzi di una versione di listino. Assorbe
  // l'ex `NAV_ICONS.PERCENTAGE` (nome di disegno, senza lettori).
  VARIAZIONE_PREZZO: 'pi pi-percentage',
  // Escludere una riga dall'eccezione di listino (la toglie dalla vendita a
  // quel prezzo). ⛔ Non `DISATTIVA`: la riga non si spegne.
  ESCLUDI: 'pi pi-cart-minus',
  // Tornare al prezzo di listino (ripristina l'eccezione, «usa il prezzo di
  // listino»). ⛔ Non `CORREZIONE` ne' `UNDO`.
  RIPRISTINA_LISTINO: 'pi pi-reply',
  // Riallineare un prezzo a quello vigente («rendilo uguale»). ⛔ Non
  // `CONVERSIONI` (`pi-sync`, le unita' di misura).
  RIALLINEA: 'pi pi-equals',
  // La categoria «commerciale» delle prestazioni di una pratica (tile
  // «Comincia» della home pratiche): il rapporto col cliente, la rubrica di chi
  // si segue. ⛔ Non il carrello (`NAV_ICONS.VENDITE`), che e' la categoria
  // «vendite» accanto (Tid 2026-09-27: due categorie, due segni).
  COMMERCIALE: 'pi pi-address-book',
  // Chiedere l'approvazione di livello 2 (chiede un «si'» a qualcun altro).
  // ⛔ Non `SEND`, che spinge a valle, ne' `APPROVE`, che e' il si'.
  RICHIEDI_APPROVAZIONE: 'pi pi-question-circle',
  //
  // ─── Incassi e competenza ──────────────────────────────────────────────────
  // Legare l'incasso alla rata. Ripete `NAV_ICONS.CODA_ABBINARE`: e' la porta
  // della stessa coda.
  ABBINA: 'pi pi-link',
  // Accredito richiesto al cliente (registro commessa). ⚠️ Ripete
  // `NAV_ICONS.ECCEDENZE` (C18): l'eccedenza diventa credito, concetto vicino.
  ACCREDITO: 'pi pi-money-bill',
  // Generare righe della distinta scegliendole dalle rate. ⛔ Non
  // `pi-list-check`, che e' la voce Inventari.
  RIGHE_DA_RATE: 'pi pi-file-import',
  // Riportare i residui al periodo successivo. ⛔ Non `pi-replay`
  // (`CORREZIONE`): i residui vanno avanti nel calendario, non si correggono.
  RIPORTA: 'pi pi-calendar-plus',
  // La scheda «fondi da decidere» del tool di fatturazione: denaro in attesa
  // di destinazione. ⛔ Non `pi-wallet` (Distinte, conti bancari).
  FONDI: 'pi pi-euro',
  // Rinunciare (alla riconsegna di un reso). ⛔ Non `DISATTIVA` (`pi-ban`) ne'
  // `REJECT`: non si spegne niente e non si respinge una richiesta altrui.
  RINUNCIA: 'pi pi-thumbs-down',
  //
  // ─── Scegliere, predefinire, valori ricavati ──────────────────────────────
  // I preferiti dell'operatore (menu, pannello Home, stato vuoto).
  PREFERITI: 'pi pi-star',
  // «E' nei preferiti» (il clic lo toglie). Coppia di `PREFERITI`.
  PREFERITO_ATTIVO: 'pi pi-star-fill',
  // Il valore che vale quando non si dice altro (mapping di default, conto
  // predefinito). ⛔ Non la stella (`PREFERITI`) ne' la spunta cerchiata
  // (`PUBLISH`).
  PREDEFINITO: 'pi pi-thumbtack',
  // Hint «valore ricavato dal contesto» (istanza derivata dal BA o dalla
  // pratica). ⛔ Non `pi-link` (`ABBINA`).
  DERIVATO: 'pi pi-arrow-down-right',
  // Scegliere questa voce fra piu' (es. «usa questo indirizzo»): e' un
  // bottone radio. ⛔ Non `CONFIRM`: non si conferma un form.
  SELEZIONA: 'pi pi-circle-on',
  // Generare un valore invece di digitarlo (es. il codice fiscale).
  // ⚠️ Non e' l'assistente AI, che ha `NAV_ICONS.ASSISTENTE_AI`.
  GENERA: 'pi pi-sparkles',
  // Fissare l'entita' come contesto di lavoro della sessione. ⛔ Non
  // `PUBLISH` (`pi-check-circle`) ne' `PREDEFINITO`.
  IMPOSTA_CONTESTO: 'pi pi-bookmark',
  // Badge «figlio di» (billing account padre): la freccia punta al padre.
  // ⛔ Non `pi-sitemap`, che e' la `BOM`.
  GERARCHIA: 'pi pi-arrow-up-left',
  //
  // ─── Liste, elenchi, campi ─────────────────────────────────────────────────
  // Riordinare (colonne, widget). ⛔ Non `EXPAND`/`COLLAPSE`.
  SPOSTA_SU: 'pi pi-arrow-up',
  SPOSTA_GIU: 'pi pi-arrow-down',
  // Ripristinare le impostazioni di default (colonne, widget): «torna
  // all'inizio». ⛔ Non `RELOAD` (`pi-refresh`), che rilegge i dati.
  RIPRISTINA_DEFAULT: 'pi pi-fast-backward',
  // Togliere un elemento da un ELENCO (file caricato, riga d'archivio) senza
  // eliminare il record. ⛔ Non `DELETE` ne' `CANCEL`.
  TOGLI: 'pi pi-delete-left',
  // Svuotare un campo o una conversazione. ⛔ Non `CANCEL` (chiude) ne'
  // `FILTRI_PULISCI` (toglie i filtri).
  SVUOTA: 'pi pi-eraser',
  // Anteprima del risultato (email, variazione) prima di farlo. ⛔ Non
  // `INSPECT` (`pi-eye`), che guarda cio' che c'e' gia'.
  ANTEPRIMA: 'pi pi-image',
  // «Vedi novita'» del preset di lista. ⛔ Non `INSPECT`.
  NOVITA: 'pi pi-bell',
  //
  // ─── Accessi, inviti, sessioni ─────────────────────────────────────────────
  // Inviare/reinviare un invito (portale, shop, operatore). ⚠️ L'invito E'
  // un'email: condivide la busta con `RECAPITO_ICONS.EMAIL` e
  // `NAV_ICONS.EMAIL`, come `REGISTRA`/`CLOSE` condividono il lucchetto.
  INVITA: 'pi pi-envelope',
  // Attivare l'accesso allo shop (T8, Tid 2026-09-27: il negozio resta qui, il
  // ruolo RESELLER passa al megafono). ⛔ Non `pi-shopping-bag` (ACQUISTI).
  ACCESSO_SHOP: 'pi pi-shop',
  // Gli accessi al portale web di un soggetto. ⛔ Non `pi-globe`, che e' la
  // geografia (provincia/regione/stato).
  ACCESSI_WEB: 'pi pi-sign-in',
  // Le sessioni attive dell'operatore (titolo del pannello). ⛔ Non
  // `PERMISSIONS` (`pi-shield`).
  SESSIONI: 'pi pi-desktop',
  // Revocare una sessione (butta fuori quel dispositivo). ⛔ Non `CANCEL`
  // (`pi-times`) ne' `LOGOUT` (esco io, da qui).
  REVOCA: 'pi pi-eject',
  // Provare la connessione di un account email.
  TEST_CONNESSIONE: 'pi pi-wifi',
  //
  // ─── Tecnico e giornale ────────────────────────────────────────────────────
  // Riesporre il plumbing del motore (super-admin). ⛔ Non `pi-wrench`
  // (dominio Strumenti).
  MODALITA_TECNICA: 'pi pi-code',
  // Rinascondere il plumbing. Coppia di `INSPECT` (`pi-eye`).
  NASCONDI_TECNICO: 'pi pi-eye-slash',
  // Evento «priorita' cambiata».
  PRIORITA: 'pi pi-flag',
  // La spia «strumenti usati» dall'assistente AI. ⛔ Non `pi-cog`
  // (`PERSONALIZZA`, `NAV_ICONS.CONFIG`).
  STRUMENTI_AI: 'pi pi-microchip',
  //
  // ─── Periodi (anno, mese) ──────────────────────────────────────────────────
  // Stessi glifi del paginator PrimeVue. ⛔ Non `ROW_EXPAND`
  // (`pi-chevron-right`), che apre una riga.
  PRECEDENTE: 'pi pi-angle-left',
  SUCCESSIVO: 'pi pi-angle-right',
  //
  // ─── Guscio dell'app (topbar, sidebar, finestre) ──────────────────────────
  // Apre il menu su mobile.
  MENU: 'pi pi-bars',
  // Esci dall'applicazione.
  LOGOUT: 'pi pi-sign-out',
  // Cambio lingua. ⛔ Non `pi-globe` (geografia).
  LINGUA: 'pi pi-language',
  // Passa a tema chiaro / scuro.
  TEMA_CHIARO: 'pi pi-sun',
  TEMA_SCURO: 'pi pi-moon',
  // Espandi / comprimi la sidebar.
  SIDEBAR_ESPANDI: 'pi pi-angle-double-right',
  SIDEBAR_COMPRIMI: 'pi pi-angle-double-left',
  // Ingrandisci / riduci un widget flottante.
  FINESTRA_ESPANDI: 'pi pi-window-maximize',
  FINESTRA_RIDUCI: 'pi pi-window-minimize',
  // Affianca due tab (vista divisa).
  AFFIANCA: 'pi pi-objects-column',
  // Scambia i due pannelli affiancati. ⛔ Non `pi-arrows-h`, che e' la voce
  // Unita' di misura.
  SCAMBIA: 'pi pi-arrow-right-arrow-left',
}

// Icone di STATO / ESITO (2026-09-27, T12 del censimento icone). ⛔ Non sono
// GESTI (quelli stanno in `MANAGE_ICONS`) ne' PORTE dell'app (`NAV_ICONS`): una
// spia dice com'e' una cosa, non cosa si puo' farne. Tenerle a parte e' cio'
// che impedisce a un «si'» di prendere in prestito la spunta di `CONFIRM`, o a
// un «bloccato» il lucchetto di `CLOSE`.
// Uso: <i :class="STATUS_ICONS.INFO" />
export const STATUS_ICONS = Object.freeze({
  // ═══ I DUE SEGNI CHE SI CONFONDONO, e vanno tenuti separati ═══════════
  //
  // ⭐ ERRORE — «qualcosa è andato storto». Era già lo standard DI FATTO in una
  //    ventina di punti (`ErroreRigaInfo`, la spia della lista lotti, le
  //    conferme di `useConfirmAction`, la vista d'errore): qui prende un NOME,
  //    perché un segno usato ovunque senza nome è un segno che il ventunesimo
  //    consumatore copia dal vicino sbagliato. ⛔ Non è `MANAGE_ICONS.ANNULLA`
  //    (il gesto che disfa un atto).
  ERRORE: 'pi pi-exclamation-triangle',
  //
  // ⚠️ ATTESA — lavoro che deve ancora essere fatto: non è un errore e non è un
  //    ritardo. ⛔ Serve perché il triangolo torna all'errore: senza, i due
  //    conteggi del semaforo mese porterebbero lo STESSO glifo distinti dal
  //    solo colore. ⛔ E non `pi-clock`, che in quella stessa schermata dice
  //    già «in ritardo» (`IN_RITARDO`).
  ATTESA: 'pi pi-hourglass',
  //
  // In ritardo / anzianita'. ⛔ Non `ATTESA`: il lavoro in attesa non e'
  // ancora in ritardo.
  IN_RITARDO: 'pi pi-clock',
  // C'e' qualcosa da sapere (nota, perimetro, motivo). Controparte di `ERRORE`.
  INFO: 'pi pi-info-circle',
  //
  // ─── Lo stato vuoto ───────────────────────────────────────────────────────
  // Niente da mostrare / non ancora caricato. ⚠️ Ripete
  // `NAV_ICONS.CODE_LAVORO` (T7, Tid 2026-09-27): la coda e' un vassoio, lo
  // stato vuoto e' un vassoio vuoto al centro di un'area con testo — mai un
  // gesto.
  VUOTO: 'pi pi-inbox',
  // «Caricato, e non c'e' niente che non va». ⚠️ Stesso glifo di
  // `MANAGE_ICONS.PUBLISH`: qui e' uno stato, mai un bottone.
  TUTTO_OK: 'pi pi-check-circle',
  //
  // ─── Esiti e spie ─────────────────────────────────────────────────────────
  // Esito positivo di una verifica (diagnosi del resolver prezzi): stesso
  // segno di `TUTTO_OK`, perche' dice la stessa cosa su un singolo controllo.
  OK: 'pi pi-check-circle',
  // La verifica non si applica a questo caso (il trattino del «n/a»).
  // ⛔ Non `MANAGE_ICONS.ANNULLA` (`pi-times-circle`): non e' un fallimento.
  NON_APPLICABILE: 'pi pi-minus',
  // Spia booleana «si'» (default, esposto, regolare, compilato). ⛔ Non la
  // spunta nuda, che e' `CONFIRM`/`APPROVE`: una spia non si clicca.
  SI: 'pi pi-check-square',
  // Spia booleana «no»: la coppia di `SI` (quadrato vuoto accanto a quello
  // spuntato). ⛔ Non `NON_APPLICABILE`: «no» e' una risposta, «n/a» dice che
  // la domanda non si pone.
  NO: 'pi pi-stop',
  // Caricamento in corso. Lo spinner di PrimeIcons con la sua rotazione: una
  // costante sola, cosi' il segno dell'attesa breve e' lo stesso ovunque.
  // ⛔ Non `ATTESA` (`pi-hourglass`): quello e' lavoro da fare, non un dato
  // che sta arrivando.
  CARICAMENTO: 'pi pi-spin pi-spinner',
  // Il passo si esegue da solo (handler automatico nel percorso pratica).
  // ⛔ Non `pi-bolt`, che e' `MANAGE_ICONS.UTILITY`; ne' `ESEGUI`, che e' il
  // gesto di chi lo avvia.
  AUTOMATICO: 'pi pi-step-forward',
  // Bloccato / non disponibile / serve un'autorizzazione. ⛔ Non il lucchetto
  // (`CLOSE`, `REGISTRA`, `VIETATO`): qui la cosa e' ferma, non chiusa.
  BLOCCATO: 'pi pi-stop-circle',
  // Chiuso / scartato / natura bloccata: uscito dal gioco. ⛔ Non `pi-ban`
  // (`MANAGE_ICONS.DISATTIVA`, il gesto).
  ESCLUSO: 'pi pi-minus-circle',
  // Superato da una versione piu' recente. ⛔ Non `pi-history`
  // (`MANAGE_ICONS.VERSIONI`, la cronologia).
  SUPERATO: 'pi pi-angle-double-up',
  // «Piu' di uno» (commesse, registri) in una cella. ⚠️ C19: glifo vicino a
  // `MANAGE_ICONS.CLONE` (`pi-copy`), non affiancarli.
  MULTIPLI: 'pi pi-clone',
  // Evento di giornale senza icona propria (vocabolario aperto dal DB).
  EVENTO: 'pi pi-circle',
  //
  // Sola lettura: il livello LETTURA sull'area o sull'oggetto (badge
  // «Modalita' consultazione»). ⚠️ Stesso occhio di `MANAGE_ICONS.INSPECT`, come
  // `TUTTO_OK` con `PUBLISH`: qui e' uno stato, mai un bottone.
  SOLA_LETTURA: 'pi pi-eye',
  //
  // ─── Pagine di stato ──────────────────────────────────────────────────────
  // Accesso negato (403). ⚠️ Lucchetto come `CLOSE`/`REGISTRA`: la porta e'
  // chiusa per chi guarda.
  VIETATO: 'pi pi-lock',
  // Pagina inesistente (404). ⛔ Non `pi-map`, che e' `MANAGE_ICONS.UBICAZIONI`
  // (P2): la bussola dice «qui non si arriva».
  NON_TROVATO: 'pi pi-compass',
  // Funzione non ancora costruita. ⛔ Non `pi-wrench` (dominio Strumenti).
  IN_COSTRUZIONE: 'pi pi-hammer',
})

// Icone di CAMPO: il tipo di recapito / identificativo in una scheda (card
// contatti, conti bancari). ⛔ Non sono gesti ne' porte, per questo non stanno
// in `MANAGE_ICONS`; hanno un nome perche' si ripetono fra card e drawer.
export const RECAPITO_ICONS = Object.freeze({
  // ⚠️ Stessa busta di `MANAGE_ICONS.INVITA` e `NAV_ICONS.EMAIL`: tutti «un'email».
  EMAIL: 'pi pi-envelope',
  TELEFONO: 'pi pi-phone',
  CELLULARE: 'pi pi-mobile',
  // ⚠️ C20: stessa chiocciola di `NAV_ICONS.ACCOUNT_EMAIL`. Icona di campo,
  // accettata dal censimento.
  PEC: 'pi pi-at',
  // Codice BIC/SWIFT: la banca. ⚠️ Stesso segno di `NAV_ICONS.CANALI_INCASSO`
  // e del ruolo BANCA: il concetto «banca» e' uno solo.
  BIC: 'pi pi-building-columns',
  // La filiale della banca: l'edificio. ⚠️ Stesso segno di
  // `MANAGE_ICONS.BUILDING` e `NAV_ICONS.COMUNE`: tutti «una sede».
  FILIALE: 'pi pi-building',
})

// Scope readonly — area (schema DB) passata come primo arg a useReadonlyMode.
// Unico punto dove compaiono i nomi degli schemi DB lato FE. Cambiare qui =
// cambiare ovunque senza rompere il refresh cross-tab o il matching permessi.
export const READONLY_DOMAINS = {
  AMM_SOFTWARE: 'amm_software',
  ANAGRAFICHE: 'anagrafiche',
  CATALOGO: 'catalogo',
  CONFIG: 'config',
  DOCUMENTI: 'documenti',
  // Area del dominio magazzino (Lotto 2, 2026-09-18): il documento interno
  // (inventari, rettifiche) e la consultazione (disponibilita', movimenti).
  // Permesso di AREA: il dominio non ha un livello oggetto a catalogo.
  MAGAZZINO: 'magazzino',
  // Area dedicata del dominio Strumenti (code di lavoro; l'area `core` resta
  // all'infra tracciamento, non si apre agli operatori per le code).
  STRUMENTI: 'strumenti',
  PAGAMENTI: 'pagamenti',
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
  LISTINO: 'listino',
  OFFERTA_COMMERCIALE: 'offerta_commerciale',
  ORDINE: 'ordine',
  PRATICA: 'pratica',
  PREVENTIVO: 'preventivo',
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
  FATTURA: 'fattura',
  EMAIL_ACCOUNTS: 'email-accounts',
  EMAIL_TEMPLATES: 'email-templates',
  EMITTENTE_FISCALE: 'emittente-fiscale',
  FORNITORE: 'fornitore',
  INDIRIZZO: 'indirizzo',
  // Le due famiglie del documento interno di magazzino (Lotto 2): producer =
  // i verbi degli store `documentiInterni`, consumer = le due liste.
  INVENTARIO: 'inventario',
  LISTINO: 'listino',
  // L'anagrafica dei magazzini (2026-09-21): producer = i verbi dello store
  // `magazzini` E quelli delle ubicazioni (cambiano `ubicazioni_count` del
  // padre); consumer = la lista magazzini.
  MAGAZZINO: 'magazzino',
  OFFERTA_COMMERCIALE: 'offerta_commerciale',
  OPERATORE: 'operatore',
  ORDINE: 'ordine',
  PRATICA: 'pratica',
  PREVENTIVO: 'preventivo',
  PROFILO_REPARTO: 'profilo-reparto',
  PROMO_ARTICOLI: 'promo_articoli',
  PROVINCIA: 'provincia',
  REGIONE: 'regione',
  RETTIFICA: 'rettifica',
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

// Schede della vista «Code di lavoro» (Strumenti → Code di lavoro).
//
// ⚠️ Sono un CONTRATTO fra due file che non si vedono: il drawer rapido del
//    badge in topbar (`CodeLavoroDrawer`, producer del deep-link `?tab=`) e la
//    vista che lo consuma (`CodeLavoroView`). Scritte come literal, un refuso
//    non fallisce: la vista aprirebbe la scheda di default e il click sulla
//    sezione «Coda stampa» porterebbe in silenzio sui lavori.
// ⛔ Stanno in `core/` e non in `strumenti/constants.js` perche' il producer e'
//    un componente di `core/`: un modulo di core che importasse da un dominio
//    invertirebbe gli anelli.
export const CODE_TABS = Object.freeze({
  LAVORI: 'lavori',
  STAMPA: 'stampa',
})

// Scopo: le schede della vista «Processi automatici» (`ProcessiAutomaticiListView`).
// ⚠️ Stesso contratto di `CODE_TABS`: il pallino dei presidi in topbar
//    (`AppTopbar`, producer del deep-link `?tab=`) apre la vista GIÀ sui
//    presidi. Scritto come literal, un refuso non fallirebbe: il click sul
//    pallino rosso porterebbe in silenzio sulla lista dei processi.
export const PROCESSI_TABS = Object.freeze({
  PROCESSI: 'processi',
  PRESIDI: 'presidi',
})

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

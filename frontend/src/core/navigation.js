// Configurazione centralizzata della navigazione per dominio.
// Sidebar, HomeView e store navigation leggono da qui — un'unica fonte di verita'.

import { MANAGE_ICONS, READONLY_DOMAINS, TIPO_RUOLO } from './constants'

// ── Dove si apre la scheda di un soggetto, dato il tipo ruolo ──
// La lista anagrafica che legge il CONTESTO globale (`useContextStore`) e apre
// da se' il drawer: cliente e fornitore la loro, ogni altro tipo (o nessuno)
// quella dei soggetti. ⭐ Regola del 2 (ok Tid 2026-10-02): la ricerca
// universale (`SearchDrawer`) e il salto da una veste alla sua scheda
// (`useSchedaVeste`) la scrivevano ognuno per se'.
export const ROTTA_LISTA_SOGGETTI = 'anagrafiche-soggetti'
export const ROTTA_LISTA_PER_TIPO_RUOLO = Object.freeze({
  [TIPO_RUOLO.CLIENTE]: 'anagrafiche-clienti',
  [TIPO_RUOLO.FORNITORE]: 'anagrafiche-fornitori',
})

// Scopo: il nome della rotta della lista che apre la scheda di quel tipo
//        ruolo; ripiego sulla lista dei soggetti.
export function rottaListaTipoRuolo(codiceTipoRuolo) {
  return ROTTA_LISTA_PER_TIPO_RUOLO[codiceTipoRuolo] || ROTTA_LISTA_SOGGETTI
}

export const NAV_ICONS = Object.freeze({
  ANAGRAFICHE: 'pi pi-users',
  CATALOGO: 'pi pi-box',
  VENDITE: 'pi pi-shopping-cart',
  ACQUISTI: 'pi pi-shopping-bag',
  MAGAZZINO: 'pi pi-warehouse',
  PAGAMENTI: 'pi pi-credit-card',
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
  // ⛔ Non `pi-inbox` (la coda lavori e lo stato vuoto) ne' `pi-chart-line`
  //    (`MANAGE_ICONS.ESITI`): il backlog e' il lavoro che scade nel tempo.
  DASHBOARD_BACKLOG: 'pi pi-calendar-clock',
  LOTTI: 'pi pi-server',
  // Tool della fatturazione (vendite): cassetta attrezzi del giro, distinta
  // dal dominio Strumenti (pi-wrench) che raccoglie le viste trasversali.
  TOOL_FATTURAZIONE: 'pi pi-sliders-v',
  PROMO_ARTICOLI: 'app-nav-icon app-nav-icon-promo-articoli',
  PERSONALIZZAZIONI_LISTE: 'pi pi-th-large',
  // Dominio Strumenti (viste operative trasversali: code di lavoro, in
  // futuro giri/job). pi-wrench = cassetta attrezzi, non-tecnico.
  STRUMENTI: 'pi pi-wrench',
  CODE_LAVORO: 'pi pi-inbox',
  // Il gruppo Diagnostica di Strumenti (2026-10-06): il battito del sistema —
  // processi, audit, errori, email. Glifo non usato da altre chiavi.
  // ⛔ Non `PROCESSI_AUTOMATICI` ne' `ERROR_LOG`: sono due delle
  //    voci DENTRO il gruppo, e il gruppo non e' nessuna di loro.
  DIAGNOSTICA: 'pi pi-wave-pulse',
  // Dominio INCASSI. ⚠️ Nessuna e' l'icona del dominio (`pi-credit-card`): una
  // voce di menu che ripete l'icona del suo dominio non distingue niente.
  DISTINTE: 'pi pi-wallet',
  // Le due porte della stessa coda: `pi-link` = legare l'incasso alla rata,
  // `pi-pause` = messa da parte in attesa di risoluzione.
  CODA_ABBINARE: 'pi pi-link',
  CODA_SOSPESE: 'pi pi-pause',
  RATE_FUORI_CAPIENZA: 'pi pi-exclamation-triangle',
  ECCEDENZE: 'pi pi-money-bill',
  CANALI_INCASSO: 'pi pi-building-columns',
  // Dominio MAGAZZINO (Lotto 2, 2026-09-18). ⚠️ Nessuna e' l'icona del
  // dominio (`pi-warehouse`), per la stessa ragione degli incassi.
  // L'inventario e' il CONTEGGIO a scaffale (la lista spuntata); la rettifica
  // e' una correzione in piu' o in meno (le due frecce); la disponibilita' e'
  // «quanto c'e'» (l'indicatore); il registro dei movimenti e' il libro.
  // L'anagrafica dei magazzini (2026-09-21): il DEPOSITO come luogo — e' la
  // sola voce del dominio con l'icona del dominio, perche' e' la cosa che il
  // dominio nomina.
  MAGAZZINI: 'pi pi-warehouse',
  INVENTARI: 'pi pi-list-check',
  RETTIFICHE: 'pi pi-sort-alt',
  DISPONIBILITA: 'pi pi-gauge',
  MOVIMENTI: 'pi pi-book',
  // Osservabilita' (2026-09-19): il registro degli errori tecnici (Amm.
  // Software) e il giornale trasversale degli eventi (Strumenti). ⚠️ Il
  // giornale ripete `pi-book` dei movimenti di magazzino: sono entrambi un
  // REGISTRO che si legge in ordine di tempo, e la voce sta in un altro
  // dominio.
  // ⭐ Famiglia dei diari di Diagnostica (Tid 2026-10-24): base righe di
  //    testo + simbolo di che cosa registrano (main.css, `app-nav-icon-log-*`).
  ERROR_LOG: 'app-nav-icon app-nav-icon-log-errori',
  GIORNALE: 'pi pi-book',
  HOME: 'pi pi-home',
  BACK: 'pi pi-arrow-left',

  // ═══ Voci di Amministrazione software (2026-09-27, censimento icone P1) ═══
  // Il nome e' quello della VOCE, non del disegno: prima erano `KEY`,
  // `SITEMAP`, `SHIELD`… — e una chiave col nome del glifo invita a usarla
  // ovunque serva quel glifo, qualunque cosa voglia dire.
  //
  // Profili di reparto: l'organigramma. ⚠️ Stesso albero di
  // `MANAGE_ICONS.BOM` (distinta base): due alberi, da decidere se separarli.
  PROFILI_REPARTO: 'pi pi-sitemap',
  // Definizioni workflow: il PERCORSO di una pratica (il cartello). ⛔ Non
  // piu' `pi-sitemap`, che portava anche i profili di reparto — due voci dello
  // stesso menu con un segno solo.
  DEFINIZIONI_WORKFLOW: 'pi pi-directions-alt',
  // Chi EMETTE i documenti fiscali. ⛔ Non `pi-id-card`, che e'
  // `MANAGE_ICONS.CONTATTI`.
  EMITTENTI_FISCALI: 'pi pi-file-check',
  // Le categorie clienti (T10, Tid 2026-09-27: tengono le etichette;
  // `MANAGE_ICONS.LOTTO_MAGAZZINO` e' passato al codice a barre).
  CATEGORIE_CLIENTI: 'pi pi-tags',
  // Il registro delle modifiche: chi ha cambiato cosa. Famiglia dei diari
  // (vedi `ERROR_LOG`), simbolo la matita. ⛔ Non `pi-history`, che e'
  // `MANAGE_ICONS.VERSIONI` (le versioni di un listino); ⛔ non piu'
  // `pi-user-edit`, che diceva «modifica un utente», non «registro».
  AUDIT_LOG: 'app-nav-icon app-nav-icon-log-audit',
  // Tutte le email inviate. ⛔ Non `EMAIL`: e' la voce accanto (le email
  // dell'operatore), e due voci dello stesso menu col segno solo non si
  // distinguono.
  EMAIL_LOG: 'app-nav-icon app-nav-icon-log-email',
  // Processi automatici: il server che lavora da solo, a ciclo (server +
  // frecce circolari, main.css `app-nav-icon-processi`, Tid 2026-10-24).
  // Distinta da CODE_LAVORO (la coda di ciò che sta girando adesso).
  // ⛔ Non piu' `pi-cog`: e' `CONFIG` e `MANAGE_ICONS.PERSONALIZZA`.
  PROCESSI_AUTOMATICI: 'app-nav-icon app-nav-icon-processi',
  // Gli account email di invio. ⚠️ C20: stessa chiocciola di
  // `RECAPITO_ICONS.PEC` (icona di campo).
  ACCOUNT_EMAIL: 'pi pi-at',
  // I modelli delle email: il gesto «componi». ⛔ Non `pi-file-edit`, che e'
  // `MANAGE_ICONS.NOTE`.
  TEMPLATE_EMAIL: 'pi pi-pen-to-square',
  // Le email (registro di invio, email dell'operatore). ⚠️ Stessa busta di
  // `MANAGE_ICONS.INVITA` e `RECAPITO_ICONS.EMAIL`: tutti «un'email».
  EMAIL: 'pi pi-envelope',
  // Anagrafiche: icone dedicate per le 3 liste root del modulo.
  // Soggetti = pi pi-users (omini, "anagrafe generale").
  // Clienti = icona composta receipt+user ("chi riceve fattura").
  // Fornitori = icona composta building+user ("azienda + persona di riferimento").
  CLIENTI: 'app-nav-icon app-nav-icon-clienti',
  FORNITORI: 'app-nav-icon app-nav-icon-fornitori',
  // Amministrazione operatori (singolo utente tecnico, distinto da
  // ANAGRAFICHE che usa pi-users per la rubrica multi-soggetto). E' anche la
  // voce di menu «Operatori» (C10: prima portava `pi-key`, che e'
  // `MANAGE_ICONS.SBLOCCA`) e l'avatar dell'operatore nel widget AI.
  OPERATORE: 'pi pi-user',
  // L'area «Accessi» (brief-db-be-fe-area-accessi, 2026-10-02): il censimento
  // di TUTTE le credenziali, in tre tab. ⭐ Stesso segno degli accessi web di
  // un soggetto (`MANAGE_ICONS.ACCESSI_WEB`): e' la stessa cosa — gli accessi —
  // guardata per tutti invece che per uno. Riferita, non ricopiata.
  ACCESSI: MANAGE_ICONS.ACCESSI_WEB,
  // L'assistente AI: pulsante topbar, voce menu mobile, header e avatar del
  // widget. E' una porta dell'app, per questo sta qui.
  ASSISTENTE_AI: 'pi pi-microchip-ai',
  // Toponomastica / gestione indirizzi (drawer dedicati in core/components).
  // pi-building per il comune (edificio civico, distinto dal fornitore
  // che usa l'icona composta building+user). pi-globe condiviso tra
  // provincia/regione/stato (gerarchia geografica omogenea).
  // INDIRIZZO e' anche la voce di menu Indirizzi (ex `MAP_MARKER`, stesso
  // valore e stesso significato: una chiave sola).
  INDIRIZZO: 'pi pi-map-marker',
  TOPONOMASTICA: 'pi pi-directions',
  COMUNE: 'pi pi-building',
  // Il CAP e' un punto sulla mappa (T9, Tid 2026-09-27). ⚠️ Stesso segnaposto
  // di `INDIRIZZO`, accettato: e' un pezzo dell'indirizzo. ⛔ Non piu'
  // `pi-inbox`, che e' la coda lavori.
  CAP: 'pi pi-map-marker',
  PROVINCIA: 'pi pi-globe',
  REGIONE: 'pi pi-globe',
  STATO: 'pi pi-globe',
  // Unita' di misura (le due frecce della grandezza). La ripete
  // `MANAGE_ICONS.UOM` (Tid 2026-09-27: un concetto, un segno).
  UNITA_MISURA: 'pi pi-arrows-h',
  // Famiglie di documento. Ripetuta da `MANAGE_ICONS.FAMIGLIA_DOCUMENTO`.
  FAMIGLIE_DOCUMENTO: 'pi pi-file',
  // Gestione pratiche (la cartella aperta). ⚠️ Stesso segno di
  // `MANAGE_ICONS.ARCHIVE` (archivio documenti generati): preesistente, da
  // decidere.
  GESTIONE_PRATICHE: 'pi pi-folder-open',
})

// Icona del TIPO DI RUOLO di un soggetto (chip di contesto in topbar).
// Spostata da `stores/context.js` il 2026-09-27 (censimento icone §3.1d): sta
// accanto a NAV_ICONS perche' dove il ruolo ha una voce di menu (clienti,
// fornitori) ne RIPETE l'icona — chi vede il chip deve riconoscere «quella
// li'».
// ⚠️ Le CHIAVI sono i codici di ruolo che arrivano dal backend
// (`tipo_ruolo_codice`: `DISTRIB`, `BANK`…), non nomi scelti qui: rinominarle
// spegnerebbe l'icona senza errore.
// Ripiego (ruolo senza icona propria): `MANAGE_ICONS.SOGGETTO`, vedi
// `resolveTipoRuoloIcon`.
export const TIPO_RUOLO_ICONS = Object.freeze({
  CLIENTE: NAV_ICONS.CLIENTI,
  FORNITORE: NAV_ICONS.FORNITORI,
  // Chi tratta col cliente. ⛔ Non `pi-briefcase`, che e' `MANAGE_ICONS.COMMESSA`
  // (P8).
  VENDITORE: 'pi pi-comments',
  DISTRIB: 'pi pi-share-alt',
  // Chi rivende e promuove (T8, Tid 2026-09-27). ⛔ Non `pi-shop`, che e'
  // `MANAGE_ICONS.ACCESSO_SHOP`.
  RESELLER: 'pi pi-megaphone',
  // Chi trasporta: il camion, liberato dal fornitore (C16).
  VETTORE: 'pi pi-truck',
  // ⚠️ Stesso segno di `NAV_ICONS.CANALI_INCASSO` e `RECAPITO_ICONS.BIC`: il
  // concetto «banca» e' uno solo.
  BANK: 'pi pi-building-columns',
})

// Scopo: l'icona di un tipo di ruolo, col ripiego sul soggetto generico.
export function resolveTipoRuoloIcon(codice) {
  return TIPO_RUOLO_ICONS[codice] || MANAGE_ICONS.SOGGETTO
}
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
  { key: 'pratiche', icon: NAV_ICONS.PRATICHE, to: '/pratiche', schemaDb: 'pratiche' },
  // Strumenti: viste operative trasversali. ⛔ SENZA `schemaDb` sul dominio,
  // di proposito (Tid 2026-09-26, assorbe il dominio «Personale»): le sue voci
  // appartengono ad aree DIVERSE — le code all'area BE `strumenti` (decisione
  // Tid 2026-07-21: non si apre `core` solo per le code), il giornale a
  // `vendite`, le email dell'operatore a nessuna (`skip_area_check` delle
  // rotte BE, chi vede quale riga lo decide la RLS). Il cancello d'area sta
  // quindi sulla VOCE (`requireArea`), non sul dominio: un `schemaDb` qui
  // nasconderebbe le email a chi non ha l'area `strumenti`, mentre il backend
  // risponde.
  { key: 'strumenti', icon: NAV_ICONS.STRUMENTI, to: '/strumenti' },
  { key: 'config', icon: NAV_ICONS.CONFIG, to: '/config'},
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
//   adminOnly (opzionale, boolean) — solo il super admin. Per la voce che
//                               vive in un dominio aperto a tutti ma il cui
//                               backend e' `AdminAPIView` (Strumenti →
//                               Diagnostica).
//   ⚠️ I cancelli di un GRUPPO (voce con `children`) valgono per i figli:
//      li applica `isMenuItemAllowed` risalendo `gruppo`, che mette
//      `flattenMenu`. Un cancello si scrive una volta, sul gruppo.
export const DOMAIN_MENUS = {
  'amm-software': [
    { key: 'accessi', icon: NAV_ICONS.ACCESSI, to: '/amm-software/accessi' },
    { key: 'profili-reparto', icon: NAV_ICONS.PROFILI_REPARTO, to: '/amm-software/profili-reparto' },
    // ℹ️ Niente piu' voce «Permessi» (2026-10-06, Tid): il riepilogo e'
    //    «Mostra permessi» della lista in Accessi → Operatori, e una voce che
    //    porta li' accendeva «Accessi» nel menu. Il vecchio path resta come
    //    redirect (router).
    { key: 'emittenti-fiscali', icon: NAV_ICONS.EMITTENTI_FISCALI, to: '/amm-software/emittenti-fiscali' },
    // Accanto agli emittenti, ed e' la loro vicina di casa: i registri di
    // numerazione vivono nel drawer dell'emittente, la REGOLA che applicano
    // vive qui — globale, uguale per tutti.
    { key: 'famiglie-documento', icon: NAV_ICONS.FAMIGLIE_DOCUMENTO, to: '/amm-software/famiglie-documento' },
    { key: 'categorie-clienti', icon: NAV_ICONS.CATEGORIE_CLIENTI, to: '/amm-software/categorie-clienti' },
    { key: 'definizioni-workflow', icon: NAV_ICONS.DEFINIZIONI_WORKFLOW, to: '/amm-software/definizioni-workflow' },
    { key: 'matrici', icon: NAV_ICONS.TABELLE, to: '/amm-software/matrici' },
    // ⭐ Processi automatici, audit, errori tecnici e log email stanno in
    // Strumenti → Diagnostica dal 2026-10-06 (Tid): qui resta cio' che si
    // CONFIGURA, li' cio' che si GUARDA.
    { key: 'email-accounts', icon: NAV_ICONS.ACCOUNT_EMAIL, to: '/amm-software/email-accounts' },
    { key: 'email-templates', icon: NAV_ICONS.TEMPLATE_EMAIL, to: '/amm-software/email-templates' },
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
    { key: 'indirizzi', icon: NAV_ICONS.INDIRIZZO, to: '/anagrafiche/indirizzi' },
    // Presidio dei titoli IVA sfondati (I7/Q4): l'altra meta' della decisione
    // del team DB di NON bloccare il superamento sulle forzature.
    { key: 'titoli-iva-sfondati', icon: MANAGE_ICONS.TITOLI_IVA, to: '/anagrafiche/titoli-iva-sfondati' }
  ],
  'catalogo': [
    { key: 'articoli', icon: NAV_ICONS.CATALOGO, to: '/catalogo/articoli' },
    // Una voce sola per tutto l'impianto delle UdM: unita', conversioni e tipi
    // sono tre schede della stessa vista dal 2026-09-04 (erano tre voci, cioe'
    // tre quarti del menu di dominio, con l'articolo — il soggetto vero del
    // catalogo — ridotto a una voce fra quattro).
    { key: 'unita-misura', icon: NAV_ICONS.UNITA_MISURA, to: '/catalogo/unita-misura' }
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
    // ⭐ La settima lista del ciclo attivo, arrivata il 2026-08-24: fino ad
    // allora la fattura era l'unico documento senza la sua, e si raggiungeva
    // solo passando da un lotto o da un collegamento.
    { key: 'fatture', icon: NAV_ICONS.FATTURE, to: '/vendite/fatture' },
    { key: 'contratti', icon: NAV_ICONS.CONTRATTI, to: '/vendite/contratti' },
    { key: 'listini', icon: NAV_ICONS.LISTINI, to: '/vendite/listini' },
    { key: 'promo-articoli', icon: NAV_ICONS.PROMO_ARTICOLI, to: '/vendite/promo-articoli' },
    { key: 'approvazioni-prezzo', icon: NAV_ICONS.APPROVAZIONI_PREZZO, to: '/vendite/approvazioni-prezzo' },
    // ⭐ IN FONDO di proposito (scelta di Tid): i tool non sono un percorso
    // quotidiano — sono dove si va quando il giro automatico ha lasciato
    // qualcosa indietro. Gli elenchi che chiedono una persona vivono qui.
    {
      key: 'tool-fatturazione',
      icon: NAV_ICONS.TOOL_FATTURAZIONE,
      to: '/vendite/tool-fatturazione',
    }
  ],
  'acquisti': [],
  // ⭐ Dominio MAGAZZINO. L'ordine e' il PERCORSO DELLA MERCE, non l'alfabeto:
  //    il primo carico in assoluto si fa dall'inventario, una rettifica
  //    corregge quello che l'inventario ha scritto, la disponibilita' e' cio'
  //    che ne risulta, e il registro dei movimenti e' la storia di tutto —
  //    come per gli incassi, che seguono il percorso del denaro.
  'magazzino': [
    // Q-4 (Tid, 2026-09-21): voce propria, prima del blocco documenti.
    { key: 'magazzini', icon: NAV_ICONS.MAGAZZINI, to: '/magazzino/magazzini' },
    { key: 'inventari', icon: NAV_ICONS.INVENTARI, to: '/magazzino/inventari' },
    { key: 'rettifiche', icon: NAV_ICONS.RETTIFICHE, to: '/magazzino/rettifiche' },
    { key: 'disponibilita', icon: NAV_ICONS.DISPONIBILITA, to: '/magazzino/disponibilita' },
    { key: 'movimenti', icon: NAV_ICONS.MOVIMENTI, to: '/magazzino/movimenti' },
  ],
  // ⭐ Dominio INCASSI. L'ordine e' il PERCORSO del denaro, non l'alfabeto: si
  // apre una distinta, si abbinano le sue righe alle rate, e quello che non
  // torna finisce nei due elenchi in fondo.
  // ⭐ «Da abbinare» e «sospese» sono DUE PORTE DELLA STESSA LISTA (Q-4 -> c):
  // stesso seed a catalogo, filtro diverso — due mestieri, non due schermate.
  'pagamenti': [
    { key: 'distinte', icon: NAV_ICONS.DISTINTE, to: '/pagamenti/distinte' },
    { key: 'coda-abbinare', icon: NAV_ICONS.CODA_ABBINARE, to: '/pagamenti/righe/da-abbinare' },
    { key: 'coda-sospese', icon: NAV_ICONS.CODA_SOSPESE, to: '/pagamenti/righe/sospese' },
    { key: 'rate-fuori-capienza', icon: NAV_ICONS.RATE_FUORI_CAPIENZA, to: '/pagamenti/rate-fuori-capienza' },
    { key: 'eccedenze', icon: NAV_ICONS.ECCEDENZE, to: '/pagamenti/eccedenze' },
    // ⚠️ Ultima voce di proposito: e' CONFIGURAZIONE, non lavoro di giornata —
    //    metterla fra le code la farebbe sembrare una coda da smaltire.
    { key: 'canali-incasso', icon: NAV_ICONS.CANALI_INCASSO, to: '/pagamenti/canali-incasso' },
  ],
  // ⚠️ Ogni voce dichiara la SUA area (o nessuna): il dominio non ne ha una.
  'strumenti': [
    // Accesso primario = badge top bar; la voce menu e' la via secondaria
    // (brief gestione-code P-1).
    { key: 'code-lavoro', icon: NAV_ICONS.CODE_LAVORO, to: '/strumenti/code-lavoro', requireArea: 'strumenti' },
    // Il giornale trasversale degli eventi (osservabilita', pezzo G): «cosa e'
    // andato storto, su tutto», con il salto al lotto e al documento. Dati e
    // endpoint restano dell'area `vendite` (`/vendite/giornale/`): la voce ne
    // porta il cancello.
    { key: 'giornale', icon: NAV_ICONS.GIORNALE, to: '/strumenti/giornale', requireArea: 'vendite' },
    // Le email dell'operatore (dal 2026-09-26). ⛔ Senza `requireArea`: e' la
    // forma a video dello `skip_area_check` di `/core/email/log/`.
    { key: 'email', icon: NAV_ICONS.EMAIL, to: '/strumenti/email' },
    // ⭐ Diagnostica (Tid 2026-10-06): i diari del sistema, prima in
    // Amm. software. ⛔ `adminOnly` sul GRUPPO e su nessun figlio: le viste
    // nominano TUTTE le aziende senza RLS e il backend le serve solo al super
    // admin (`AdminAPIView`, endpoint rimasti sotto `/amm-software/`). I figli
    // ereditano il cancello da `flattenMenu`, che lo porta anche al router
    // guard: senza, il menu li nasconderebbe ma l'indirizzo li aprirebbe.
    {
      key: 'diagnostica',
      icon: NAV_ICONS.DIAGNOSTICA,
      adminOnly: true,
      children: [
        { key: 'processi-automatici', icon: NAV_ICONS.PROCESSI_AUTOMATICI, to: '/strumenti/diagnostica/processi-automatici' },
        { key: 'audit-log', icon: NAV_ICONS.AUDIT_LOG, to: '/strumenti/diagnostica/audit-log' },
        // Il registro degli errori tecnici (`dbops.error_log`): stessa
        // famiglia dei diari accanto (audit e email).
        { key: 'error-log', icon: NAV_ICONS.ERROR_LOG, to: '/strumenti/diagnostica/error-log' },
        // Tutte le email inviate. ⚠️ Non e' la voce `email` qui sopra (le
        // email dell'operatore, con la RLS): stessa lista, un'altra porta.
        { key: 'email-log', icon: NAV_ICONS.EMAIL_LOG, to: '/strumenti/diagnostica/email-log' }
      ]
    }
  ],
  'pratiche': [
    { key: 'home', icon: NAV_ICONS.HOME, to: '/pratiche' },
    { key: 'gestione', icon: NAV_ICONS.GESTIONE_PRATICHE, to: '/pratiche/gestione' }
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

// Scopo: appiattisce un menu di dominio in un unico elenco di voci
// (L1 + figli L2), per cercare una voce per `key` o per `to` senza
// dover conoscere la profondita' della struttura.
// Centralizzata qui perche' consumata da piu' composable di
// navigazione (preferiti, deep-link dei widget dashboard, router guard,
// schede): e' la definizione unica di "tutte le voci di questo dominio".
// ⛔ Ogni figlio esce con `gruppo` = la voce padre: e' cosi' che i cancelli
//    del gruppo arrivano a `isMenuItemAllowed`. Il figlio e' una COPIA:
//    nessuno confronti le voci per identita'.
export function flattenMenu(items) {
  return (items || []).flatMap(item =>
    item.children
      ? [item, ...item.children.map(child => ({ ...child, gruppo: item }))]
      : [item],
  )
}

// Scopo: la voce di menu e' permessa all'utente? Filtro UNICO dei cancelli di
// voce (`requireArea`, `requireAnyAction`, `adminOnly`, piu' quelli del
// `gruppo` da cui il figlio viene, vedi `flattenMenu`), letto da sidebar, preferiti,
// widget e router guard (estratto 2026-09-26, regola del 2, ok Tid).
// ⛔ Il router DEVE leggere la stessa regola della sidebar: un cancello solo a
// video lascia aprire la pagina dall'indirizzo, e l'utente trova una schermata
// di 403 invece di «Accesso negato».
// `auth` e' lo store (passato, non importato: questo modulo resta puro).
export function isMenuItemAllowed(item, auth) {
  if (!item) return false
  if (item.gruppo && !isMenuItemAllowed(item.gruppo, auth)) return false
  if (item.adminOnly && !auth.isSuperAdmin) return false
  if (item.requireArea && auth.isAreaBlocked(item.requireArea)) return false
  if (Array.isArray(item.requireAnyAction) && item.requireAnyAction.length > 0) {
    if (!auth.isSuperAdmin && !item.requireAnyAction.some(action => auth.isActionAllowed(action))) {
      return false
    }
  }
  return true
}

// Scopo: la voce di menu di una rotta, da `meta.domain` + `meta.menuKey`.
export function findMenuItem(domain, menuKey) {
  if (!domain || !menuKey) return null
  return flattenMenu(DOMAIN_MENUS[domain]).find(item => item.key === menuKey) || null
}

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

// Scopo: l'etichetta A VIDEO di una tab aperta, ricalcolata a ogni render
// (estratto 2026-09-26, regola del 2, ok Tid: barra delle tab e pannello
// affiancato). Un nome dato a mano (`customLabel`) vince; altrimenti si
// risolve da `domain`/`menuKey` e solo in ultima istanza si ripiega sulla
// `label` salvata.
// ⛔ La `label` salvata e' una FOTOGRAFIA presa all'apertura: se la tab nasce
// prima che i messaggi i18n siano caricati (boot, ripristino da localStorage)
// contiene la chiave grezza (`nav_menu.vendite.ordini`), e dopo un cambio
// lingua e' nella lingua vecchia. Mostrarla com'e' e' il difetto che questo
// BB chiude.
export function resolveTabDisplayLabel(tab, t, te = null) {
  if (!tab) return ''
  if (tab.customLabel) return tab.label
  return resolveNavigationLabel(tab, t, te) || tab.label
}

// Risolve l'icona tab dalla route meta.
// Cerca prima nelle voci L2 (DOMAIN_MENUS), poi nel dominio (DOMAINS).
export function resolveTabIcon(meta) {
  const { domain, menuKey } = meta
  if (menuKey && DOMAIN_MENUS[domain]) {
    const item = flattenMenu(DOMAIN_MENUS[domain])
      .find(m => m.key === menuKey)
    if (item) return item.icon
  }
  if (domain) {
    const d = DOMAINS.find(d => d.key === domain)
    if (d) return d.icon
  }
  return null
}

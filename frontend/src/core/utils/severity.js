// Helper centralizzati per mappatura codici → severity PrimeVue Tag/Badge.
// Un solo punto di modifica per i colori di stato in tutta l'applicazione.
// Ogni mappa associa codice_interno (con trim) a una severity PrimeVue.

// --- Resolver generico ---
// Scopo: Risolve severity da una mappa. Trim automatico, fallback 'secondary'.
export function resolveSeverity(map, codice) {
  return map[(codice || '').trim()] || 'secondary'
}

// --- Mappa stati cliente ---
// AT=attivo(verde), CH/CF/CM/CW=chiuso(rosso), AN=annulla(arancio),
// PR=pre-contratto(blu), SC/SF=sospeso(secondario), RS=richiesta sosp.(arancio)
export const STATO_CLIENTE_MAP = {
  AT: 'success',
  CH: 'danger',
  CF: 'danger',
  CM: 'danger',
  CW: 'danger',
  AN: 'warn',
  RS: 'warn',
  PR: 'info',
  AG: 'secondary',
  SC: 'secondary',
  SF: 'secondary',
}

// Scopo: Shortcut per stato cliente (usabile direttamente nei template).
export function statoClienteSeverity(codice) {
  return resolveSeverity(STATO_CLIENTE_MAP, codice)
}

// --- Mappa stati fornitore ---
// VE=in verifica(blu), AT=attivo(verde), SO=sospeso(arancio),
// CE=cessato(rosso), BL=blacklist(rosso)
export const STATO_FORNITORE_MAP = {
  VE: 'info',
  AT: 'success',
  SO: 'warn',
  CE: 'danger',
  BL: 'danger',
}

// Scopo: Shortcut per stato fornitore (usabile direttamente nei template).
export function statoFornitoreSeverity(codice) {
  return resolveSeverity(STATO_FORNITORE_MAP, codice)
}

// --- Mappa stati pratica ---
// BOZZA=secondario, APERTA=info, SOSPESA=arancio, CHIUSA=verde, ANNULLATA=rosso
export const STATO_PRATICA_MAP = {
  BOZZA: 'secondary',
  APERTA: 'info',
  SOSPESA: 'warn',
  CHIUSA: 'success',
  ANNULLATA: 'danger',
}

// Scopo: Shortcut per stato pratica.
export function statoPraticaSeverity(codice) {
  return resolveSeverity(STATO_PRATICA_MAP, codice)
}

// --- Mappa priorita' pratica ---
// BASSA=secondario, NORMALE=info, ALTA=arancio, URGENTE=rosso
export const PRIORITA_PRATICA_MAP = {
  BASSA: 'secondary',
  NORMALE: 'info',
  ALTA: 'warn',
  URGENTE: 'danger',
}
// Scala cromatica: grigio(bassa) → azzurro(normale) → arancio(alta) → rosso(urgente)

// Scopo: Shortcut per priorita' pratica.
export function prioritaPraticaSeverity(codice) {
  return resolveSeverity(PRIORITA_PRATICA_MAP, codice)
}

// --- Mappa stati flusso pratica ---
// DA_ESEGUIRE=secondario, IN_CORSO=info, COMPLETATO=verde, SOSPESO=arancio,
// ANNULLATO=rosso, ERRORE=rosso
export const STATO_FLUSSO_MAP = {
  DA_ESEGUIRE: 'secondary',
  IN_CORSO: 'info',
  COMPLETATO: 'success',
  SOSPESO: 'warn',
  ANNULLATO: 'danger',
  ERRORE: 'danger',
}

// Scopo: Shortcut per stato flusso pratica.
export function statoFlussoSeverity(codice) {
  return resolveSeverity(STATO_FLUSSO_MAP, codice)
}

// --- Mappa esiti flusso ---
// POSITIVO=verde, NEGATIVO=rosso, PARZIALE=arancio, NON_APPLICABILE=secondario
export const ESITO_FLUSSO_MAP = {
  POSITIVO: 'success',
  NEGATIVO: 'danger',
  PARZIALE: 'warn',
  NON_APPLICABILE: 'secondary',
}

// Scopo: Shortcut per esito flusso.
export function esitoFlussoSeverity(codice) {
  return resolveSeverity(ESITO_FLUSSO_MAP, codice)
}

// --- Mappa fase documento sorgente (proiezione stato dominio, V10) ---
// Vocabolario universale del descrittore doc_* (script.vw_stato_sorgente):
// APERTO=secondario (bozza), IN_ATTESA=arancio (si aspetta il cliente),
// IN_CORSO=info; CHIUSO colora per esito (verdetto): POSITIVO=verde,
// NEGATIVO=rosso, altrimenti secondario.
export const FASE_SORGENTE_MAP = {
  APERTO: 'secondary',
  IN_ATTESA: 'warn',
  IN_CORSO: 'info',
}

// Scopo: Severity per lo stato del documento sorgente proiettato nella
// pratica. `fase` guida il colore; su CHIUSO decide l'esito.
export function faseSorgenteSeverity(fase, esito) {
  if ((fase || '').trim() === 'CHIUSO') {
    return resolveSeverity(ESITO_FLUSSO_MAP, esito)
  }
  return resolveSeverity(FASE_SORGENTE_MAP, fase)
}

// --- Mappa azioni giornale pratica ---
// Associa azione giornale a severity e icona per la timeline audit.
// Chiavi = codici azione REALI del giornale (pratiche.giornale.azione, CHECK
// chk_giornale_azione), non nomi astratti: azioneGiornaleStyle riceve il codice
// grezzo (es. 'FLUSSO_STATO_CAMBIATO'), quindi le chiavi devono combaciare.
export const AZIONE_GIORNALE_MAP = {
  PRATICA_CREATA: { severity: 'info', icon: 'pi pi-plus-circle' },
  PRATICA_GENERATA: { severity: 'info', icon: 'pi pi-copy' },
  STATO_CAMBIATO: { severity: 'warn', icon: 'pi pi-sync' },
  PRIORITA_CAMBIATA: { severity: 'secondary', icon: 'pi pi-flag' },
  ASSEGNAZIONE_CAMBIATA: { severity: 'secondary', icon: 'pi pi-user' },
  FLUSSO_CREATO: { severity: 'info', icon: 'pi pi-sitemap' },
  FLUSSO_STATO_CAMBIATO: { severity: 'warn', icon: 'pi pi-sync' },
  FLUSSO_ASSEGNAZIONE_CAMBIATA: { severity: 'secondary', icon: 'pi pi-user-plus' },
  NOTA_AGGIUNTA: { severity: 'secondary', icon: 'pi pi-comment' },
  ALLEGATO_AGGIUNTO: { severity: 'secondary', icon: 'pi pi-paperclip' },
  SOSPENSIONE_REGISTRATA: { severity: 'warn', icon: 'pi pi-pause' },
  SOSPENSIONE_CHIUSA: { severity: 'success', icon: 'pi pi-play' },
}

const _AZIONE_DEFAULT = { severity: 'secondary', icon: 'pi pi-circle' }

// Eventi del REGISTRO delle righe di commessa (`vendite.commesse_attivita_log`).
// ⚠️ Le chiavi sono i CODICI del database, non nomi astratti: la funzione riceve
// il codice grezzo, quindi devono combaciare.
// ⛔ Vocabolario APERTO e posseduto dal DB: un evento nuovo non deve rompere
// niente — cade sul default e resta visibile col proprio codice. Mai una lista
// chiusa che faccia sparire ciò che non conosce.
export const EVENTO_REGISTRO_COMMESSA_MAP = {
  ONERE_AGGIUNTO: { severity: 'info', icon: 'pi pi-plus-circle' },
  RIGA_MANUALE_ANNULLATA: { severity: 'danger', icon: 'pi pi-times-circle' },
  // Il ritiro non è un errore: è il documento di origine che è stato annullato
  // e si è portato via il lavoro non ancora emesso.
  RIGA_RITIRATA_DA_SORGENTE: { severity: 'warn', icon: 'pi pi-undo' },
  RIGA_RIPORTATA_DA_EMETTERE: { severity: 'warn', icon: 'pi pi-replay' },
  ACCREDITO_RICHIESTO: { severity: 'info', icon: 'pi pi-money-bill' },
  ACCREDITO_ANNULLATO: { severity: 'secondary', icon: 'pi pi-ban' },
}

// Scopo: Risolve severity+icon per un evento del registro commessa.
//        Trim automatico, ripiego secondario sui codici non ancora mappati.
export function eventoRegistroCommessaStyle(evento) {
  return EVENTO_REGISTRO_COMMESSA_MAP[(evento || '').trim()] || _AZIONE_DEFAULT
}

// Scopo: Risolve severity+icon per azione giornale. Trim automatico, fallback secondario.
export function azioneGiornaleStyle(azione) {
  return AZIONE_GIORNALE_MAP[(azione || '').trim()] || _AZIONE_DEFAULT
}

// --- Mappa stati versione listino ---
// BOZZA=grigio, ATTIVA=verde, CHIUSA=arancio
export const STATO_VERSIONE_LISTINO_MAP = {
  BOZZA: 'secondary',
  ATTIVA: 'success',
  CHIUSA: 'warn',
}
export function statoVersioneListinoSeverity(codice) {
  return resolveSeverity(STATO_VERSIONE_LISTINO_MAP, codice)
}

// Scopo: Calcola lo stato "visibile" di una versione listino in modo data-driven:
//        se `valido_al` e` valorizzato e strettamente minore di oggi, la versione
//        e` operativamente CHIUSA anche se lo stato persistito in DB dice ancora
//        ATTIVA (il job notturno non e` ancora passato). Altrimenti restituisce
//        lo stato DB. Coerente con il principio fail-safe del brief listini v5
//        (brief-db-listini-stato-chiusa-sync.md §2): data = fonte di verita`
//        operativa, stato = flag informativo.
export function statoVersioneVisibile(versione) {
  if (!versione) return null
  const validoAl = versione.valido_al
  if (validoAl) {
    // Parsing tollerante: stringa ISO YYYY-MM-DD o Date
    const dataAl = validoAl instanceof Date ? validoAl : new Date(validoAl)
    const oggi = new Date()
    oggi.setHours(0, 0, 0, 0)
    dataAl.setHours(0, 0, 0, 0)
    if (dataAl < oggi) return 'CHIUSA'
  }
  return versione.stato
}

// --- Mappa stati preventivo vendita ---
// DRAFT=grigio, EMESSO=azzurro, ACCETTATO=verde, EVASO=azzurro,
// RIFIUTATO=rosso, SCADUTO=arancio, ANNULLATO=rosso.
// EVASO = stato terminale post-push commessa (transizione automatica
// ACCETTATO -> EVASO BE-driven): info per distinguerlo da ACCETTATO
// (= accettato dal cliente, fase vendita) e segnalare "lavorato".
export const STATO_PREVENTIVO_MAP = {
  DRAFT: 'secondary',
  EMESSO: 'info',
  ACCETTATO: 'success',
  EVASO: 'info',
  RIFIUTATO: 'danger',
  SCADUTO: 'warn',
  ANNULLATO: 'danger',
}

// Scopo: Shortcut per stato preventivo vendita.
export function statoPreventiveSeverity(codice) {
  return resolveSeverity(STATO_PREVENTIVO_MAP, codice)
}

// --- Mappa domini listino ---
// UTILITY=azzurro, COMMERCIO=arancio
export const DOMINIO_LISTINO_MAP = {
  UTILITY: 'info',
  COMMERCIO: 'warn',
}
export function dominioListinoSeverity(codice) {
  return resolveSeverity(DOMINIO_LISTINO_MAP, codice)
}

// --- Mappa origine match resolver pricing v5 ---
// PROMO=arancio (offerta speciale, stadio 0 batte tutto),
// CONTRATTO/CONTRATTO_LISTINO/CONTRATTO_OVERRIDE=azzurro (condizioni cliente
// specifiche), CATEGORIA=verde (listino di default per categoria cliente),
// LISTINO_BUNDLE=help (prezzo bundle del padre composito, modello unificato
// componenti BoM 2026-05-13, resolver bundle-aware STADIO 0; tinta distinta
// da CATEGORIA per evidenziare che e' un prezzo contestualizzato al padre),
// MANUALE=secondary (override manuale operatore, niente colore di sistema).
// Default 'secondary' per origini sconosciute o future.
// Usato cross-dominio: PreventiviRigaForm (badge sotto prezzo riga),
// PreventiviRigheTable (badge sotto componenti CASO A),
// TestResolverDialog (badge esito test), futuri prospect/ordini/fatture.
export const PRICING_ORIGINE_MAP = {
  PROMO: 'warn',
  CONTRATTO: 'info',
  CONTRATTO_LISTINO: 'info',
  CONTRATTO_OVERRIDE: 'info',
  CATEGORIA: 'success',
  LISTINO_BUNDLE: 'help',
  MANUALE: 'secondary',
}
export function pricingOrigineSeverity(codice) {
  return resolveSeverity(PRICING_ORIGINE_MAP, codice)
}

// Mapping origine -> chiave i18n del badge. Centralizzato per evitare drift
// fra consumer (PreventiviRigaForm legacy + PreventiviRigaComponentiPanel
// post-refactor 2026-05-11). Include `CONTRATTO` legacy (resolver vecchio,
// pre-distinzione listino/override) per fallback grazia.
// Quando il pattern verra' replicato sui 4 sorgenti futuri valutare lo
// spostamento delle chiavi i18n in `common.pricing_origine_*`.
export const PRICING_ORIGINE_LABEL_KEY = {
  PROMO: 'vendite.preventivi.badge_origine_promo',
  CONTRATTO: 'vendite.preventivi.badge_origine_contratto',
  CONTRATTO_LISTINO: 'vendite.preventivi.badge_origine_contratto',
  CONTRATTO_OVERRIDE: 'vendite.preventivi.badge_origine_contratto_override',
  CATEGORIA: 'vendite.preventivi.badge_origine_categoria',
  LISTINO_BUNDLE: 'vendite.preventivi.badge_origine_listino_bundle',
  MANUALE: 'vendite.preventivi.badge_origine_manuale',
}

// Scopo: Ritorna la chiave i18n per il codice origine, o null se sconosciuto.
//        Il chiamante decide il fallback (es. mostrare il codice raw).
export function pricingOrigineLabelKey(codice) {
  return PRICING_ORIGINE_LABEL_KEY[codice] || null
}

// --- Mappa stati contratto (v5) ---
// DRAFT=grigio, ATTIVO=verde, SOSPESO=arancio, CESSATO=rosso
export const STATO_CONTRATTO_MAP = {
  DRAFT: 'secondary',
  ATTIVO: 'success',
  SOSPESO: 'warn',
  CESSATO: 'danger',
}
export function statoContrattoSeverity(codice) {
  return resolveSeverity(STATO_CONTRATTO_MAP, codice)
}

// --- Mappa stati offerta commerciale ---
// BOZZA=grigio, EMESSA=azzurro, ACCETTATA=verde, RIFIUTATA=rosso,
// ANNULLATA=rosso (ritiro da noi), SUPERATA=grigio (revisione N+1 vincente).
export const STATO_OFFERTA_MAP = {
  BOZZA: 'secondary',
  EMESSA: 'info',
  ACCETTATA: 'success',
  RIFIUTATA: 'danger',
  ANNULLATA: 'danger',
  SUPERATA: 'secondary',
}
export function statoOffertaSeverity(codice) {
  return resolveSeverity(STATO_OFFERTA_MAP, codice)
}

// --- Mappa stati ordine di vendita ---
// DRAFT=grigio (bozza), CONFERMATO/EVASO/ALLOCATO/SPEDITO=azzurro (ciclo in corso),
// CONSEGNATO/FATTURATO=verde (concluso), ANNULLATO=rosso.
// EVASO = terminale post-push commessa (transizione automatica CONFERMATO→EVASO
// BE-driven): info perche' la fattura e' ancora a valle (coerente con preventivo).
// Allineato a config.stati_doc_ordini.codice_interno.
export const STATO_ORDINE_MAP = {
  DRAFT: 'secondary',
  CONFERMATO: 'info',
  PARZIALMENTE_EVASO: 'info',
  EVASO: 'info',
  ALLOCATO: 'info',
  SPEDITO: 'info',
  CONSEGNATO: 'success',
  FATTURATO: 'success',
  ANNULLATO: 'danger',
}
export function statoOrdineSeverity(codice) {
  return resolveSeverity(STATO_ORDINE_MAP, codice)
}

// --- Mappa stati DDT di vendita ---
// DRAFT=grigio (bozza, numero non ancora assegnato), EMESSO/SPEDITO=azzurro
// (ciclo logistico in corso), CONSEGNATO=verde (concluso), RESO=arancio
// (reso merce), ANNULLATO=rosso. Allineato a config.stati_doc_ddt.codice_interno.
export const STATO_DDT_MAP = {
  DRAFT: 'secondary',
  EMESSO: 'info',
  SPEDITO: 'info',
  CONSEGNATO: 'success',
  RESO: 'warn',
  ANNULLATO: 'danger',
}
export function statoDdtSeverity(codice) {
  return resolveSeverity(STATO_DDT_MAP, codice)
}

// --- Mappa stati reso (vendite.resi) ---
// DRAFT=grigio (bozza), CONFERMATO=verde (effetti applicati: residuo riaperto,
// eventuale flip DDT), ANNULLATO=rosso. Allineato a
// config.stati_doc_reso.codice_interno.
export const STATO_RESO_MAP = {
  DRAFT: 'secondary',
  CONFERMATO: 'success',
  ANNULLATO: 'danger',
}
export function statoResoSeverity(codice) {
  return resolveSeverity(STATO_RESO_MAP, codice)
}

// --- Mappa stato ri-consegna riga reso (DERIVATO dalla copertura del ponte
// resi_righe_riconsegne, vw_resi_da_riconsegnare / list_righe BE) ---
export const STATO_RICONSEGNA_MAP = {
  DA_RICONSEGNARE: 'warn',
  PARZIALE: 'info',
  COMPLETATA: 'success',
}
export function statoRiconsegnaSeverity(codice) {
  return resolveSeverity(STATO_RICONSEGNA_MAP, codice)
}

// --- Mappa etichetta NC della coda accrediti (vw_resi_da_accreditare, forma
// contatore): DOVUTA = obbligo (a credito, lavoro arretrato), FACOLTATIVA =
// opzione dell'operatore su merce da ri-spedire (DL-26). ---
export const ETICHETTA_ACCREDITO_MAP = {
  DOVUTA: 'warn',
  FACOLTATIVA: 'secondary',
}
export function etichettaAccreditoSeverity(codice) {
  return resolveSeverity(ETICHETTA_ACCREDITO_MAP, codice)
}

// --- Mappa stati commessa ---
// BOZZA=grigio, APERTA/IN_ESECUZIONE/PRONTA_FATTURAZIONE=azzurro (ciclo in corso),
// CHIUSA=verde (concluso), ANNULLATA=rosso.
// Allineato a vendite.stati_commessa.codice_interno.
export const STATO_COMMESSA_MAP = {
  BOZZA: 'secondary',
  APERTA: 'info',
  IN_ESECUZIONE: 'info',
  PRONTA_FATTURAZIONE: 'info',
  CHIUSA: 'success',
  ANNULLATA: 'danger',
}
export function statoCommessaSeverity(codice) {
  return resolveSeverity(STATO_COMMESSA_MAP, codice)
}

// Stati documento fiscale (fatture): DRAFT=grigio (bozza), EMESSA/INVIATA=
// azzurro (in pipeline), REGISTRATA/DEFINITIVA=verde (consolidata),
// ANNULLATA=rosso. Allineato a config.stati_doc_fiscale.codice_interno.
export const STATO_DOC_FISCALE_MAP = {
  DRAFT: 'secondary',
  EMESSA: 'info',
  INVIATA: 'info',
  REGISTRATA: 'success',
  DEFINITIVA: 'success',
  ANNULLATA: 'danger',
}
export function statoDocFiscaleSeverity(codice) {
  return resolveSeverity(STATO_DOC_FISCALE_MAP, codice)
}

// Stati della DISTINTA CONTABILE (`pagamenti.vendite_contabili_stati`):
// BOZZA=grigio (si sta ancora digitando), IMPORTATA=azzurro (arrivata da un
// flusso), VALIDATA=arancio, CHIUSA=verde (registrata), ANNULLATA=rosso.
// ⭐ VALIDATA e' arancio e non azzurro di proposito: e' lo stato in cui la
// distinta ASPETTA il gesto irreversibile — la registrazione — e l'arancio dice
// «c'e' qualcosa da fare qui», che e' esattamente la verita'.
export const STATO_DISTINTA_MAP = {
  BOZZA: 'secondary',
  IMPORTATA: 'info',
  VALIDATA: 'warn',
  CHIUSA: 'success',
  ANNULLATA: 'danger',
}
export function statoDistintaSeverity(codice) {
  return resolveSeverity(STATO_DISTINTA_MAP, codice)
}

// Stati della RIGA contabile (`pagamenti.vendite_contabili_righe_stati`), letti
// per «che cosa deve fare l'operatore»:
// IMPORTATA=grigio (nessuno l'ha ancora presa in mano) · DA_ABBINARE=arancio
// (e' LA coda, chiede lavoro) · ABBINATA=azzurro (pronta, in attesa della
// registrazione) · SOSPESA=rosso (uscita dal flusso, richiede risoluzione:
// e' quella che non va dimenticata) · SCARTATA=grigio (chiusa senza effetto,
// non e' un errore) · POSTATA=verde (registrata).
// ⚠️ IMPORTATA e SCARTATA condividono il grigio, e non competono mai per
// l'attenzione: una sta prima del lavoro, l'altra dopo che e' stato archiviato.
export const STATO_RIGA_CONTABILE_MAP = {
  IMPORTATA: 'secondary',
  DA_ABBINARE: 'warn',
  ABBINATA: 'info',
  SOSPESA: 'danger',
  SCARTATA: 'secondary',
  POSTATA: 'success',
}
export function statoRigaContabileSeverity(codice) {
  return resolveSeverity(STATO_RIGA_CONTABILE_MAP, codice)
}

// Stati di un ATTO DI SISTEMAZIONE (`pagamenti.sistemazioni.stato`):
// BOZZA=arancio (una decisione presa e NON ancora eseguita: e' quella che
// chiede il gesto successivo) · CONFERMATA=verde (il denaro si e' mosso) ·
// ANNULLATA=grigio (scartata, resta a registro con la sua ragione).
// ⚠️ ANNULLATA e' grigia e non rossa: scartare una decisione non e' un guasto,
// e' un esito previsto — colorarla di rosso metterebbe in allarme per una cosa
// che qualcuno ha deciso apposta.
export const STATO_SISTEMAZIONE_MAP = {
  BOZZA: 'warn',
  CONFERMATA: 'success',
  ANNULLATA: 'secondary',
}
export function statoSistemazioneSeverity(codice) {
  return resolveSeverity(STATO_SISTEMAZIONE_MAP, codice)
}

// Classi di azionabilita' backlog fatturazione (Lente 2, DL-6/7):
// RECUPERABILE=arancio (lavoro interno da fare), SOLLECITO_CLIENTE=azzurro
// (attesa esterna), ANOMALIA=rosso (da rivedere). Il FISIOLOGICO non arriva
// mai al FE (escluso a monte dalla vista). Allineato al CHECK di
// config.motivi_fermo.classe.
export const CLASSE_BACKLOG_MAP = {
  RECUPERABILE: 'warn',
  SOLLECITO_CLIENTE: 'info',
  ANOMALIA: 'danger',
}
export function classeBacklogSeverity(codice) {
  return resolveSeverity(CLASSE_BACKLOG_MAP, codice)
}

// Fasi normalizzate della proiezione stato dominio (config.stati_doc_*.fase,
// vocabolario uniforme delle 4 aree documento — Situazione aperta):
// APERTO=grigio (in lavorazione interna), IN_ATTESA=azzurro (palla al
// cliente), IN_CORSO=arancio (avanzato, non concluso), CHIUSO=verde.
export const FASE_DOCUMENTO_MAP = {
  APERTO: 'secondary',
  IN_ATTESA: 'info',
  IN_CORSO: 'warn',
  CHIUSO: 'success',
}
export function faseDocumentoSeverity(codice) {
  return resolveSeverity(FASE_DOCUMENTO_MAP, codice)
}

// Stato di esecuzione del lotto di fatturazione (cockpit Fase B): DRAFT=grigio,
// IN_ESECUZIONE=arancio (step in corso), COMPLETATO=verde, ERRORE=rosso.
// Allineato a vendite.fatturazione_lotti.stato_lotto.
export const STATO_LOTTO_MAP = {
  DRAFT: 'secondary',
  IN_ESECUZIONE: 'warn',
  COMPLETATO: 'success',
  ERRORE: 'danger',
}
export function statoLottoSeverity(codice) {
  return resolveSeverity(STATO_LOTTO_MAP, codice)
}

// Task-run della pipeline lotto (vendite.fatturazione_lotti_task_runs.task_stato):
// IN_ESECUZIONE=arancio, COMPLETATO=verde, ERRORE=rosso, ANNULLATO=grigio.
export const STATO_TASK_RUN_MAP = {
  IN_ESECUZIONE: 'warn',
  COMPLETATO: 'success',
  ERRORE: 'danger',
  ANNULLATO: 'secondary',
}
export function statoTaskRunSeverity(codice) {
  return resolveSeverity(STATO_TASK_RUN_MAP, codice)
}

// Esito di esecuzione dentro un lotto — UNA mappa per DUE livelli:
// `vendite.fatturazione_lotti_fatture.stato_esecuzione` (la fattura prodotta) e
// `vendite.fatturazione_lotti_gruppi.stato_esecuzione` (il documento preso in
// carico, che una fattura può non essere mai diventata).
//
// ⭐ Una sola mappa perché il vocabolario è UNO SOLO, e lo è per decisione: la
// D-2 di `brief-db-esito-gruppo-lotto` tiene i due CHECK identici, «due colonne
// che rispondono alla stessa domanda a due livelli non possono parlare due
// lingue». Due mappe qui sarebbero la seconda sede della stessa cosa.
//
// 🔴 FINO AL 2026-09-06 QUESTA MAPPA PARLAVA UNA LINGUA CHE IL DATABASE NON
// PARLA: diceva `PRONTA` / `ELABORATA` / `ESCLUSA`, mentre il CHECK
// `chk_fatturazione_lf_stato_esecuzione` ammette solo
// `PENDING` / `RUNNING` / `COMPLETED` / `ERRORE`. Effetto: nel drawer del lotto
// un documento `COMPLETED` prendeva il ripiego `secondary` — GRIGIO, cioè
// «bozza» — invece del verde. ⚠️ Nessun errore da nessuna parte: `resolveSeverity`
// ripiega di proposito, e un colore sbagliato non fallisce. Trovato aggiungendo
// il secondo consumatore, che parla lo stesso vocabolario.
//
// ⚠️ `PENDING` è grigio e non azzurro: è «in coda», cioè un lavoro che non è
// ancora cominciato — `RUNNING` è quello in corso.
export const STATO_ESECUZIONE_LOTTO_MAP = {
  PENDING: 'secondary',
  RUNNING: 'info',
  COMPLETED: 'success',
  ERRORE: 'danger',
}
export function statoEsecuzioneLottoSeverity(codice) {
  return resolveSeverity(STATO_ESECUZIONE_LOTTO_MAP, codice)
}

// Natura del documento fiscale (config.nature_doc_fiscale.codice_interno):
// FATTURA | NOTA_CREDITO | NOTA_DEBITO.
// ⚠️ NESSUNA delle tre è `danger`, ed è una scelta: una nota di credito non è
// un errore né un'anomalia — è un documento di segno opposto, previsto dal
// modello. Colorarla di rosso la farebbe cercare fra i problemi in ogni lista
// in cui compare, e il totale negativo che porta con sé sembrerebbe un difetto
// invece che il suo contenuto.
// `secondary` alla fattura (è il caso normale: non deve gridare) e `info` alle
// due rettifiche, che sono ciò che merita di essere notato.
export const NATURA_DOC_MAP = {
  FATTURA: 'secondary',
  NOTA_CREDITO: 'info',
  NOTA_DEBITO: 'info',
}
export function naturaDocSeverity(codice) {
  return resolveSeverity(NATURA_DOC_MAP, codice)
}

// Stato approvazione della riga commessa (vendite.commesse_attivita
// .stato_approvazione): BOZZA=arancio (lavoro da fare), APPROVATA=verde,
// RIFIUTATA=rosso.
export const STATO_APPROVAZIONE_ATTIVITA_MAP = {
  BOZZA: 'warn',
  APPROVATA: 'success',
  RIFIUTATA: 'danger',
}
export function statoApprovazioneAttivitaSeverity(codice) {
  return resolveSeverity(STATO_APPROVAZIONE_ATTIVITA_MAP, codice)
}

// Stato emissione della riga commessa (vendite.commesse_attivita
// .stato_emissione): NON_EMESSA=grigio, EMESSA=azzurro, ANNULLATA=rosso.
export const STATO_EMISSIONE_ATTIVITA_MAP = {
  NON_EMESSA: 'secondary',
  EMESSA: 'info',
  ANNULLATA: 'danger',
}
export function statoEmissioneAttivitaSeverity(codice) {
  return resolveSeverity(STATO_EMISSIONE_ATTIVITA_MAP, codice)
}

// Stato dei job della coda lavori generica (dbops.coda_lavori.stato):
// PENDING=arancio (in attesa), IN_CORSO=azzurro, FATTO=verde, ERRORE=rosso,
// ANNULLATO=grigio. UI gestione code (FE-7, centralizzata qui).
export const STATO_CODA_LAVORI_MAP = {
  PENDING: 'warn',
  IN_CORSO: 'info',
  FATTO: 'success',
  ERRORE: 'danger',
  ANNULLATO: 'secondary',
}
export function statoCodaLavoriSeverity(codice) {
  return resolveSeverity(STATO_CODA_LAVORI_MAP, codice)
}

// Stato delle righe coda stampa (vendite.fatture_stampa_coda.stato):
// stesso vocabolario visivo della coda lavori, senza ANNULLATO (il CHECK DB
// non lo prevede). Unifica la mappa prima inline in FatturazioneEsitiPanel.
export const STATO_CODA_STAMPA_MAP = {
  PENDING: 'warn',
  IN_CORSO: 'info',
  FATTO: 'success',
  ERRORE: 'danger',
}
export function statoCodaStampaSeverity(codice) {
  return resolveSeverity(STATO_CODA_STAMPA_MAP, codice)
}

// Stato del conto della merce — il vocabolario e' UNO e vive a DB
// (`vw_situazione_merce_ordine.stato` e `vw_partite_merce.stato`, brief della
// partita merce generalizzata §9.3). Qui si sceglie solo il colore: il verso
// del saldo il frontend NON lo ri-traduce mai (richiesta BE-2).
//
// ⚠️ Il criterio dei due grigi-non-grigi e' la richiesta FE-1: «tutto regolare»
// deve essere VISIBILMENTE diverso da «non ancora calcolato».
//   PAREGGIATA      verde     il conto torna
//   NON_FATTURABILE grigio    il conto non si applica, ed e' normale
//                             (causale di trasporto non fatturabile)
//   NON_MISURABILE  ROSSO     il conto non si PUO' calcolare: kit senza
//                             coefficiente, oppure uno scope che nasconde la
//                             commessa. Non e' uno zero ed e' un difetto da
//                             guardare — grigio lo confonderebbe col caso
//                             sopra, che invece e' sano.
export const STATO_MERCE_MAP = {
  PAREGGIATA: 'success',
  // Ordine ancora sotto la soglia CONFERMATO (o abortito): non c'e' impegno,
  // quindi non c'e' arretrato — `da_spedire` e' NULL, non 0 (20260818-06).
  // Grigio come NON_FATTURABILE: sono entrambi «non si applica», sani.
  NON_IMPEGNATA: 'secondary',
  DA_FATTURARE: 'info',
  DA_ACCREDITARE: 'warn',
  NON_SPEDITA: 'secondary',
  NON_FATTURABILE: 'secondary',
  NON_MISURABILE: 'danger',
  RICONSEGNA: 'info',
}
export function statoMerceSeverity(codice) {
  return resolveSeverity(STATO_MERCE_MAP, codice)
}

// --- Motivi «fondo fattura da decidere» (vw_fondi_fattura_da_decidere, D-10:
// vocabolario CHIUSO per costruzione — quattro letterali nei rami della UNION,
// nessun dato li produce). ---
//
// ⚠️ Il colore separa DUE COSE DIVERSE, e non e' una gradazione di urgenza:
//   PROPOSTA_SENZA_ATTO      arancio  c'e' una decisione DA PRENDERE su un
//                                     caso sano (il fondo ci vuole e non c'e')
//   NON_PIU_CAPIENTE         arancio  idem: l'atto esiste, la sorgente non lo
//                                     regge piu' e va deciso cosa farne
//   IMPORTO_NON_CORRISPONDENTE rosso  il dato NON TORNA (segno diverso dal
//                                     documento o residuo piu' grande): non e'
//                                     una scelta, e' qualcosa da capire
//   UTILITY_NON_ATTRIBUIBILE   rosso  la riga e' IRRAGGIUNGIBILE da qualunque
//                                     giro (utility nulla, e il filtro e' `=`):
//                                     nessuna decisione la sblocca, va corretta
// Chi guarda l'elenco deve poter separare a colpo d'occhio «devo scegliere» da
// «qui c'e' qualcosa di rotto»: sono due lavori diversi, spesso di due persone
// diverse.
export const MOTIVO_FONDO_DA_DECIDERE_MAP = {
  PROPOSTA_SENZA_ATTO: 'warn',
  NON_PIU_CAPIENTE: 'warn',
  IMPORTO_NON_CORRISPONDENTE: 'danger',
  UTILITY_NON_ATTRIBUIBILE: 'danger',
}
export function motivoFondoDaDecidereSeverity(codice) {
  return resolveSeverity(MOTIVO_FONDO_DA_DECIDERE_MAP, codice)
}

// Scopo: colore della gravità di una riga di giornale (`script.vw_giornale_entita`).
// ⭐ Il vocabolario è quello NORMALIZZATO dalla vista — INFO | WARN | ERROR —
//    non quello dei singoli registri (`C`/`W`/`I` dei log, `task_stato` dei
//    task run): la vista li mappa una volta sola, e qui si legge il risultato.
// ⚠️ `null` NON è un caso da appiattire su «neutro e via»: la vista dichiara che
//    una gravità nulla significa «un vincolo si è allargato e la mappa è rimasta
//    indietro». Si rende visibile (secondary + trattino dal chiamante), non si
//    nasconde.
export const GRAVITA_GIORNALE_MAP = {
  ERROR: 'danger',
  WARN: 'warn',
  INFO: 'info',
}

export function gravitaGiornaleSeverity(gravita) {
  return resolveSeverity(GRAVITA_GIORNALE_MAP, gravita)
}

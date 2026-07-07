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
  PROMO: 'preventivi.badge_origine_promo',
  CONTRATTO: 'preventivi.badge_origine_contratto',
  CONTRATTO_LISTINO: 'preventivi.badge_origine_contratto',
  CONTRATTO_OVERRIDE: 'preventivi.badge_origine_contratto_override',
  CATEGORIA: 'preventivi.badge_origine_categoria',
  LISTINO_BUNDLE: 'preventivi.badge_origine_listino_bundle',
  MANUALE: 'preventivi.badge_origine_manuale',
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

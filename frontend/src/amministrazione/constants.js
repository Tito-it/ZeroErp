// Scopo: costanti e helper del modulo Amm. Software.
// Enum: re-export da core/constants (fonte unica di verita').
// Builder opzioni per Select centralizzati (zero duplicazione).

// Re-export enum da core — usati anche da stores/auth.js e test.
export { LIVELLO_ACCESSO } from '../core/constants'
import { LIVELLO_ACCESSO } from '../core/constants'

// --- Tipo ruolo per SoggettoResolver ---
export const TIPO_RUOLO_CODICE = {
  RIS_UMANA: 'RIS_UMANA'
}

// Scopo: Opzioni filtro SUPER_ADMIN per toolbar lista operatori.
// Valori tri-state: null = tutti, true = solo SUPER_ADMIN, false = escludi.
// Il BE accetta il param is_super_admin come bool opzionale.
export function buildFilterSuperAdminOptions(t) {
  return [
    { label: t('amministrazione.filter_super_admin_tutti'), value: null },
    { label: t('amministrazione.filter_super_admin_si'), value: true },
    { label: t('amministrazione.filter_super_admin_no'), value: false }
  ]
}

// Scopo: Opzioni filtro stato operatore per toolbar. Tri-state
// null/true/false mappato direttamente su is_active del BE.
export function buildFilterStatoOptions(t) {
  return [
    { label: t('amministrazione.stato_all'), value: null },
    { label: t('amministrazione.stato_attivo'), value: true },
    { label: t('amministrazione.stato_inattivo'), value: false }
  ]
}

// Scopo: Costruisce le opzioni livello accesso per Select.
export function buildLivelloOptions(t) {
  return [
    { label: t('amministrazione.livello_tutto'), value: LIVELLO_ACCESSO.TUTTO },
    { label: t('amministrazione.livello_lettura'), value: LIVELLO_ACCESSO.LETTURA },
    { label: t('amministrazione.livello_bloccato'), value: LIVELLO_ACCESSO.BLOCCATO }
  ]
}

// Fase 5 (LANDED): le opzioni filtro audit-log arrivano dal lookup BE
// /amm-software/lookup/audit-sources/ (vw_audit_sources, single source DB).
// Vedi AuditLogView.vue: usa useGlobalLookup('amm.audit_sources') con
// label tradotta via t(label_key). Il vecchio buildAuditTabellaOptions e' stato
// rimosso (era hardcoded e mancava override_oggetti + identita_digitali).

// --- Arrotondamento importi ---
// Fase 3 (LANDED): l'enum dei modi di arrotondamento e' gestito dal lookup
// statico /amm-software/lookup/rounding-modes/ via wrapper riusabile
// EmittenteRoundingModeSelect. Single source of truth lato BE in
// amm_software_service._ROUNDING_MODE_VALIDI_EMITTENTE.
// Range decimali tecnico, allineato al CHECK constraint DB
// (chk_emittenti_fiscali_utilities_arrotondamento_dec).
export const ROUNDING_DECIMALI_RANGE = { MIN: 0, MAX: 6 }

// --- Email log stati ---
// Fase 5 (LANDED): l'enum + le opzioni filtro arrivano dal lookup BE
// /amm-software/lookup/email-log-stati/. Vedi EmailLogStatoSelect.vue
// (wrapper riusabile cached con useGlobalLookup('amm.email_log_stati')).
// Single source of truth lato BE: amm_software_service._EMAIL_LOG_STATI_VALIDI.
//
// `getEmailLogStatoSeverity` resta lato FE (puro mapping CSS, presentation).
// ⛔ IL RIPIEGO SU 'info' NON E' UNA RETE, ed e' costato una riga di lavoro nel
//    2026-09-11: 'info' e' anche la severity di PENDING, quindi uno stato nuovo
//    non «cade su un default neutro» — esce IDENTICO a «in lavorazione».
//    Su `SIMULATA` sarebbe stato il colmo: il valore nasce apposta per non dire
//    «consegnata», e a video avrebbe detto «in corso».
// ⇒ Ogni stato TERMINALE vuole il suo ramo. Il ripiego resta per non rompersi
//    su un codice ignoto, ma va letto per quello che e': l'ultima spiaggia.

// Scopo: Restituisce la severity PrimeVue per uno stato email log (puro CSS).
export function getEmailLogStatoSeverity(stato) {
  if (stato === 'SENT') return 'success'
  if (stato === 'FAILED') return 'danger'
  if (stato === 'RETRY') return 'warn'
  // ⭐ SIMULATA: stampata a video, non spedita. Terminale e VOLUTA — quindi non
  //    rossa (non e' un guasto) e non verde (non e' arrivata a nessuno).
  //    Grigia, come la convenzione del progetto vuole per cio' che e' inerte.
  if (stato === 'SIMULATA') return 'secondary'
  return 'info' // PENDING o codice non riconosciuto
}

// --- Severity mapping riusabili ---

// Scopo: Restituisce la severity PrimeVue per un livello accesso.
export function getLivelloSeverity(livello) {
  if (livello === LIVELLO_ACCESSO.TUTTO) return 'success'
  if (livello === LIVELLO_ACCESSO.LETTURA) return 'warn'
  return 'danger'
}

// Scopo: Restituisce la label i18n per un livello accesso.
export function getLivelloLabel(t, livello) {
  if (livello === LIVELLO_ACCESSO.TUTTO) return t('amministrazione.livello_tutto')
  if (livello === LIVELLO_ACCESSO.LETTURA) return t('amministrazione.livello_lettura')
  return t('amministrazione.livello_bloccato')
}

// Scopo: Restituisce la severity PrimeVue per un tipo operazione audit.
export function getAuditOpSeverity(tipo) {
  if (tipo === 'INIZIALE') return 'info'
  if (tipo === 'MODIFICA') return 'warn'
  if (tipo === 'ELIMINAZIONE') return 'danger'
  return 'secondary'
}

// ------------------------------------------------------------
// Registri di numerazione — i vocabolari CHIUSI che il frontend deve conoscere
// ------------------------------------------------------------
// ⛔ Stanno qui e non in un catalogo perche' NON hanno un catalogo: sono
//    `CHECK` del database, verificati sul vivo il 2026-09-01. Una tabella da
//    cui leggerli non esiste, quindi l'unica alternativa a queste costanti
//    sarebbe la stessa stringa scritta a mano in tre punti della maschera.
// ⚠️ Se un giorno un CHECK si allarga, questo file va allargato con lui: e' un
//    elenco parallelo dichiarato, e la sua unica difesa e' stare in UN posto.

// La famiglia che ammette i campi fiscali. Le altre quattro li vedono
// ⛔ QUI C'ERA `REGISTRO_FAMIGLIA_FISCALE = 'FATTURA'`, ED È STATO TOLTO IL
//    2026-09-02 (§11.10 FE-F2). Era il gemello di un letterale identico nel
//    backend, e diceva col nome di UNA riga una proprietà che è una COLONNA:
//    `famiglie_documento.presidia_data_documento`, che il drawer dei registri
//    riceve col lookup delle famiglie. Due copie della stessa affermazione, in
//    due linguaggi, che nessun presidio teneva allineate.

// `chk_registri_fatturazione_politica_data`: due valori, non di piu'.
// ⭐ `OGGI` e' anche il NEUTRO che il CHECK pretende fuori da FATTURA.
export const REGISTRO_POLITICA_DATA = ['OGGI', 'FINE_MESE_COMPETENZA']
export const REGISTRO_POLITICA_DATA_NEUTRA = 'OGGI'

// `chk_registri_fatturazione_reset`: due valori, e sono quelli che il CHECK
// ammette dal changeSet `20260901-06` — prima ce n'era uno solo.
// ⛔ `MENSILE` NON c'e' e non torna: nessun documento porta il mese, quindi un
//    contatore che discriminasse per mese consegnerebbe numeri che il documento
//    non e' in grado di ospitare (brief chiave-del-contatore §6).
// ⭐ `NESSUNA` invece e' sicura per l'asimmetria del §1: usa MENO assi, non di
//    piu'. Vuol dire numerazione continua fra gli anni, che i gestionali fanno
//    davvero su DDT e ordini.
// ⚠️ Si sceglie SOLO alla nascita del registro: e' un asse della chiave del
//    contatore, e cambiarla dopo il primo numero sposta il secchio.
export const REGISTRO_RESET_POLICY = ['ANNUALE', 'NESSUNA']
export const REGISTRO_RESET_POLICY_DEFAULT = 'ANNUALE'

// Limiti della UI per `lunghezza_numero`.
// ⚠️ NON sono un vincolo del database — la colonna non ha `CHECK` — sono un
//    guard di maschera: il progressivo e' un `bigint`, quindi oltre 18 cifre
//    il contatore non ci starebbe comunque, e sotto 1 non esiste un numero.
//    Dichiarati qui perche' servono in DUE punti (il campo e l'anteprima) e
//    due letterali che devono restare uguali sono un letterale di troppo.
export const REGISTRO_CIFRE_MIN = 1
export const REGISTRO_CIFRE_MAX = 18

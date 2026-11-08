// Scopo: costanti e helper del modulo Amm. Software.
// Enum: re-export da core/constants (fonte unica di verita').
// Builder opzioni per Select centralizzati (zero duplicazione).

// Re-export enum da core — usati anche da stores/auth.js e test.
export { LIVELLO_ACCESSO } from '../core/constants'
import { LIVELLO_ACCESSO } from '../core/constants'

// ⛔ Il tipo ruolo per il SoggettoResolver non sta qui: e' `TIPO_RUOLO` di
//    `core/constants` (fino al 2026-11-04 c'era una copia, `TIPO_RUOLO_CODICE`).

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

// ⛔ `buildFilterStatoOptions` E' STATA RITIRATA il 2026-09-23 (regola del 2,
//    ok Tid): era la terna «tutti / attivo / non attivo» — la stessa che
//    `EmittentiFiscaliListView`, `FamiglieDocumentoListView`,
//    `ListiniSearchTable` e `ArticoliSearchTable` si scrivevano a mano — con le
//    chiavi di questo dominio invece di quelle di `common`. Adesso la sede e'
//    una: `core/utils/options.js` → `buildAttivoOptions(t)`, accanto al gemello
//    `buildBoolOptions` che la stessa terna la produce con `Sì`/`No`.
// ⭐ Non e' stata lasciata come alias: *quando emerge un BB generico i duplicati
//    si ritirano subito* — un alias e' una seconda sede che aspetta solo di
//    divergere.
// ⚠️ `buildFilterSuperAdminOptions` qui sopra RESTA: e' tri-state uguale nella
//    forma, ma le sue etichette sono una domanda di dominio («solo SUPER_ADMIN
//    / escludili»), non lo stato `attivo` del modello.

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
// Range dei decimali degli importi di una utility: lo specchio del CHECK
// `chk_emittenti_fiscali_utilities_arrotondamento_dec` (0..2, come
// `chk_utilities_arrotondamento_importi_dec` sulla tabella madre).
// 🔴 Fino al 2026-10-31 qui c'era MAX 6 col commento «allineato al CHECK»: il
//    campo accettava 4, il Salva si accendeva e il database rifiutava la riga
//    (segnalazione di Tid). Il 6 e' l'intervallo di ALTRI vincoli (termini di
//    pagamento, regole di fatturazione dell'articolo), non di questo.
// ⚠️ Resta una copia del vincolo: il giorno che il CHECK cambia, questa no.
//    Il rifiuto del DB esce comunque parlante e col campo (`_UTILITY_CHECK_
//    CONSTRAINTS` lato BE), ma la sede giusta del numero e' il database.
export const ROUNDING_DECIMALI_RANGE = { MIN: 0, MAX: 2 }

// --- Email log stati ---
// ⭐ Dal 2026-09-26 in `core`: il select (`core/components/EmailLogStatoSelect`,
// lookup /core/email/log/stati/) e il colore (`core/utils/severity.js`,
// `statoEmailLogSeverity`). Li usano il log dell'admin e quello dell'operatore.

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

// Le tre schede dell'area «Accessi» (brief-db-be-fe-area-accessi, A-1/A-2):
// una PARTIZIONE delle credenziali — ognuna sta in una scheda sola, decisa dal
// DB (`script.fn_categoria_accesso`). Il valore e' quello del `?tab=` del
// link: stringhe stabili, mai indici (frontend-standards §«Pattern Tab-View»).
export const ACCESSI_TABS = Object.freeze({
  OPERATORI: 'operatori',
  ALTRI: 'altri',
  SISTEMA: 'sistema',
})

// Il TIPO di una credenziale di sistema (`vw_accessi_sistema.tipo`).
export const TIPO_ACCESSO_SISTEMA = Object.freeze({
  PROCESSO: 'PROCESSO',
  API_CLIENT: 'API_CLIENT',
})

// Client API per il modulo Amm. Software.
// Usa l'istanza axios condivisa con interceptor JWT.

import api from '../../core/api'

const BASE = '/amm-software'

// --- Operatori ---

export function listOperatori(params = {}) {
  return api.get(`${BASE}/operatori/`, { params })
}

export function getOperatore(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/`)
}

export function createOperatore(payload) {
  return api.post(`${BASE}/operatori/`, payload)
}

// La credenziale che porta un'email, con username e vesti: i dati del dialog
// di conferma del riuso (B-20). `data.credenziale` null = nessuna credenziale.
export function getCredenzialePerEmail(email) {
  return api.get(`${BASE}/operatori/credenziale-per-email/`, { params: { email } })
}

export function updateOperatore(authUserId, payload) {
  return api.patch(`${BASE}/operatori/${authUserId}/`, payload)
}

export function disabilitaOperatore(authUserId) {
  return api.post(`${BASE}/operatori/${authUserId}/disabilita/`)
}

// ⛔ Niente `riattivaOperatore` (ritirato il 2026-10-04, D-3): un operatore
//    spento si riattiva col reinvio dell'invito (`reinviaInvito`).

// --- Area «Accessi» (brief-db-be-fe-area-accessi) ---
// I due tab accanto agli operatori: insieme censiscono TUTTE le credenziali,
// ognuna in un tab solo (la categoria la decide il DB).

// Scopo: le persone senza veste operatore (portale, shop, nessuna veste).
export function listAccessiAltri(params = {}) {
  return api.get(`${BASE}/accessi/altri/`, { params })
}

// Scopo: le credenziali delle macchine (utenti tecnici dei processi, API_CLIENT).
export function listAccessiSistema(params = {}) {
  return api.get(`${BASE}/accessi/sistema/`, { params })
}

// --- La CREDENZIALE: azioni che valgono per tutte le sue vesti (A-4, A-5) ---
// ⛔ Non stanno sotto `/operatori/`: una persona senza veste operatore non si
//    raggiunge da li'. Fino al 2026-10-02 il secondo fattore stava sotto
//    `operatori/<id>/secondo-fattore/`: ritirato.

// Scopo: lo stato della credenziale (blocco dell'amministratore, capability).
export function getCredenziale(authUserId) {
  return api.get(`${BASE}/credenziali/${authUserId}/`)
}

// Scopo: blocca la credenziale su tutte le porte e chiude le sue sessioni.
export function bloccaCredenziale(authUserId, motivo) {
  return api.post(
    `${BASE}/credenziali/${authUserId}/blocca/`,
    { motivo },
  )
}

// Scopo: elimina una credenziale che non ha mai avuto una veste.
// ⚠️ Il gesto e' irreversibile, ma la key che l'interceptor mette da solo e'
//    una per CHIAMATA: il doppio invio risponde come il primo solo se il
//    chiamante passa in `config` la key del GESTO (`useChiaveGesto`), come fa
//    `useEliminaCredenziale`.
export function eliminaCredenziale(authUserId, config = {}) {
  return api.delete(
    `${BASE}/credenziali/${authUserId}/`,
    config,
  )
}

// Scopo: toglie il blocco dell'amministratore.
export function sbloccaCredenziale(authUserId) {
  return api.post(
    `${BASE}/credenziali/${authUserId}/sblocca/`,
    {},
  )
}

// Scopo: lo stato del secondo fattore della credenziale, e se l'obbligo viene
//        dalla credenziale o da un profilo (brief sicurezza §3.4-bis, T-4).
export function getSecondoFattoreCredenziale(authUserId) {
  return api.get(`${BASE}/credenziali/${authUserId}/secondo-fattore/`)
}

// Scopo: accende o spegne l'obbligo sulla CREDENZIALE.
export function impostaObbligoSecondoFattore(authUserId, valore) {
  return api.post(`${BASE}/credenziali/${authUserId}/secondo-fattore/obbligo/`, { valore })
}

// Scopo: cancella il device della credenziale (telefono perso), col motivo.
export function disattivaSecondoFattoreCredenziale(authUserId, motivo) {
  return api.post(`${BASE}/credenziali/${authUserId}/secondo-fattore/disattiva/`, { motivo })
}

// --- Invito operatore ---

export function invitaOperatore(authUserId) {
  return api.post(`${BASE}/operatori/${authUserId}/invita/`)
}

export function reinviaInvito(authUserId) {
  return api.post(`${BASE}/operatori/${authUserId}/reinvia-invito/`)
}

// --- Override permessi operatore ---

export function getOverrideAree(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/override-aree/`)
}

export function putOverrideAree(authUserId, items) {
  return api.put(`${BASE}/operatori/${authUserId}/override-aree/`, { items })
}

export function getOverrideAzioni(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/override-azioni/`)
}

export function putOverrideAzioni(authUserId, items) {
  return api.put(`${BASE}/operatori/${authUserId}/override-azioni/`, { items })
}

export function getOverrideOggetti(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/override-oggetti/`)
}

export function putOverrideOggetti(authUserId, items) {
  return api.put(`${BASE}/operatori/${authUserId}/override-oggetti/`, { items })
}

export function getModelOverridesLookup() {
  return api.get(`${BASE}/lookup/model-overrides/`)
}

// Fase 2 multi-face: shape `{scope_mode, emittenti_ids, allowed_scope_modes,
// can_change_scope, change_scope_reason, emittente_descrizione}`. La GET
// e' coerente con la PUT: stesso shape in input e output.
export function getEmittentiScope(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/emittenti-scope/`)
}

// payload: { scope_mode: 'GLOBAL'|'SINGLE', emittenti_ids?: number[] }
export function putEmittentiScope(authUserId, payload) {
  return api.put(`${BASE}/operatori/${authUserId}/emittenti-scope/`, payload)
}

// --- Riepilogo permessi ---

// Scopo: il riepilogo PER AREA degli operatori indicati — una riga per
//        (operatore, area attiva) con `livello`, `override_count`,
//        `voci_limitate` (`script.fn_get_permessi_riepilogo_aree`). Si chiede
//        per gli id di una PAGINA della lista operatori, o per uno solo (il
//        pannello permessi).
export function getPermessiRiepilogo(authUserIds) {
  return api.get(`${BASE}/permessi-riepilogo/`, { params: { auth_user_ids: authUserIds.join(',') } })
}

// --- Processi automatici (registro + presidi + utenti tecnici) ---

// Scopo: elenco paginato del registro dei processi automatici.
export function listProcessi(params = {}) {
  return api.get(`${BASE}/processi/`, { params })
}

// Scopo: stato dei presidi in un round-trip (conteggi + prime righe).
//        ⚠️ QUANTI siano lo dice il catalogo `dbops.presidi`, non questa riga:
//        fino al 2026-09-18 diceva «sei» ed erano gia' di piu'.
export function getProcessiPresidi() {
  return api.get(`${BASE}/processi/presidi/`)
}


// Scopo: i vocabolari dei filtri del pannello processi `{ classi, canali }`.
//        ⛔ Le tendine li leggono da qui, non da una copia: quella che c'era
//        non aveva `CODA_AUTOMATICA` (2026-11-09).
export function getProcessiVocabolari() {
  return api.get(`${BASE}/processi/vocabolari/`)
}

// Scopo: dettaglio di un processo (bersagli dichiarati + identità tecniche).
export function getProcesso(codice) {
  return api.get(`${BASE}/processi/${encodeURIComponent(codice)}/`)
}

// Scopo: corse recenti di un processo (`maintenance.job_run_log`).
export function listProcessoRun(codice, params = {}) {
  return api.get(`${BASE}/processi/${encodeURIComponent(codice)}/run/`, { params })
}

// Scopo: un verbo sull'utente tecnico di un processo PER UN'AZIENDA. I due verbi
//        pubblici (crea, riattiva) differiscono solo per il segmento finale
//        dell'URL: corpo e header sono gli stessi, e stanno qui una volta sola.
// ⛔ L'azienda si passa, non si deduce: il sistema non concede perimetri da solo
//    (D-9) — il pannello mostra chi non è servito, la decisione resta di chi
//    guarda.
// ⚠️ Gli endpoint dichiarano `require_idempotency_key`: senza header 400.
function postIdentita(codice, azione, emittenteCodice) {
  return api.post(
    `${BASE}/processi/${encodeURIComponent(codice)}/identita/${azione}`,
    { emittente_codice: emittenteCodice },
  )
}

// Scopo: crea l'utente tecnico di un processo per un'azienda.
export function creaUtenteTecnico(codice, emittenteCodice) {
  return postIdentita(codice, '', emittenteCodice)
}

// Scopo: riaccende l'utente tecnico SPENTO di un processo per un'azienda.
// ⭐ Verbo SEPARATO, non un flag su `creaUtenteTecnico`: «non c'è» e «c'è ed è
//    spento» sono due stati del mondo diversi, e un solo endpoint che sceglie da
//    sé quale dei due fare non direbbe a chi lo chiama che cosa è successo.
// ⚠️ Ci si arriva da un rifiuto: la fabbrica risponde
//    `E_UTENTE_TECNICO_DA_RIATTIVARE` e manda qui.
export function riattivaUtenteTecnico(codice, emittenteCodice) {
  return postIdentita(codice, 'riattiva/', emittenteCodice)
}

// Scopo: «Esegui ora» su una SVEGLIA di deploy di un processo. Il web non
//        esegue niente: ACCODA un lavoro `ESEGUI_PROCESSO` con l'identità di
//        chi preme, e il drenatore lancia il comando alla corsa successiva
//        (piano-be-fe-avvio-manuale-di-un-processo.md §1).
// ⛔ Si manda la UNIT, mai un comando: l'argv lo risolve il backend dal
//    dichiarato di deploy (`sveglie.json`), che è la whitelist. Un client che
//    potesse dire «lancia questo» sarebbe una shell remota con un altro nome.
// ⚠️ `require_idempotency_key`: senza header 400. Questa è la chiave HTTP del
//    doppio submit; quella di BUSINESS («una per unit sui lavori vivi») la
//    mette il backend, ed è quella che fa dire «già in coda» alla capability.
// Risposta: `{job_id, stato: 'PENDING', unit}` — la forma del giro di
// fatturazione. ⚠️ A tipo di coda spento risponde 501 `E_JOB_TYPE_NON_ATTIVO`:
// è il cancello voluto finché l'handler non è in servizio, e il toast lo dice.
export function eseguiOraProcesso(codice, unit) {
  return api.post(
    `${BASE}/processi/${encodeURIComponent(codice)}/esegui-ora/`,
    { unit },
  )
}

// Scopo: la SCELTA A MANO sull'accensione di un processo, su questa
//        installazione: `acceso` true accende, false spegne, null toglie la
//        scelta e torna il default per ambiente. Il motivo è obbligatorio per
//        tutti e tre i gesti (brief-db-processi-accensione-per-ambiente §6.0
//        punto 5).
// Risposta: l'accensione rinfrescata, nella forma di `accensione` del
// dettaglio. ⚠️ `require_idempotency_key`: senza header 400.
export function impostaAccensioneProcesso(codice, acceso, motivo) {
  return api.post(
    `${BASE}/processi/${encodeURIComponent(codice)}/accensione/`,
    { acceso, motivo },
  )
}

export function getAuditLog(params = {}) {
  return api.get(`${BASE}/audit-log/`, { params })
}

// --- Registro degli errori tecnici (`dbops.error_log`, pezzo E) ---

// Scopo: la consultazione paginata di `dbops.error_log` col catalogo dei
//        messaggi (codice, classe, frase, causa, soluzione) e il `context`.
export function listErrorLogs(params = {}) {
  return api.get(`${BASE}/error-log/`, { params })
}

// Scopo: export CSV/Excel della consultazione, stessi filtri della lista.
// ⚠️ `formato` e non `format` (parametro magico di DRF); risposta Blob, senza
//    `useApiHandler` (`feedback_blob_download_no_useapihandler`).
export function exportErrorLogs(params = {}) {
  return api.get(`${BASE}/error-log/export/`, { params, responseType: 'blob' })
}

// --- Reparti e profili ---

// Scopo: la lista paginata dei reparti (`amm.reparti`): `params` porta ricerca,
//        ordinamento e pagina.
export function listReparti(params = {}) {
  return api.get(`${BASE}/reparti/`, { params })
}

export function getProfiloReparto(uoId) {
  return api.get(`${BASE}/reparti/${uoId}/profilo/`)
}

// `richiedeSecondoFattore`: il segno del profilo (chi lo riceve deve usare il
// secondo fattore). `undefined` = non si manda, e il backend lo lascia com'e'.
export function putProfiloReparto(uoId, aree, azioni, richiedeSecondoFattore) {
  const corpo = { aree, azioni }
  if (richiedeSecondoFattore !== undefined) corpo.richiede_secondo_fattore = richiedeSecondoFattore
  return api.put(`${BASE}/reparti/${uoId}/profilo/`, corpo)
}

// --- Email Accounts ---

export function listEmailAccounts(params = {}) {
  return api.get(`${BASE}/email-accounts/`, { params })
}

export function getEmailAccount(id) {
  return api.get(`${BASE}/email-accounts/${id}/`)
}

export function createEmailAccount(payload) {
  return api.post(`${BASE}/email-accounts/`, payload)
}

export function updateEmailAccount(id, payload) {
  return api.patch(`${BASE}/email-accounts/${id}/`, payload)
}

export function testEmailAccount(id) {
  return api.post(`${BASE}/email-accounts/${id}/test/`)
}

// --- Email Templates ---

export function listEmailTemplates(params = {}) {
  return api.get(`${BASE}/email-templates/`, { params })
}

export function getEmailTemplate(id) {
  return api.get(`${BASE}/email-templates/${id}/`)
}

export function updateEmailTemplate(id, payload) {
  return api.patch(`${BASE}/email-templates/${id}/`, payload)
}

export function previewEmailTemplate(id, variabili) {
  return api.post(`${BASE}/email-templates/${id}/preview/`, { variabili })
}

// --- Email Log ---

export function listEmailLogs(params = {}) {
  return api.get(`${BASE}/email-log/`, { params })
}

export function getEmailLog(id) {
  return api.get(`${BASE}/email-log/${id}/`)
}

// --- Lookup ---

export function listUnitaOrganizzative() {
  return api.get(`${BASE}/lookup/unita-organizzative/`)
}

// Livelli EREDITATI dal profilo: cosa l'operatore avrebbe senza override.
// ⛔ Non e' `reparti/<uo_id>/profilo/`, che legge il solo binding REPARTO: i
//    bindings sono tre (AD_HOC prio 1, REPARTO prio 2, PORTALE di veste prio 3)
//    e i resolver prendono il primo per priorita'. Alimenta la colonna «ereditato».
// ℹ️ Nessuna chiave `oggetti`: per un model l'ereditato e' il livello della sua
//    AREA, che sta gia' in `aree`.
export function getPermessiEreditati(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/permessi-ereditati/`)
}

// Permessi EFFETTIVI su azioni e oggetti, col tetto d'area gia' applicato a DB
// (brief-db-permessi-tetto-area): per ogni voce il valore senza tetto, quello
// applicato e `limitata_da_area` / `limitato_da_area`. Alimenta l'etichetta
// «limitata dall'area» del pannello. ⛔ Il tetto non si ricalcola nel FE.
export function getPermessiEffettivi(authUserId) {
  return api.get(`${BASE}/operatori/${authUserId}/permessi-effettivi/`)
}

export function listAreeFunzionali() {
  return api.get(`${BASE}/lookup/aree-funzionali/`)
}

export function listAzioniProcesso() {
  return api.get(`${BASE}/lookup/azioni-processo/`)
}


// --- Setup status (refactor operatore-emittenti) ---

// Stato setup refactor: contatori EF/operatori per banner UI.
// Restituisce { emittenti_attivi, operatori_totali, operatori_assegnati,
// operatori_admin_globali, operatori_non_assegnati }.
export function getSetupStatus() {
  return api.get(`${BASE}/setup-status/`)
}

// --- Form-defaults emittente fiscale (Fase 3) ---

// Defaults pre-compilazione form anagrafica emittente fiscale.
// Cast tipi gia' applicato lato BE: bollo_auto bool, bollo_soglia
// Decimal|null, rounding_policy str|null. Il FE non duplica il cast
// generico di /core/parameters/defaults/.
// Restituisce { defaults: { bollo_auto, bollo_soglia, rounding_policy },
//               non_editable_fields: [...] }.
export function getEmittenteFormDefaults() {
  return api.get(`${BASE}/emittenti-fiscali/form-defaults/`)
}

// Lookup statico modi di arrotondamento ammessi per emittente fiscale
// (4 codici fissi: UP/DOWN/HALF_UP/HALF_DOWN, niente HALF_EVEN).
// Single source of truth lato BE in
// amm_software_service._ROUNDING_MODE_VALIDI_EMITTENTE.
// Restituisce lista nuda di { codice, descrizione, ordering }.
export function lookupEmittenteRoundingModes() {
  return api.get(`${BASE}/lookup/rounding-modes/`)
}

// --- Audit hardening + email log lookup (Fase 5) ---

// Lookup sorgenti audit ammesse (8 righe). Single source of truth lato DB:
// script.vw_audit_sources. Sostituisce buildAuditTabellaOptions hardcoded.
// Restituisce lista nuda di { code, label_key, area_funzionale }.
export function lookupAuditSources() {
  return api.get(`${BASE}/lookup/audit-sources/`)
}


// Client API lotti di fatturazione — registro dei giri (cockpit Fase B).
// Doc BE: api_lotti (lista+dettaglio), api_lotto_fatture_list, pipeline.
// La lista/dettaglio sono read; le azioni (avanza step, rerun, reset) sono
// write con Idempotency-Key. Nessuna logica: la macchina step/gate vive nel
// motore DB/BE, il drawer diagnostico rende ed esercita.
import api from '../../core/api'
import { generateIdempotencyKey } from '../../core/utils/idempotency'

const BASE = '/vendite/lotti'

// GET lista lotti paginata (filtri competenza/stato/tipo_doc/emittente/utility).
export function listLotti(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// Export CSV/XLSX della lista configurabile `vendite.lotti`: stessi filtri e
// stesso ordinamento della lista a video, colonne dal catalogo (nascoste
// escluse, permessi rispettati). `responseType: 'blob'` e NON passare da
// useApiHandler, che unwrappando l'envelope perderebbe header e binario
// (memoria feedback_blob_download_no_useapihandler).
export function exportLotti(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}

// GET conteggi lotti/mese di un anno (badge sidebar anno/mese). Fotografia
// completa (nessun filtro stato): { anno, mesi: [{competenza_mese, n_lotti}] }.
export function listLottiMensile(anno) {
  return api.get(`${BASE}/mensile/`, { params: { anno } })
}

// GET dettaglio testata lotto (B-1). 404 su lotto fuori scope/inesistente.
export function getLotto(lottoId) {
  return api.get(`${BASE}/${lottoId}/`)
}

// GET fatture del lotto (stato esecuzione, ordinamento, paginazione). Il
// filtro `esclusa` non esiste piu': la colonna e' stata droppata dal DB il
// 2026-08-04 (slice 6-B) perche' nessuno la valorizzava — ogni predicato che
// la nominava era una condizione sempre vera.
export function listLottoFatture(lottoId, params = {}) {
  return api.get(`${BASE}/${lottoId}/fatture/`, { params })
}

// GET task-run runtime del lotto (tentativi/esiti per step).
export function listLottoTaskRuns(lottoId, { limit = 100 } = {}) {
  return api.get(`${BASE}/${lottoId}/task-runs/`, { params: { limit } })
}

// GET segnalazioni del lotto: conteggi (critical/warning/attention + blocco
// step) **e** l'elenco del livello richiesto, in una risposta sola.
//
// `livello`: 'C' critiche · 'W' avvisi · 'I' attenzioni. Assente = 'C', che è
// la domanda con cui si arriva alla scheda (sono le critiche a fermare il lotto).
//
// ⚠️ Conteggi ed elenco viaggiano INSIEME di proposito: sono la stessa
// informazione a due granularità e li legge la stessa scheda. Due chiamate
// separate potrebbero cadere a cavallo di un giro e mostrare «2 critiche» sopra
// un elenco di tre.
export function getLottoSegnalazioni(lottoId, { livello = null } = {}) {
  const params = livello ? { livello } : {}
  return api.get(`${BASE}/${lottoId}/segnalazioni/`, { params })
}

// POST avanza pipeline lotto di UN step (com'è il motore). Riusata anche per il
// rerun su ERRORE: stesso endpoint, stesso lotto. `lock_batch_id` opzionale per
// correlare gli eventi del giro.
export function runLottoPipeline(lottoId, { lockBatchId = null } = {}) {
  const payload = { lotto_id: lottoId }
  if (lockBatchId) payload.lock_batch_id = lockBatchId
  return api.post(
    '/vendite/pipeline/run/',
    payload,
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST «Rendi definitive» (C-4): numerazione di un singolo lotto EMESSA. Esegue
// lo step DEFINITIVA (numera + accoda stampa). Gate fiscale separato (I-7):
// endpoint e permesso dedicati (numera_fatture_lotti), distinto da «Avanza».
export function numeraLotto(lottoId) {
  return api.post(
    `/vendite/fatturazione/lotti/${lottoId}/numera/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST ristampa MASSIVA di un lotto DEFINITIVA (C-8): accoda in coda stampa una
// riga per fattura non esclusa; il worker draina_coda_stampa le renderizza
// (async). Ritorna { lotto_id, accodate }. Re-stampa, mai numerazione (gate BE
// DEFINITIVA). Accodamento sincrono (non un job con polling).
export function ristampaLotto(lottoId) {
  return api.post(
    `/vendite/fatturazione/lotti/${lottoId}/ristampa/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// GET esiti giri fatturazione per corsia (job_run_log) + stato coda stampa
// (conteggi per stato, scope emittente operatore). Sola lettura (C-5).
//
// `competenzaMese` (YYYY-MM-DD, opzionale): restringe i GIRI a quelli lanciati
// per quel mese. Senza, sono i totali da sempre. La coda stampa non è mai
// filtrata: è lo stato attuale della coda, non un dato di periodo.
export function getFatturazioneEsiti(competenzaMese = null) {
  return api.get('/vendite/fatturazione/esiti/', {
    params: competenzaMese ? { competenza_mese: competenzaMese } : {},
  })
}

// POST «Fattura competenza» (C-3/C-6): avvia un GIRO di fatturazione on-demand,
// NON bloccante (I-3). Accoda un job in dbops.coda_lavori e ritorna subito
// { job_id, stato: 'PENDING' }; l'avanzamento si segue via getFatturazioneRun.
// Si ferma a EMESSA (D-1): la numerazione è atto separato (I-7). Idempotenza a
// 2 layer: header HTTP + chiave business competenza+scope[+gruppi].
//
// `gruppi` (emissione mirata): array di `gruppo_key` prese da
// listDashboardCompetenzaGruppi. Presente → si fatturano SOLO quei gruppi
// fatturabili (un documento sorgente o gli oneri di una commessa) e la corsia
// non filtra: la selezione dell'operatore è un perimetro più preciso
// dell'instradamento automatico. Assente → giro di massa del mese, invariato.
//
// L'esito del job (`result`) porta `lotti: [{lotto_id, …}]`: sono N, non uno —
// un gruppo con righe di tipo doc fiscale diverso finisce in lotti diversi.
export function runFatturazione(competenzaMese, { gruppi = null } = {}) {
  const payload = { competenza_mese: competenzaMese }
  if (gruppi && gruppi.length) payload.gruppi = gruppi
  return api.post(
    '/vendite/fatturazione/run/',
    payload,
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST «Rendi definitive competenza» (C-4/C-7): numerazione di PERIMETRO, NON
// bloccante. Accoda un job che esegue lo step DEFINITIVA (numera + accoda
// stampa) sui lotti EMESSA del mese. Atto fiscale SEPARATO dalla fatturazione
// (I-7). Ritorna { job_id, stato: 'PENDING' }; avanzamento via getFatturazioneRun.
export function runNumerazione(competenzaMese) {
  return api.post(
    '/vendite/fatturazione/numera/',
    { competenza_mese: competenzaMese },
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// GET stato di un job accodato (polling, C-3/C-4/C-6/C-7). Ownership per SCOPE:
// un job di altro scope/inesistente → 404. Sola lettura (nessuna Idempotency-Key).
export function getFatturazioneRun(jobId) {
  return api.get(`/vendite/fatturazione/run/${jobId}/`)
}

// POST reset del lotto a bozza (DEMOLIZIONE pre-fiscale): cancella le fatture
// non numerate; le attività tornano libere per un lotto nuovo. Azione forte.
export function resetLottoDraft(lottoId) {
  return api.post(
    `${BASE}/${lottoId}/reset-draft/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST ritorno del lotto a BOZZA (Fase 6). Da non confondere con
// `resetLottoDraft` qui sopra, che invece CHIUDE il lotto: questo lo rimette in
// lavorazione perché si possa correggere a monte e rifare il giro. Le fatture
// si cancellano comunque — è un rollback, non una riapertura — ma il rilancio
// le rigenera, e le righe di commessa tornano «da emettere».
export function riportaLottoADraft(lottoId) {
  return api.post(
    `${BASE}/${lottoId}/riporta-a-draft/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

// POST elimina UNA fattura dal lotto, liberandone le attivita'. Togliere una
// fattura vuol dire CANCELLARLA (RD-7): non c'e' nessun archivio di documenti
// «estratti», coerente col ritorno in bozza del lotto intero, che le sue
// fatture le cancella gia'.
//
// Perimetro (DB 2026-08-04): lotto **e** fattura pre-fiscali, cioe' DRAFT o
// EMESSA. Prima il DB pretendeva il lotto in DRAFT mentre il drawer proponeva
// la voce su qualunque lotto con una fattura pre-fiscale: su un lotto EMESSA la
// chiamata falliva. L'URL resta `reset-draft/` — e' un contratto verso il
// client, non segue le rinomine della funzione DB.
//
// Ritorna 4 contatori: updated_attivita, deleted_fatture, deleted_righe,
// riemesse_attivita (righe di commessa tornate «da emettere»).
export function eliminaFatturaDaLotto(lottoId, fatturaId) {
  return api.post(
    `${BASE}/${lottoId}/fatture/${fatturaId}/reset-draft/`,
    {},
    { headers: { 'Idempotency-Key': generateIdempotencyKey() } },
  )
}

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

// GET i tentativi dei task del lotto — elenco PAGINATO e ordinabile
// (`vendite.fn_list_lotto_task_runs`), con il totale nell'envelope.
// ⚠️ `order_by` va lasciato al DB: la whitelist vive nella funzione, e su un
// nome ignoto ripiega sul default invece di rifiutare.
// ⭐ `taskStato` è un ARRAY di stati e viaggia separato da virgole: «errori e
//    annullati» è una domanda legittima quanto «solo errori», e con un valore
//    singolo non si potrebbe fare. Assente/vuoto = nessun filtro.
// ⚠️ Il vocabolario ammesso NON sta qui: lo possiede la funzione DB, e uno
//    stato che non conosce non aggiunge e non toglie nulla.
export function listLottoTaskRuns(
  lottoId,
  { page = 1, pageSize = 25, orderBy = null, orderDir = 'desc', taskStato = null, soloGiroCorrente = false } = {},
) {
  const params = { page_size: pageSize, offset: (page - 1) * pageSize, order_dir: orderDir }
  if (orderBy) params.order_by = orderBy
  if (taskStato?.length) params.task_stato = taskStato.join(',')
  if (soloGiroCorrente) params.solo_giro_corrente = true
  return api.get(`${BASE}/${lottoId}/task-runs/`, { params })
}

// Export delle tre liste del drawer lotto: CSV/XLSX con le colonne del
// catalogo (ordine, visibilità e permessi dell'utente) e gli STESSI filtri e
// ordinamento della lista a video — il file È la lista, non una seconda query
// che le somiglia.
// ⚠️ `formato` e non `format`: quest'ultimo è un magic parameter di DRF e
// verrebbe intercettato prima della view (memoria feedback_drf_format_magic_param).
export function exportLottoFatture(lottoId, params = {}) {
  return api.get(`${BASE}/${lottoId}/fatture/export/`, { params, responseType: 'blob' })
}

export function exportLottoTaskRuns(lottoId, params = {}) {
  return api.get(`${BASE}/${lottoId}/task-runs/export/`, { params, responseType: 'blob' })
}

export function exportLottoSegnalazioni(lottoId, params = {}) {
  return api.get(`${BASE}/${lottoId}/segnalazioni/export/`, { params, responseType: 'blob' })
}

// GET riepilogo segnalazioni del lotto: solo i CONTEGGI (critical/warning/
// attention) più `blocks_next_step`. Alimenta il banner di testata e le
// etichette del filtro.
export function getLottoSegnalazioni(lottoId) {
  return api.get(`${BASE}/${lottoId}/segnalazioni/`)
}

// GET l'ELENCO paginato delle segnalazioni (`vendite.fn_list_lotto_segnalazioni`):
// le due origini — log di fattura e log di lotto — in una lista sola, col
// documento e l'importo già composti dal DB.
//
// ⭐ Endpoint SEPARATO dal riepilogo, e non è una duplicazione: quello conta e
// il drawer lo chiede a ogni apertura; questo elenca, pagina e ordina, e serve
// solo quando la scheda è aperta. Farne uno solo vorrebbe dire portarsi dietro
// l'elenco per mostrarne un numero.
//
// `livello`/`origine` assenti = nessun filtro. `solo_attive` è true di default
// lato BE: una segnalazione ritirata non si mostra.
// ⚠️ La risposta porta `fuori_job_count`: quante restano fuori dall'ultima
// corsa di pipeline. Senza quel numero un elenco filtrato e uno vuoto si
// leggono uguali.
export function listLottoSegnalazioni(
  lottoId, { livello = null, page = 1, pageSize = 25, orderBy = null, orderDir = 'desc' } = {},
) {
  const params = { page, page_size: pageSize, order_dir: orderDir }
  if (livello) params.livello = livello
  if (orderBy) params.order_by = orderBy
  return api.get(`${BASE}/${lottoId}/segnalazioni/rows/`, { params })
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

// ⭐ LA STORIA DEL LOTTO — «cosa è successo a questo lotto, in che ordine»: il
//    lotto PIÙ le sue fatture, righe non-INFO. Sorgente
//    `script.vw_giornale_entita`, la vista che cuce i registri di evento; sul
//    lotto ne rispondono TRE (`EVENT_LOG`, `LOTTO_LOG`, `TASK_RUN`) più
//    `FATTURA_LOG` per i documenti che contiene.
//
// ⭐ «Il lotto più le sue fatture» è una decisione (Tid, 2026-08-24): il lotto
//    ripete «Esito fatture lotto · WARN» e il MOTIVO sta sulla fattura, perché
//    la sua entità è la fattura. Un pannello limitato al lotto sarebbe onesto e
//    nel giorno in cui serve non conterrebbe la risposta.
//
// ⛔ Da non confondere con `segnalazioni/`, che elenca i problemi APERTI da
//    risolvere: qui c'è anche ciò che è andato bene e i tentativi superati.
// ⚠️ 404 unificato inesistente/fuori scope, deciso dalla TESTATA: la vista da
//    sola risponderebbe zero righe, cioè «nessuna storia» invece di «non lo
//    vedi».
// ⭐ Ordinamento e filtri sono del SERVER: la lista è paginata, quindi filtrare
//    o riordinare qui lavorerebbe sulla sola pagina caricata.
export function getLottoGiornale(
  lottoId,
  { page = 1, pageSize = 50, sortBy = 'gravita', sortDir = 'desc', info = false } = {},
) {
  return api.get(`${BASE}/${lottoId}/giornale/`, {
    params: {
      page, page_size: pageSize, sort_by: sortBy, sort_dir: sortDir,
      // ⚠️ Solo quando serve: il default del server è «nascoste», e mandare
      // `info=false` esplicito funzionerebbe uguale ma legherebbe il client a
      // un default che è del backend.
      ...(info ? { info: true } : {}),
    },
  })
}

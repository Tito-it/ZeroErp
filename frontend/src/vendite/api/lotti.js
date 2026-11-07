// Client API lotti di fatturazione — registro dei giri (cockpit Fase B).
// Doc BE: api_lotti (lista+dettaglio), api_lotto_fatture_list, pipeline.
// La lista/dettaglio sono read; le azioni (avanza step, rerun, reset) sono
// write con Idempotency-Key. Nessuna logica: la macchina step/gate vive nel
// motore DB/BE, il drawer diagnostico rende ed esercita.
import api from '../../core/api'
import { USO_MISURA, misuraDefault } from '../../core/misurePagina'

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
// ⭐ `annullati`: come la lista, i lotti annullati restano fuori dal conteggio
//    a meno che l'operatore non li chieda (2026-09-12).
export function listLottiMensile(anno, { annullati = false } = {}) {
  return api.get(`${BASE}/mensile/`, { params: { anno, ...(annullati ? { annullati: true } : {}) } })
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

// GET i DOCUMENTI che il lotto ha preso in carico, con l'esito di ciascuno.
//
// ⭐ Non è un doppione di `listLottoFatture`, ed è la ragione per cui esiste
// (brief-db-esito-gruppo-lotto). Quella elenca le FATTURE del lotto: un
// documento che cade PRIMA di diventarne una non ha niente a cui appendersi e
// sparisce dal racconto — sul lotto LTF-0009578 se ne vedevano due su tre, e il
// terzo era nominato solo da una segnalazione, per giunta con
// l'identificativo della COMMESSA.
// ⚠️ Le due liste NON sono in corrispondenza 1:1 nemmeno a giro riuscito: una
// fattura può raccogliere più documenti. Sono due domande diverse.
// ⭐ La riga è l'UNIONE di due fatti (rev DB 2026-09-07): il PERIMETRO — che
// dichiarano i soli giri mirati — e l'ESITO, che c'è su entrambi i tipi di
// giro. Perciò la scheda dice qualcosa anche sui giri di massa, che prima
// restavano muti, e continua a mostrare i documenti dichiarati e non ancora
// tentati (esito vuoto).
// `statoEsecuzione` assente = tutti, compresi i mai tentati.
export function listLottoGruppi(
  lottoId, { limit = misuraDefault(USO_MISURA.PAGINA), offset = 0, orderBy = null, orderDir = null, statoEsecuzione = null } = {},
) {
  const params = { limit, offset }
  if (orderBy) params.order_by = orderBy
  // ⚠️ Il verso si manda SOLO insieme alla colonna: senza colonna il backend ha
  // un ordine di default suo — i falliti in cima — e un `asc` spedito a vuoto
  // lo annullerebbe.
  if (orderBy && orderDir) params.order_dir = orderDir
  if (statoEsecuzione) params.stato_esecuzione = statoEsecuzione
  return api.get(`${BASE}/${lottoId}/gruppi/`, { params })
}

// POST toglie N documenti dal giro di fatturazione
// (`vendite.fn_escludi_documento_da_giro`, brief-db-uscita-documento-dal-giro).
//
// ⭐ Un giro prende in carico N documenti; se uno è rotto il lotto si ferma e
// gli altri N-1 — che hanno già le loro bozze — non vengono emessi. Questo è il
// gesto che li libera: il documento esce, il lotto riparte con quelli che
// restano. Con più documenti rotti si ripete, e il lotto riparte quando esce
// l'ultimo.
//
// ⚠️ Le chiavi viaggiano nel BODY e non nel path: sono chiavi di dominio
// (`ORDINE_VENDITA:01a06…`) e contiene i due punti, che in un segmento di URL
// vanno codificati — un contratto che si sbaglia a mano.
// ⛔ `motivo` è OBBLIGATORIO e non ha un default: un documento che esce senza
// motivo è una riga che fra un mese nessuno sa spiegare (D-5). La regola la
// tiene il database; qui non c'è un ripiego che la aggiri.
// ⚠️ L'uscita è a SENSO UNICO (D-3): per rimettere tutto in un lotto solo si
// annulla il lotto e lo si rigenera.
// ⭐ Una LISTA anche per un documento solo, ed è una scelta: un endpoint solo,
// e la riga singola è una lista di uno. Due superfici per lo stesso verbo
// divergerebbero su permessi, conferme e forma dell'esito.
// ⭐ La risposta è un REPORT a tre stati (`COMPLETATO` / `PARZIALE` / `ERRORE`)
// e torna 200 anche quando falliscono tutti: chi legge DEVE guardare `esito` e
// `falliti`, dove ogni riga porta il suo CODICE — «già uscito» si legge diverso
// da «non è in errore».
// 🔴 `Idempotency-Key`, e la sua assenza NON e' un dettaglio: il backend chiede
// l'header su ogni write e senza risponde `E_IDEMPOTENCY_KEY_REQUIRED` — cioe'
// il verbo non parte affatto. Trovato provandolo a video il 2026-09-08: la
// conferma tornava un errore dopo che l'operatore aveva gia' scritto il motivo.
// ⚠️ Nessun test lo vedeva: i test del servizio chiamano la funzione Python, e
// l'header vive due strati piu' su.
export function escludiDocumentiDaGiro(lottoId, { gruppoKeys, motivo }) {
  return api.post(
    `${BASE}/${lottoId}/documenti/escludi/`,
    { gruppo_keys: gruppoKeys, motivo },
  )
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
  { limit = misuraDefault(USO_MISURA.PAGINA), offset = 0, orderBy = null, orderDir = 'desc', taskStato = null, soloGiroCorrente = false } = {},
) {
  // `limit`/`offset` come ogni lista (Tid 2026-10-21, un dialetto solo): fino a
  // quel giorno qui viaggiava `page_size` accanto a `offset`.
  const params = { limit, offset, order_dir: orderDir }
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

export function exportLottoGruppi(lottoId, params = {}) {
  return api.get(`${BASE}/${lottoId}/gruppi/export/`, { params, responseType: 'blob' })
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
  lottoId, { livello = null, limit = misuraDefault(USO_MISURA.PAGINA), offset = 0, orderBy = null, orderDir = 'desc' } = {},
) {
  const params = { limit, offset, order_dir: orderDir }
  if (livello) params.livello = livello
  if (orderBy) params.order_by = orderBy
  return api.get(`${BASE}/${lottoId}/segnalazioni/rows/`, { params })
}

// POST avanza pipeline lotto di UN step (com'è il motore). Riusata anche per il
// rerun su ERRORE: stesso endpoint, stesso lotto. `lock_batch_id` opzionale per
// correlare gli eventi del giro.
export function runLottoPipeline(lottoId, { lockBatchId = null } = {}, config = {}) {
  const payload = { lotto_id: lottoId }
  if (lockBatchId) payload.lock_batch_id = lockBatchId
  return api.post(
    '/vendite/pipeline/run/',
    payload,
    config,
  )
}

// POST «Rendi definitive» (C-4): numerazione di un singolo lotto EMESSA. Esegue
// lo step DEFINITIVA (numera + accoda stampa). Gate fiscale separato (I-7):
// endpoint e permesso dedicati (numera_fatture_lotti), distinto da «Avanza».
// `dataDocumento` (ISO `YYYY-MM-DD`, facoltativa): la data dichiarata per
// l'atto. Riscrive la data delle fatture non ancora numerate del lotto e ne
// RIGENERA i piani rate, prima di numerare. Assente/null = nessuna
// dichiarazione: i documenti tengono la data che hanno.
export function numeraLotto(lottoId, { dataDocumento = null } = {}, config = {}) {
  const payload = dataDocumento ? { data_documento: dataDocumento } : {}
  return api.post(
    `/vendite/fatturazione/lotti/${lottoId}/numera/`,
    payload,
    config,
  )
}

// GET la FINESTRA DI NUMERAZIONE di un perimetro: con quale data si puo'
// numerare, e da quale data i documenti partono adesso.
// Un perimetro solo per chiamata: `{ lottoId }`, `{ competenzaMese }` oppure
// `{ lotti }` (la selezione della lista). Due insieme → 400.
// Risposta: { lotto_id, competenza_mese, n_lotti, data_documento, data_corrente,
//             data_minima } — tutte ISO o null.
// ⚠️ `data_minima` null = nessun pavimento (nessun numero ancora emesso su quei
// sezionali), non «nessun limite noto».
// ⭐ Sul perimetro `lotti` il limite va richiesto di nuovo a OGNI cambio di
//    selezione: il pavimento è di ogni SEZIONALE, e aggiungere un lotto di un
//    altro registro può spostarlo in avanti.
export function getFinestraNumerazione({ lottoId = null, competenzaMese = null, lotti = null } = {}) {
  const params = {}
  if (lottoId != null) params.lotto_id = lottoId
  if (competenzaMese) params.competenza_mese = competenzaMese
  if (lotti?.length) params.lotti = lotti
  // ⛔ `indexes: null` NON è un dettaglio di stile: senza, axios serializza un
  //    array come `?lotti[]=12&lotti[]=15` (provato su axios 1.20, che è la
  //    versione in `package.json`), mentre il backend legge
  //    `query_params.getlist('lotti')` — cerca la chiave `lotti`, trova la
  //    chiave `lotti[]`, e non vede NIENTE.
  // ⚠️ Il difetto non si presenta come «parametro ignorato»: `_query_lotti_ids`
  //    traduce la lista vuota in `None` di proposito (assente = «non sto
  //    chiedendo per selezione»), quindi il servizio riceve tutti e tre i
  //    perimetri nulli e risponde `E_VALIDATION_INPUT` — «indicarne esattamente
  //    uno» — su una richiesta in cui l'operatore UNO l'aveva indicato.
  //    A video: «La finestra di numerazione non è stata letta».
  // ⭐ Qui prima c'era un commento che affermava l'opposto («axios serializza
  //    un array così di default»). Era falso, ed è il motivo per cui questa
  //    riga è arrivata fino al collaudo: la giustificazione era scritta accanto
  //    al codice e nessuno l'ha messa alla prova. Trovato in-app da Tid il
  //    2026-08-27, primo giro vero del verbo su selezione.
  return api.get('/vendite/fatturazione/finestra-numerazione/', {
    params,
    paramsSerializer: { indexes: null },
  })
}

// POST ristampa MASSIVA di un lotto DEFINITIVA (C-8): accoda in coda stampa una
// riga per fattura non esclusa; il worker draina_coda_stampa le renderizza
// (async). Ritorna { lotto_id, accodate }. Re-stampa, mai numerazione (gate BE
// DEFINITIVA). Accodamento sincrono (non un job con polling).
export function ristampaLotto(lottoId, config = {}) {
  return api.post(
    `/vendite/fatturazione/lotti/${lottoId}/ristampa/`,
    {},
    config,
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
// NON bloccante (I-3). Accoda in dbops.coda_lavori UN LAVORO PER AZIENDA (uno
// con un'azienda scelta, uno per ciascuna in modalita' «Tutti gli emittenti»:
// BE10 a, 2026-11-07) e ritorna subito { lavori: [{ job_id, stato,
// emittente_fiscale_id, emittente_codice, gruppi? }] }; ogni lavoro si segue
// via getFatturazioneRun (`useJobPolling().seguiLavori`).
// Si ferma a EMESSA (D-1): la numerazione è atto separato (I-7). Idempotenza a
// 2 layer: header HTTP + chiave business competenza+azienda[+gruppi].
// ⭐ Con i gruppi il backend divide la selezione per azienda: ogni lavoro
//    porta in `gruppi` le SUE chiavi, ed e' su quelle che si marcano le righe.
//
// `gruppi` (emissione mirata): array di `gruppo_key` prese da
// listDashboardCompetenzaGruppi. Presente → si fatturano SOLO quei gruppi
// fatturabili (un documento sorgente o gli oneri di una commessa) e la corsia
// non filtra: la selezione dell'operatore è un perimetro più preciso
// dell'instradamento automatico. Assente → giro di massa del mese, invariato.
//
// L'esito del job (`result`) porta `lotti: [{lotto_id, …}]`: sono N, non uno —
// un gruppo con righe di tipo doc fiscale diverso finisce in lotti diversi.
// `dataDocumento` (facoltativa): la data dichiarata per i lotti che il giro
// creera'. Assente = la decide la POLITICA del registro (`OGGI` /
// `FINE_MESE_COMPETENZA`) — che non e' un sinonimo di «oggi».
export function runFatturazione(competenzaMese, { gruppi = null, dataDocumento = null } = {}, config = {}) {
  const payload = { competenza_mese: competenzaMese }
  if (gruppi && gruppi.length) payload.gruppi = gruppi
  if (dataDocumento) payload.data_documento = dataDocumento
  return api.post(
    '/vendite/fatturazione/run/',
    payload,
    config,
  )
}

// POST «Rendi definitive competenza» (C-4/C-7): numerazione di PERIMETRO, NON
// bloccante. Accoda un job che esegue lo step DEFINITIVA (numera + accoda
// stampa) sui lotti EMESSA del mese. Atto fiscale SEPARATO dalla fatturazione
// (I-7). Ritorna { lavori: [...] } come runFatturazione, un lavoro per azienda;
// con una selezione ogni lavoro porta in `lotti` i SUOI id. Avanzamento via
// getFatturazioneRun.
// `dataDocumento` (facoltativa): UNA data per l'INTERO atto — vale per tutti i
// lotti che il giro numera, non una per lotto (decisione 5 del brief).
// ⭐ `lotti`: il perimetro SELEZIONATO. Assente = tutti i lotti emessi della
//    competenza (atto di mese). ⛔ Una lista VUOTA non si manda: il backend la
//    rifiuta con un 400, e fa bene — «numera niente» e «numera tutto» non si
//    indovinano su un atto fiscale. Chi non ha spuntato nulla non deve premere.
export function runNumerazione(competenzaMese, { dataDocumento = null, lotti = null } = {}, config = {}) {
  const payload = { competenza_mese: competenzaMese }
  if (dataDocumento) payload.data_documento = dataDocumento
  if (lotti?.length) payload.lotti = lotti
  return api.post(
    '/vendite/fatturazione/numera/',
    payload,
    config,
  )
}

// GET stato di un job accodato (polling, C-3/C-4/C-6/C-7). Ownership per
// AZIENDA: un job di un'azienda fuori dal perimetro, o inesistente → 404. Sola lettura (nessuna Idempotency-Key).
export function getFatturazioneRun(jobId) {
  return api.get(`/vendite/fatturazione/run/${jobId}/`)
}

// POST reset del lotto a bozza (DEMOLIZIONE pre-fiscale): cancella le fatture
// non numerate; le attività tornano libere per un lotto nuovo. Azione forte.
export function resetLottoDraft(lottoId, config = {}) {
  return api.post(
    `${BASE}/${lottoId}/reset-draft/`,
    {},
    config,
  )
}

// POST ritorno del lotto a BOZZA (Fase 6). Da non confondere con
// `resetLottoDraft` qui sopra, che invece CHIUDE il lotto: questo lo rimette in
// lavorazione perché si possa correggere a monte e rifare il giro. Le fatture
// si cancellano comunque — è un rollback, non una riapertura — ma il rilancio
// le rigenera, e le righe di commessa tornano «da emettere».
export function riportaLottoADraft(lottoId, config = {}) {
  return api.post(
    `${BASE}/${lottoId}/riporta-a-draft/`,
    {},
    config,
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
// ⭐ Dal 2026-09-27 è la lista a catalogo `vendite.giornale` (la stessa della
//    Storia della fattura e del trasversale): contratto di lista standard dallo
//    store (`giornaleEntita`), più il filtro che è solo del lotto — `info`,
//    «anche le righe di routine» — e l'emittente del lotto
//    (`emittente_soggetto_ruolo_id`) che scioglie il cancello di perimetro.
export function listLottoGiornale(lottoId, params = {}) {
  return api.get(`${BASE}/${lottoId}/giornale/`, { params })
}

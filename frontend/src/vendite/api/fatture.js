// Client API fatture — CONSULTAZIONE.
// Doc BE: docs/it/backend/vendite/manual/api_fattura_dettaglio.md
//
// La fattura non ha CRUD: è prodotta dalla pipeline di fatturazione e oltre
// EMESSA le righe sono congelate a DB. Qui vive solo la lettura del documento
// per il drawer; stampa/allegati passano dal motore documentale
// (`/vendite/fatture/<id>/documenti/…`, BB `PdfDocumentiSorgenteDialog`) e le
// azioni di processo dal cockpit fatturazione.
import api from '../../core/api'
import { makeRigheListaApi } from '../_shared/righe/righeListaApi'

const BASE = '/vendite/fatture'

// GET documento completo: testata (cliente, emittente, pagamento, totali già
// decodificati) + righe + riepilogo IVA + scadenze in un round-trip.
// Sono gli stessi lettori che alimentano il contesto del PDF: video e stampa
// mostrano lo stesso documento per costruzione.
// 404 se la fattura non esiste **o** è fuori dallo scope emittente: i due casi
// sono indistinguibili di proposito.
export function getFatturaDettaglio(fatturaId) {
  return api.get(`${BASE}/${fatturaId}/`)
}

// ⭐ LA STORIA DEL DOCUMENTO: «cosa è successo a questa fattura, in ordine di
//    tempo». Sorgente `script.vw_giornale_entita`, la vista che cuce i registri
//    di evento del progetto — per la fattura oggi risponde `fatture_log`.
// ⛔ Da non confondere con `passaggi/`: quello dice con quali ALTRI documenti la
//    fattura è legata, questo cosa le è successo. Domande diverse, sorgenti
//    diverse.
// ⚠️ 404 unificato inesistente/fuori scope, come il dettaglio.
// ⭐ Dal 2026-09-27 è la lista a catalogo `vendite.giornale` filtrata sul
//    documento (la stessa del giornale trasversale): contratto di lista
//    standard — `limit`/`offset`/`order_by`/`order_dir` dallo store, più
//    `emittente_soggetto_ruolo_id`, l'emittente del documento che scioglie il
//    cancello di perimetro della lista. I params passano tali e quali: chi li
//    compone è lo store (`giornaleEntita`), non questo modulo.
export function listFatturaGiornale(fatturaId, params = {}) {
  return api.get(`${BASE}/${fatturaId}/giornale/`, { params })
}

// ⭐ LA LISTA DEI DOCUMENTI FISCALI — la settima del ciclo attivo. Sorgente
//    `vendite.vw_fatture_lista`, sullo stampo delle sei sorelle.
// ⚠️ `data_da`/`data_a` filtrano la DATA DEL DOCUMENTO, non la competenza della
//    commessa che l'ha generato: è la ragione per cui questa lista esiste.
export function listFatture(params = {}) {
  return api.get(`${BASE}/`, { params })
}

// ⚠️ `formato` e non `format`: quest'ultimo è un magic parameter di DRF e
//    verrebbe intercettato prima della view.
export function exportFatture(params = {}) {
  return api.get(`${BASE}/export/`, { params, responseType: 'blob' })
}

// Le righe come LISTA CONFIGURABILE `vendite.fattura_righe` (lista 102,
// brief-db-liste-righe-documento lotto C): pagina ed export, stessa factory dei
// quattro documenti gemelli. Sola lettura: niente POST sulle righe.
export const { listRigheLista, exportRigheLista } = makeRigheListaApi(BASE)

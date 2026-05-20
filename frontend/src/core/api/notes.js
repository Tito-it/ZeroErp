// Building block API client per note partizionate (vendite.note_*).
// Factory: il dominio passa basePath (es. '/vendite/preventivi/42' oppure
// '/vendite/contratti/7') e ottiene il set di metodi CRUD note pronto
// all'uso da composable e drawer. La factory non conosce il dominio
// sorgente: tutto cio' che cambia e' il basePath.
//
// Endpoint cablati lato BE (apps.core.api.partitioned_note_views.make_note_views):
//   GET    {basePath}/note/[?target_riga_id=&include_invisible=&page=&page_size=]
//   POST   {basePath}/note/                  (Idempotency-Key obbligatoria)
//   GET    {basePath}/note/{noteId}/
//   PATCH  {basePath}/note/{noteId}/
//   DELETE {basePath}/note/{noteId}/

import api from '../api'
import { generateIdempotencyKey } from '../utils/idempotency'

// Costruisce il set di metodi CRUD note bindati al basePath del dominio.
// Pattern simmetrico a `makeNotesApi('/vendite/preventivi/<id>')` o
// `makeNotesApi('/vendite/contratti/<id>')`.
export function makeNotesApi(basePath) {
  if (typeof basePath !== 'string' || !basePath) {
    throw new Error('makeNotesApi: basePath obbligatorio')
  }
  // Normalizza: rimuove eventuale slash trailing (lo aggiungiamo noi).
  const base = basePath.endsWith('/') ? basePath.slice(0, -1) : basePath

  // Lista note del documento. `params` ammette {target_riga_id, include_invisible, page, page_size}.
  function listNote(params = {}) {
    return api.get(`${base}/note/`, { params })
  }

  // Dettaglio singola nota.
  function getNota(noteId) {
    return api.get(`${base}/note/${noteId}/`)
  }

  // Crea nota. Genera Idempotency-Key automaticamente (richiesta dal BE).
  // Il payload accetta: testo, testo_md, anchor_tipo, posizione, seq,
  // visibile, solo_stampa, id_stile, id_lingua, meta, target_riga_id.
  function createNota(payload) {
    return api.post(`${base}/note/`, payload, {
      headers: { 'Idempotency-Key': generateIdempotencyKey() },
    })
  }

  // Aggiorna parzialmente nota. target_riga_id immutabile lato BE.
  function updateNota(noteId, payload) {
    return api.patch(`${base}/note/${noteId}/`, payload)
  }

  // Hard delete nota.
  function deleteNota(noteId) {
    return api.delete(`${base}/note/${noteId}/`)
  }

  return { basePath: base, listNote, getNota, createNota, updateNota, deleteNota }
}

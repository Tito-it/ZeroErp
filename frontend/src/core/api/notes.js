// Building block API client per note partizionate (vendite.note_*, catalogo.note).
// Factory: il dominio passa basePath (es. '/vendite/preventivi/42' oppure
// '/vendite/contratti/7') e ottiene il set di metodi CRUD note pronto
// all'uso da composable e drawer. La factory non conosce il dominio
// sorgente: tutto cio' che cambia e' il basePath.
//
// Pattern URL atteso (vendite, default):
//   GET    {basePath}/note/[?target_riga_id=&include_invisible=&limit=&offset=]
//   POST   {basePath}/note/                  (Idempotency-Key obbligatoria)
//   GET    {basePath}/note/{noteId}/
//   PATCH  {basePath}/note/{noteId}/
//   DELETE {basePath}/note/{noteId}/
// Cablato lato BE da `apps.core.api.partitioned_note_views.make_note_views`.
//
// Pattern URL alternativo (catalogo): LIST/POST sotto parent path, DETAIL
// (GET/PATCH/DELETE) su endpoint generico /catalogo/note/{noteId}/. Si attiva
// passando `detailBase` esplicito:
//   makeNotesApi('/catalogo/articoli/<id>', { detailBase: '/catalogo' })
// Il BB conserva la stessa interfaccia {listNote, getNota, createNota, ...};
// il chiamante non vede la differenza di URL routing.

import api from '../api'

// Normalizza un path stripando eventuale slash trailing — lo aggiunge il caller
// (es. `${base}/note/`). Riusato per basePath e detailBase.
function _stripTrailingSlash(path) {
  return path.endsWith('/') ? path.slice(0, -1) : path
}

// Scopo: la pagina delle note sotto il percorso del padre. Una sede sola per
//        l'URL: la usano `listNote` qui sotto e gli store di `noteLista`.
export function listNotePerPercorso(basePath, params = {}) {
  return api.get(`${_stripTrailingSlash(basePath)}/note/`, { params })
}

// Costruisce il set di metodi CRUD note bindati al basePath del dominio.
// Opzione `detailBase`: per domini (es. catalogo) in cui le rotte detail
// (GET/PATCH/DELETE) vivono su una root diversa dal parent path. Default
// `detailBase = basePath` (pattern vendite con detail parent-aware).
// Opzione `emittenteFiscaleId`: l'emittente del documento (PK), per le note
// col perimetro dell'emittente (`vendite.note`). ⚠️ Il cancello del BE vale
// per OGNI verbo dell'endpoint di lista, POST compreso: senza il parametro chi
// vede piu' emittenti avrebbe la lista ma non potrebbe creare (422).
export function makeNotesApi(basePath, { detailBase = null, emittenteFiscaleId = null } = {}) {
  if (typeof basePath !== 'string' || !basePath) {
    throw new Error('makeNotesApi: basePath obbligatorio')
  }
  if (detailBase != null && (typeof detailBase !== 'string' || !detailBase)) {
    throw new Error('makeNotesApi: detailBase deve essere stringa non vuota o null')
  }
  const base = _stripTrailingSlash(basePath)
  const detail = detailBase ? _stripTrailingSlash(detailBase) : base

  // Lista note del documento. `params` ammette {target_riga_id, include_invisible, limit, offset}.
  function listNote(params = {}) {
    return listNotePerPercorso(base, params)
  }

  // Dettaglio singola nota.
  function getNota(noteId) {
    return api.get(`${detail}/note/${noteId}/`)
  }

  // Crea nota (la Idempotency-Key la mette l'interceptor di `core/api.js`).
  // Il payload accetta: testo, testo_md, anchor_tipo, posizione, seq,
  // visibile, solo_stampa, id_stile, id_lingua, meta, target_riga_id.
  function createNota(payload) {
    const params = emittenteFiscaleId != null ? { emittente_fiscale_id: emittenteFiscaleId } : {}
    return api.post(`${base}/note/`, payload, { params })
  }

  // Aggiorna parzialmente nota. target_riga_id immutabile lato BE.
  function updateNota(noteId, payload) {
    return api.patch(`${detail}/note/${noteId}/`, payload)
  }

  // Hard delete nota.
  function deleteNota(noteId) {
    return api.delete(`${detail}/note/${noteId}/`)
  }

  return { basePath: base, detailBase: detail, listNote, getNota, createNota, updateNota, deleteNota }
}

// Composable building block per gestione note partizionate.
// Agnostico al dominio: consuma il set di metodi prodotto da `makeNotesApi`
// (core/api/notes.js). Drawer/wrapper di dominio (PreventivoNoteDrawer,
// ContrattoNoteDrawer, ecc.) ne istanziano uno per documento padre.
//
// Uso tipico in un drawer:
//   const apiClient = computed(() => makeNotesApi(`/vendite/preventivi/${props.preventivoId}`))
//   const { notes, total, loading, loadAll, save, remove } = useNote({ apiClient })
//
// `apiClient` puo' essere:
//   - oggetto statico {listNote, createNota, updateNota, deleteNota}
//   - ref/computed che ritorna lo stesso oggetto
// Cosi' il composable resta valido anche se il padre cambia id sub-resource.

import { ref, unref } from 'vue'

import { useApiHandler } from './useApiHandler'

// Helper: deref il client al momento della chiamata (no cache stale).
function _client(apiClient) {
  const c = unref(apiClient)
  if (!c || typeof c.listNote !== 'function') {
    throw new Error('useNote: apiClient invalido (atteso makeNotesApi(...)).')
  }
  return c
}

// Crea la reattivita' + i comandi CRUD bindati all'apiClient.
// `apiClient` deve avere {listNote, createNota, updateNota, deleteNota}.
// E' ammesso anche un ref/computed che produce l'oggetto: viene dereffato
// a ogni chiamata, cosi' un cambio di parent id riflette immediatamente.
export function useNote({ apiClient }) {
  // Validazione anticipata: anche se apiClient e' un ref, deve essere valido
  // al primo accesso (almeno per dare un errore precoce in dev).
  _client(apiClient)
  const { execute, loading } = useApiHandler()

  // Stato reattivo della lista corrente.
  const notes = ref([])
  const total = ref(0)
  const limit = ref(50)
  const offset = ref(0)

  // Carica le note del documento padre. `params` ammette
  //   { target_riga_id?, include_invisible?, limit?, offset? }.
  // ⭐ `limit`/`offset` come ogni lista (2026-10-21, un dialetto solo): fino a
  //    quel giorno `page`/`page_size`, che il backend ora rifiuta con un 400.
  // Aggiorna lo stato reattivo; ritorna i risultati anche al chiamante.
  async function loadAll(params = {}) {
    if (params.limit !== undefined) limit.value = params.limit
    if (params.offset !== undefined) offset.value = params.offset
    const queryParams = {
      limit: limit.value,
      offset: offset.value,
      ...params,
    }
    const data = await execute(() => _client(apiClient).listNote(queryParams))
    if (data !== null) {
      notes.value = Array.isArray(data.results) ? data.results : []
      total.value = typeof data.count === 'number' ? data.count : notes.value.length
    }
    return data
  }

  // Salva (create se id mancante, update altrimenti). Restituisce il payload
  // nota completo in caso di successo, null in errore. Il chiamante decide
  // se ricaricare la lista o sostituire l'item in-place.
  async function save(form) {
    if (!form || typeof form !== 'object') return null
    const id = form.id
    if (id) {
      // PATCH: invia solo i campi presenti, escludi id e campi immutabili
      // (target_tipo/target_id/target_riga_id sono governati dal BE).
      const patch = { ...form }
      delete patch.id
      delete patch.target_tipo
      delete patch.target_id
      delete patch.target_riga_id
      return await execute(() => _client(apiClient).updateNota(id, patch))
    }
    return await execute(() => _client(apiClient).createNota(form))
  }

  // Elimina una nota per id. Ritorna true se l'API ha risposto ok.
  async function remove(noteId) {
    const data = await execute(() => _client(apiClient).deleteNota(noteId))
    return data !== null
  }

  // Recupera una nota singola (utile per re-fetch post-update).
  async function fetchOne(noteId) {
    return await execute(() => _client(apiClient).getNota(noteId))
  }

  return {
    // Stato
    notes,
    total,
    limit,
    offset,
    loading,
    // Comandi
    loadAll,
    save,
    remove,
    fetchOne,
  }
}

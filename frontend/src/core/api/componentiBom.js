// Building block API client per i componenti BoM di una riga (modello
// unificato 2026-05-13). Factory: il dominio passa il path base
// (es. '/vendite/contratti' oppure '/vendite/preventivi') e ottiene il set
// di 4 metodi (preview / list / update / delete) pronto all'uso da drawer e
// composable. La factory non conosce il dominio: tutto cio' che cambia e' il
// path base. Gemello FE del pattern BE `make_note_views` /
// `PartitionedNoteRepository` (catalogo-building-block-backend.md).
//
// Pattern URL atteso (identico per ogni dominio vendite):
//   POST   {base}/{parentId}/righe/preview-componenti/
//   GET    {base}/{parentId}/righe/{rigaId}/componenti/[?solo_attivi=false]
//   PATCH  {base}/{parentId}/righe/{rigaId}/componenti/{componenteId}/
//   DELETE {base}/{parentId}/righe/{rigaId}/componenti/{componenteId}/
//
// NB esclusa di proposito l'offerta: usa il path `eccezioni/` (non `righe/`),
// divergenza voluta -> resta nei propri metodi in offerteApi.js.

import api from '../api'

// Normalizza il path stripando eventuale slash trailing — lo compongono i
// metodi (es. `${base}/${parentId}/...`).
function _stripTrailingSlash(path) {
  return path.endsWith('/') ? path.slice(0, -1) : path
}

// Costruisce il set di metodi componenti BoM bindati al path base del dominio.
export function makeComponentiBomApi(basePath) {
  if (typeof basePath !== 'string' || !basePath) {
    throw new Error('makeComponentiBomApi: basePath obbligatorio')
  }
  const base = _stripTrailingSlash(basePath)

  // Preview componenti pre-save (read-only): ritorna i figli BoM con
  // `prezzo_suggerito` dal resolver bundle-aware. Consumato da
  // `ComponentiDialog` PRIMA del save di una riga padre composita.
  // Payload: { articolo_id, uom_operativa_id, quantita }.
  function previewRigaComponenti(parentId, payload) {
    return api.post(`${base}/${parentId}/righe/preview-componenti/`, payload)
  }

  // `soloAttivi=true` default backcompat. EDIT panel passa false per includere
  // anche gli opzionali disattivati e permettere il toggle di riattivazione.
  function listRigaComponenti(parentId, rigaId, { soloAttivi = true } = {}) {
    const params = soloAttivi ? {} : { solo_attivi: 'false' }
    return api.get(`${base}/${parentId}/righe/${rigaId}/componenti/`, { params })
  }

  // PATCH singolo componente: `prezzo_unitario`, `attivo`, `meta` e basta
  // (`COMPONENTE_PATCH_OPERATORE` del backend). L'origine del prezzo la scrive
  // il server; IVA e campi del workflow L3 sono un 400.
  // PATCH: fuori dall'obbligo della Idempotency-Key (idempotente per semantica).
  function updateRigaComponente(parentId, rigaId, componenteId, payload) {
    return api.patch(
      `${base}/${parentId}/righe/${rigaId}/componenti/${componenteId}/`,
      payload,
    )
  }

  // Soft delete componente: il trigger DB ricalcola il prezzo della riga padre.
  function deleteRigaComponente(parentId, rigaId, componenteId) {
    return api.delete(
      `${base}/${parentId}/righe/${rigaId}/componenti/${componenteId}/`,
    )
  }

  return { previewRigaComponenti, listRigaComponenti, updateRigaComponente, deleteRigaComponente }
}

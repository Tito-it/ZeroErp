// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia admin per `documenti.template_asset` (Tranche L).
//        Non e' `createCrudStore` perche' il pattern CRUD admin qui e'
//        diverso: la creazione e' un UPLOAD multipart (FormData costruito dal
//        drawer) e c'e' il download del file. Dal 2026-09-18 la lista e'
//        `createListaStore` — era uno store scritto a mano su
//        `useListaEmptyStateFetch` con la copia del `buildParams` — e qui
//        restano solo le azioni di dominio.
//
//        `userScoped: true` di default (vedi factory).
// ------------------------------------------------------------

import { createListaStore } from '../../core/stores/createListaStore'
import {
  downloadTemplateAssetDocumento,
  getTemplateAssetDocumento,
  listTemplateAssetDocumenti,
  updateTemplateAssetDocumento,
  uploadTemplateAssetDocumento,
} from '../api/templateAssetDocumenti'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { TAB_ENTITIES } from '../../core/constants'

const STORE_NAME = 'config-template-asset-documenti'
const EMIT_KEY = TAB_ENTITIES.TEMPLATE_ASSET_DOCUMENTI

export const useTemplateAssetDocumentiStore = createListaStore(STORE_NAME, {
  fetchPage: listTemplateAssetDocumenti,
  // Parte piena, ma una ricerca sotto i 3 caratteri SVUOTA invece di lasciare
  // a video righe che non c'entrano con quello che si sta scrivendo: e' l'UX
  // che questa lista ha sempre avuto (`ricercaCorta`, migrazione 2026-08-10).
  startsEmpty: false,
  ricercaCorta: 'svuota',
  orderBy: 'codice',
  filterDefaults: {
    attivo: true,
    asset_tipo_id: null,
    emittente_fiscale_id: null,
  },
  extend: () => {
    const { emitDataChanged } = useTabEvents()

    async function fetchDetail(id) {
      const res = await getTemplateAssetDocumento(id)
      return res.data.data
    }

    async function download(id) {
      const res = await downloadTemplateAssetDocumento(id)
      return {
        blob: res.data,
        fileName: extractFileName(res) || `asset-${id}`,
      }
    }

    // Scopo: Upload asset (multipart). Il caller costruisce il FormData
    //        con `file` + i metadati. Lo store inoltra al BE e notifica
    //        i tab in ascolto via `emitDataChanged`.
    async function upload(formData) {
      const res = await uploadTemplateAssetDocumento(formData)
      emitDataChanged(EMIT_KEY, res.data.data.id)
      return res.data.data
    }

    // Scopo: PATCH metadati (no sostituzione file: per cambiare il file
    //        si carica un nuovo asset, Decisione 66).
    async function update(id, payload) {
      const res = await updateTemplateAssetDocumento(id, payload)
      emitDataChanged(EMIT_KEY, id)
      return res.data.data
    }

    return { fetchDetail, download, upload, update }
  },
})

function extractFileName(response) {
  const disposition = response?.headers?.['content-disposition']
  if (!disposition) return null
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) return decodeURIComponent(utf8Match[1])
  const plainMatch = disposition.match(/filename="?([^";]+)"?/i)
  return plainMatch?.[1] || null
}

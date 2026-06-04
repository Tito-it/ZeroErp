// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia per la lista documenti generati di una sorgente
//        (Tranche M). Lo stato della lista e' "scoped" alla coppia
//        (sorgenteCode, sorgenteId) attualmente aperta dal drawer:
//        cambiando sorgente il caller chiama `setSorgente(...)` per
//        ripartire pulito. Cosi' il pulsante/lista resta riusabile da
//        contesti diversi senza perdere l'isolamento.
//
//        `userScoped: true`: la lista contiene PDF/numeri progressivi
//        legati a una sorgente specifica visibile all'utente, non deve
//        leakare al cambio account.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useTabEvents } from '../../core/composables/useTabEvents'
import {
  contrattoDocumenti,
  offertaDocumenti,
  ordineDocumenti,
  preventivoDocumenti,
} from '../api/documentiPerSorgente'
import { SORGENTE_CODES } from '../constants'

const STORE_NAME = 'documenti-per-sorgente'
const EMIT_KEY = 'documenti_per_sorgente'

// Scopo: Mappa codice sorgente -> client API. Quando un nuovo dominio
//        sorgente entrera' nel motore documentale, basta aggiungere
//        l'entry qui (es. CONTRATTO -> contrattoDocumenti) per
//        riutilizzare lo store senza modifiche al componente FE.
const SORGENTE_CLIENT_MAP = {
  [SORGENTE_CODES.PREVENTIVO]: preventivoDocumenti,
  [SORGENTE_CODES.CONTRATTO]: contrattoDocumenti,
  [SORGENTE_CODES.OFFERTA_COMMERCIALE]: offertaDocumenti,
  [SORGENTE_CODES.ORDINE_VENDITA]: ordineDocumenti,
}

export const useDocumentiPerSorgenteStore = defineStore(STORE_NAME, () => {
  const { emitDataChanged } = useTabEvents()

  const sorgenteCode = ref(null)
  const sorgenteId = ref(null)
  const items = ref([])
  const totalRecords = ref(0)
  const loading = ref(false)
  const lastError = ref(null)

  // Scopo: Risolve il client API a partire dal codice sorgente attuale.
  //        Solleva error sincrono se il codice non e' mappato (bug FE).
  function getClient() {
    const client = SORGENTE_CLIENT_MAP[sorgenteCode.value]
    if (!client) {
      throw new Error(`SorgenteCode '${sorgenteCode.value}' non mappato in SORGENTE_CLIENT_MAP`)
    }
    return client
  }

  // Scopo: Imposta la sorgente corrente. Idempotente: se cambia la
  //        coppia, azzera la lista per non mostrare dati di un'altra
  //        sorgente residui.
  function setSorgente(code, id) {
    if (sorgenteCode.value !== code || sorgenteId.value !== id) {
      sorgenteCode.value = code
      sorgenteId.value = id
      items.value = []
      totalRecords.value = 0
      lastError.value = null
    }
  }

  // Scopo: Lista documenti generati per la sorgente corrente.
  async function fetchList(params = {}) {
    if (!sorgenteCode.value || !sorgenteId.value) return
    loading.value = true
    lastError.value = null
    try {
      const res = await getClient().list(sorgenteId.value, params)
      // L'envelope di list (Tranche K view): `success_response({...result, page, page_size})`.
      // Il `result` contiene `results`, `total_count`. Niente `paginated_envelope`.
      const data = res.data.data
      items.value = data.results || []
      totalRecords.value = data.total_count ?? items.value.length
    } catch (err) {
      lastError.value = err
      throw err
    } finally {
      loading.value = false
    }
  }

  // Scopo: Genera nuovo documento. Refresh lista in coda + emit event.
  async function genera(payload = {}) {
    if (!sorgenteId.value) throw new Error('Sorgente non impostata')
    const res = await getClient().genera(sorgenteId.value, payload)
    const generated = res.data.data
    emitDataChanged(EMIT_KEY, generated.id)
    await fetchList()
    return generated
  }

  // Scopo: Anteprima PDF (binary blob, no persist). Ritorna `{blob, fileName}`
  //        ricavando `fileName` dall'header Content-Disposition se presente.
  async function anteprima(payload = {}) {
    if (!sorgenteId.value) throw new Error('Sorgente non impostata')
    const res = await getClient().anteprima(sorgenteId.value, payload)
    return {
      blob: res.data,
      fileName: extractFileName(res) || 'anteprima.pdf',
    }
  }

  // Scopo: Download PDF persistito (binary blob).
  async function download(documentoId) {
    if (!sorgenteId.value) throw new Error('Sorgente non impostata')
    const res = await getClient().download(sorgenteId.value, documentoId)
    return {
      blob: res.data,
      fileName: extractFileName(res) || `documento-${documentoId}.pdf`,
    }
  }

  // Scopo: Lista file (principale + allegati) di un documento generato.
  async function listFiles(documentoId) {
    if (!sorgenteId.value) throw new Error('Sorgente non impostata')
    const res = await getClient().listFiles(sorgenteId.value, documentoId)
    return res.data.data
  }

  // Scopo: Aggiunge allegati (modalita' append) a un documento esistente.
  //        `files` = array di File: confezionati in FormData sotto `allegati`.
  async function aggiungiAllegati(documentoId, files) {
    if (!sorgenteId.value) throw new Error('Sorgente non impostata')
    const formData = new FormData()
    for (const file of files) formData.append('allegati', file)
    const res = await getClient().aggiungiAllegati(
      sorgenteId.value, documentoId, formData,
    )
    emitDataChanged(EMIT_KEY, documentoId)
    return res.data.data
  }

  // Scopo: Download di uno specifico file (principale o allegato) per id.
  async function downloadFile(documentoId, fileId) {
    if (!sorgenteId.value) throw new Error('Sorgente non impostata')
    const res = await getClient().downloadFile(sorgenteId.value, documentoId, fileId)
    return {
      blob: res.data,
      fileName: extractFileName(res) || `file-${fileId}`,
    }
  }

  return {
    sorgenteCode, sorgenteId, items, totalRecords, loading, lastError,
    setSorgente, fetchList, genera, anteprima, download,
    listFiles, aggiungiAllegati, downloadFile,
  }
}, { userScoped: true })


// Scopo: Estrae `filename` da un Content-Disposition. Helper standalone
//        per non dipendere da pacchetti esterni. Gestisce sia
//        `filename="x.pdf"` sia `filename*=UTF-8''x.pdf` (RFC 5987).
//        axios espone gia' `response.headers` come oggetto plain-object
//        case-insensitive: niente `.get()` Headers-API.
function extractFileName(response) {
  const cd = response.headers?.['content-disposition']
  if (!cd) return null
  // Cerco filename*=UTF-8''... (RFC 5987) prima di filename="..."
  const m1 = /filename\*=(?:UTF-8'')?([^;]+)/i.exec(cd)
  if (m1) {
    try { return decodeURIComponent(m1[1].trim()) } catch { /* fallback */ }
  }
  const m2 = /filename="?([^";]+)"?/i.exec(cd)
  if (m2) return m2[1].trim()
  return null
}

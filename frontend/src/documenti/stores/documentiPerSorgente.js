// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia delle AZIONI sui documenti generati di una sorgente
//        (Tranche M): genera, anteprima, download, file e allegati, ristampa
//        fedele. Il caller imposta la coppia (sorgenteCode, sorgenteId) con
//        `setSorgente(...)` prima di ogni azione.
//
// ⭐ La LISTA non sta piu' qui (2026-09-27): e' la lista configurabile
//    `documenti.documenti_sorgente`, con uno store per sorgente sul core
//    (`documentiSorgenteLista`). Qui teneva `items`/`fetchList` scritti a mano,
//    senza paginazione: la lista si fermava ai primi 50 documenti senza dirlo.
//
//        `userScoped: true`: la sorgente aperta e' dell'utente, non deve
//        restare al cambio account.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { SORGENTE_CLIENT_MAP } from '../api/documentiPerSorgente'

const STORE_NAME = 'documenti-per-sorgente'
const EMIT_KEY = 'documenti_per_sorgente'

export const useDocumentiPerSorgenteStore = defineStore(STORE_NAME, () => {
  const { emitDataChanged } = useTabEvents()

  const sorgenteCode = ref(null)
  const sorgenteId = ref(null)

  // Scopo: Risolve il client API a partire dal codice sorgente attuale.
  //        Solleva error sincrono se il codice non e' mappato (bug FE).
  function getClient() {
    const client = SORGENTE_CLIENT_MAP[sorgenteCode.value]
    if (!client) {
      throw new Error(`SorgenteCode '${sorgenteCode.value}' non mappato in SORGENTE_CLIENT_MAP`)
    }
    return client
  }

  // Scopo: Imposta la sorgente su cui agiscono le azioni seguenti.
  function setSorgente(code, id) {
    sorgenteCode.value = code
    sorgenteId.value = id
  }

  // Scopo: Genera nuovo documento + emit event.
  // ⚠️ Non ricarica piu' la lista: la lista ha il suo store
  //    (`documentiSorgenteLista`), e chi la mostra la ricarica dal proprio
  //    scaffolding.
  async function genera(payload = {}) {
    if (!sorgenteId.value) throw new Error('Sorgente non impostata')
    const res = await getClient().genera(sorgenteId.value, payload)
    const generated = res.data.data
    emitDataChanged(EMIT_KEY, generated.id)
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

  // Scopo: RISTAMPA FEDELE (percorso 3): ri-renderizza il documento com'era.
  //        Ritorna anche `pdfHashMatch`, letto dall'header
  //        `X-Ristampa-Pdf-Hash-Match`: `true` = identico byte per byte,
  //        `false` = fedele nel CONTENUTO ma non nei byte (renderer non
  //        deterministico, decisione §8.2). Il caller lo dice all'operatore
  //        invece di nasconderlo. `null` se l'header manca (proxy che lo
  //        filtra): "non verificabile" != "diverso", e va distinto.
  async function ristampaFedele(documentoId) {
    if (!sorgenteId.value) throw new Error('Sorgente non impostata')
    const res = await getClient().ristampaFedele(sorgenteId.value, documentoId)
    const raw = res.headers?.['x-ristampa-pdf-hash-match']
    return {
      blob: res.data,
      fileName: extractFileName(res) || `documento-${documentoId}.pdf`,
      pdfHashMatch: raw == null ? null : raw === '1',
    }
  }

  return {
    sorgenteCode, sorgenteId,
    setSorgente, genera, anteprima, download,
    listFiles, aggiungiAllegati, downloadFile, ristampaFedele,
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

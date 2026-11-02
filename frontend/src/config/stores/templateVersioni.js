// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Store Pinia delle versioni di un singolo template documentale
//        (Tranche L): la LISTA configurabile `documenti.template_versioni`
//        (88) + il ciclo di vita — `fetchDetail`, create/update/delete,
//        clona, pubblica.
//
// ⭐ DAL 2026-09-27 LA LISTA STA SUL CORE (`useListaStoreCore`: filtri, fetch
//    paginata, `fetchSospesa`, reset, «vuota» contro «non letta»). Era una
//    `fetchList(templateId)` scritta a mano, senza paginazione, perche' «il
//    ciclo BOZZA→PUBBLICATA→OBSOLETA ha per design cardinalita' contenuta»:
//    una previsione sui DATI, e le previsioni sui dati non decidono la forma
//    di una lista. Il padre (il template) sta nel PATH: `parentField`.
// ⭐ `useListaStoreCore` DIRETTO dentro `defineStore` e non `createListaStore`:
//    lo store ha i verbi del ciclo di vita (forma ammessa, catalogo BB).
// ⭐ IL PADRE E' COMPOSTO: il template (nel path) e il suo EMITTENTE (in query,
//    `emittente_fiscale_id`, il `lista_emittente_param` della view) — il padre
//    composto del core (`emittenteParam`, 2026-09-27). Finche' manca
//    l'emittente la lista non legge ed e' in `attesaPadre`. ⛔ Fino a quel
//    giorno era un `ref` dello store letto dalla `fetchPage`, e la lista
//    partiva anche senza. La creazione passa l'emittente con
//    `paramsEmittente()`: il cancello vale per ogni metodo della view, e il
//    nome del parametro ha una sede sola.
//        `userScoped: true` per coerenza con le memorie del progetto:
//        i dati versione corrente del template aperto contengono html/
//        css/markdown — non devono leakare al cambio utente.
// ------------------------------------------------------------

import { defineStore } from 'pinia'
import { useListaStoreCore } from '../../core/composables/useListaStoreCore'
import { storePerIstanza } from '../../core/stores/storePerIstanza'
import {
  clonaTemplateVersione,
  createTemplateVersione,
  deleteTemplateVersione,
  getTemplateVersione,
  listTemplateVersioni,
  pubblicaTemplateVersione,
  updateTemplateVersione,
} from '../api/templateDocumenti'
import { useTabEvents } from '../../core/composables/useTabEvents'

const STORE_NAME = 'config-template-versioni'
const EMIT_KEY = 'template_versioni'

// Uno store per sezione (`storePerIstanza`): due template aperti insieme non
// si scrivono addosso le versioni.
export const useTemplateVersioniStore = storePerIstanza(STORE_NAME, (id) => defineStore(id, () => {
  const { emitDataChanged } = useTabEvents()

  const lista = useListaStoreCore({
    fetchPage: listTemplateVersioni,
    parentField: 'templateId',
    // L'emittente del template, in query sulla lista E sulla creazione.
    // ⚠️ Non e' un filtro: le righe le fissa il template nel path.
    emittenteParam: 'emittente_fiscale_id',
    // Parte piena: sono le versioni di QUESTO template.
    startsEmpty: false,
    // La versione piu' recente in cima: e' il preset a catalogo
    // (`versione desc`) e il default del backend.
    orderBy: 'versione',
    orderDir: 'desc',
    orderDirDefault: 'desc',
  })

  // Scopo: Dettaglio versione singola (incluso payload html/css/markdown).
  async function fetchDetail(templateId, versioneId) {
    const res = await getTemplateVersione(templateId, versioneId)
    return res.data.data
  }

  // Scopo: Crea nuova versione BOZZA.
  async function create(templateId, payload) {
    const res = await createTemplateVersione(templateId, payload, lista.paramsEmittente())
    emitDataChanged(EMIT_KEY, res.data.data.id)
    return res.data.data
  }

  // Scopo: Update versione BOZZA. PUBBLICATA -> errore service-side
  //        (E_DOCUMENTI_VERSIONE_PUBBLICATA_IMMUTABILE) + trigger DB A1.
  async function update(templateId, versioneId, payload) {
    const res = await updateTemplateVersione(templateId, versioneId, payload)
    emitDataChanged(EMIT_KEY, versioneId)
    return res.data.data
  }

  // Scopo: Hard DELETE versione (solo BOZZA, trigger DB A2 block_delete).
  async function destroy(templateId, versioneId) {
    await deleteTemplateVersione(templateId, versioneId)
    emitDataChanged(EMIT_KEY, versioneId)
  }

  // Scopo: Clona versione esistente -> nuova BOZZA.
  async function clona(templateId, versioneId, payload = {}) {
    const res = await clonaTemplateVersione(templateId, versioneId, payload)
    emitDataChanged(EMIT_KEY, res.data.data.id)
    return res.data.data
  }

  // Scopo: Transizione BOZZA -> PUBBLICATA con `valido_dal` obbligatorio.
  async function pubblica(templateId, versioneId, payload) {
    const res = await pubblicaTemplateVersione(templateId, versioneId, payload)
    emitDataChanged(EMIT_KEY, versioneId)
    return res.data.data
  }

  return {
    ...lista,
    fetchDetail, create, update, destroy, clona, pubblica,
  }
}, { userScoped: true }))

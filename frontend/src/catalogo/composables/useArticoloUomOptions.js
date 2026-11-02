// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Scopo: Composable per il pattern UoM operative articolo (Fase 4.F1
//        refactor frontend vendite). Centralizza fetch + reset + helper
//        di selezione base. Le 4 occorrenze (PromoArticoloDrawer,
//        ContrattoRigheDrawer, VersioneDrawer, PreventiviRigaForm)
//        avevano la stessa funzione `loadUomPerArticolo` con micro-differenze
//        sul criterio di pre-seleziona base (formMode vs isEdit vs flag custom):
//        qui la fetch e' pura, il caller decide quando applicare il base id.
import { ref } from 'vue'
import { lookupArticoloUom } from '../api/catalogo'
import { useFetchVersion } from '../../core/composables/useFetchVersion'

/**
 * Pattern caricamento UoM operative dell'articolo selezionato.
 *
 * Restituisce stato reattivo (`uomOptions`, `uomLoading`) + 3 helper:
 * - `loadUomPerArticolo(articoloId)` — fetch dal BE, popola `uomOptions`,
 *   ritorna la lista risultante. Se articoloId e' falsy, resetta e ritorna [].
 * - `pickBaseUomId(list)` — ritorna `uom_id` della UoM base (o l'unica UoM
 *   se la lista ha un solo elemento, o null se la lista e' vuota).
 *   Pattern condiviso: `list.find(u => u.is_base) ?? list[0]`.
 * - `resetUomOptions()` — azzera (utile su close drawer / reset form).
 *
 * Esempio consumer (create con auto-pickBase):
 *   async function onArticoloSelect(item) {
 *     form.value.uom_id = null
 *     const list = await loadUomPerArticolo(item?.id)
 *     if (!isEdit.value && !form.value.uom_id) {
 *       form.value.uom_id = pickBaseUomId(list)
 *     }
 *   }
 *
 * Esempio consumer (edit, no auto-pick — UoM gia' valorizzata da detail):
 *   if (data.articolo_id) await loadUomPerArticolo(data.articolo_id)
 */
export function useArticoloUomOptions() {
  const uomOptions = ref([])
  const uomLoading = ref(false)
  // Guard di versione (BB core useFetchVersion) per scartare risposte stantie:
  // due chiamate concorrenti (es. articolo cambiato 2 volte di fila in modo
  // veloce) non devono sovrascrivere `uomOptions` col risultato della prima
  // fetch (lenta) dopo la seconda (veloce). La logica di loading resta qui:
  // il BB copre solo il confronto tag/isCurrent/invalidate.
  const fv = useFetchVersion()

  async function loadUomPerArticolo(articoloId) {
    const tk = fv.tag()
    uomOptions.value = []
    if (!articoloId) return []
    uomLoading.value = true
    try {
      const res = await lookupArticoloUom(articoloId)
      // Endpoint puo' rispondere paginated `{results: [...]}` o lista diretta.
      const list = res.data.data?.results || res.data.data || []
      // Risposta stantia (un'altra fetch e' partita nel frattempo): scarta.
      if (!fv.isCurrent(tk)) return []
      uomOptions.value = list
      return list
    } catch (err) {
      // Best-effort: errore di rete o 5xx -> combo vuota, no toast (il caller
      // puo' propagarlo se serve). Log per debug: senza questo, una combo che
      // resta vuota in produzione non lascia traccia in console.
      console.warn('[useArticoloUomOptions] loadUomPerArticolo failed', { articoloId, err })
      if (fv.isCurrent(tk)) uomOptions.value = []
      return []
    } finally {
      // Spegni loading solo se questa e' l'ultima fetch: una stantia
      // non deve azzerare lo spinner di una piu' recente ancora in corso.
      if (fv.isCurrent(tk)) uomLoading.value = false
    }
  }

  function pickBaseUomId(list) {
    if (!Array.isArray(list) || list.length === 0) return null
    const base = list.find(u => u.is_base)
    if (base) return base.uom_id
    // Singola UoM disponibile: pre-selezione automatica per UX.
    return list.length === 1 ? list[0].uom_id : null
  }

  function resetUomOptions() {
    // Invalida: una fetch in corso non sovrascrive mai dopo reset.
    fv.invalidate()
    uomOptions.value = []
  }

  return {
    uomOptions,
    uomLoading,
    loadUomPerArticolo,
    pickBaseUomId,
    resetUomOptions,
  }
}

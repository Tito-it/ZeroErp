// Scopo: Composable generico per caricare/aggiornare/eliminare i componenti
//        BoM di una riga padre composita (modello unificato 2026-05-13).
//        Parametrico sulla sorgente documento (preventivo/contratto/ordine/
//        ddt) via callback API + chiave TAB_ENTITIES per emit cross-tab.
//
//        Pattern token "scarta risposte stantie" (via useFetchVersion) per
//        switch rapido tra righe espanse. Reload automatico post update/
//        delete: il prezzo padre e' calcolato dai trigger DB e cambia a
//        ogni mutazione del componente — meglio avere lo snapshot
//        sincronizzato.
//
//        Estratto da `usePreventivoRigaComponenti.js` (Fase H 2026-05-14)
//        per supportare la nuova sessione contratti senza duplicare 100
//        righe di codice. Il wrapper preventivi-specifico, rimasto senza
//        consumatori, e' stato ritirato il 2026-09-26.

import { ref, toValue } from 'vue'

import { useFetchVersion } from './useFetchVersion'
import { useTabEvents } from './useTabEvents'

// Scopo: Factory generica componenti riga padre.
//
// `documentoIdInput`: scalar number, ref<number> o getter `() => props.x`.
//   Risolto via `toValue()` (Vue 3.3+). DEVE essere reattivo nei consumer
//   in cui il documentoId puo' cambiare in volo (es. drawer PrimeVue
//   riusato cross-documento senza rimount): passare `() => props.documentoId`
//   o `toRef(props, 'documentoId')`, NON `props.documentoId` scalar
//   (verrebbe catturato al setup e mai aggiornato).
// `apiList(documentoId, rigaId, { soloAttivi })`: GET lista componenti.
//   Atteso ritorno `res.data.data = lista[]`.
// `apiUpdate(documentoId, rigaId, componenteId, payload)`: PATCH componente.
// `apiDelete(documentoId, rigaId, componenteId)`: soft DELETE componente.
//   Esposto via `remove()` ma non invocato dal building block
//   `ComponentiPanel`: e' a disposizione di consumer custom (es. drawer
//   revisione futuro). Resta required per simmetria con le 4 sorgenti BE.
// `factoryOptions.soloAttivi` (default true): modalita' istanza-bound.
//   - true: expander tabella righe (solo componenti attivi).
//   - false: EDIT panel (include opzionali disattivati per toggle).
// `factoryOptions.tabEntity` (string, opzionale): chiave TAB_ENTITIES
//   per `emitDataChanged` post-write (cross-tab refresh). Se None nessun
//   emit.
export function useRigaComponenti(
  documentoIdInput,
  { apiList, apiUpdate, apiDelete, soloAttivi = true, tabEntity = null } = {},
) {
  if (typeof apiList !== 'function'
      || typeof apiUpdate !== 'function'
      || typeof apiDelete !== 'function') {
    throw new Error(
      'useRigaComponenti: apiList/apiUpdate/apiDelete callbacks obbligatorie',
    )
  }

  const { emitDataChanged } = useTabEvents()
  // `tag` aliasato a `nextToken` per leggibilita' locale (semantica identica).
  const { tag: nextToken, isCurrent, invalidate } = useFetchVersion()

  const componenti = ref([])
  const loading = ref(false)
  const currentRigaId = ref(null)

  // `toValue` legge dinamicamente da scalar/ref/getter. Garantisce
  // reattivita' su cambio props.documentoId nel consumer (vedi nota sopra).
  function did() {
    return toValue(documentoIdInput)
  }

  function notifyChanged() {
    if (tabEntity) {
      emitDataChanged(tabEntity, did())
    }
  }

  // Scopo: Carica i componenti per `rigaId`. Aggiorna `componenti` reattivo
  // + `currentRigaId`. Ritorna la lista (utile per chain post-load).
  // La modalita' `soloAttivi` e' fissata al factory.
  async function load(rigaId) {
    if (rigaId == null) {
      componenti.value = []
      currentRigaId.value = null
      return []
    }
    const tk = nextToken()
    loading.value = true
    currentRigaId.value = rigaId
    try {
      const res = await apiList(did(), rigaId, { soloAttivi })
      if (!isCurrent(tk)) return componenti.value
      componenti.value = res.data?.data ?? []
      return componenti.value
    } finally {
      if (isCurrent(tk)) loading.value = false
    }
  }

  // Scopo: PATCH componente + reload sincrono. Errori si propagano al
  // chiamante: il consumer (form) li mappa a banner/toast. Emit cross-tab
  // se `tabEntity` fornito al factory.
  async function update(rigaId, componenteId, payload) {
    const res = await apiUpdate(did(), rigaId, componenteId, payload)
    await load(rigaId)
    notifyChanged()
    return res.data?.data
  }

  // Scopo: Soft delete + reload. Il trigger DB ricalcola il prezzo della
  // riga padre come SUM residuo.
  async function remove(rigaId, componenteId) {
    const res = await apiDelete(did(), rigaId, componenteId)
    await load(rigaId)
    notifyChanged()
    return res.data?.data
  }

  function reset() {
    componenti.value = []
    currentRigaId.value = null
    invalidate()
  }

  return { componenti, loading, currentRigaId, load, update, remove, reset }
}

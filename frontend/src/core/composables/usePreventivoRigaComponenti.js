// Scopo: Composable per caricare/aggiornare/eliminare i componenti BoM CASO A
//        di una riga preventivo (refactor componenti 2026-05-11). Ogni
//        istanza gestisce UN riga padre alla volta: i consumer (DataTable
//        expander della tabella righe + sezione form della riga in modifica)
//        creano la loro istanza con il preventivoId fissato al mount.
//
//        Pattern token per scartare risposte stantie su switch rapido tra
//        righe espanse (allineato a useArticoloUomOptions). Reload automatico
//        post update/delete: il prezzo padre e' calcolato dai trigger DB e
//        cambia a ogni mutazione del componente, conviene avere lo snapshot
//        sincronizzato.
//
//        Quando il pattern verra' replicato sulle 4 sorgenti future
//        (ordini/contratti/ddt/consumi) si avranno composable paralleli con
//        firma identica — la generalizzazione (es. useRigaComponenti(api))
//        e' YAGNI fino al 2o consumer reale.

import { ref, unref } from 'vue'
import {
  listRigaComponenti,
  updateRigaComponente,
  deleteRigaComponente,
} from '../../vendite/preventivi/api/preventiviApi'
import { useTabEvents } from './useTabEvents'
import { TAB_ENTITIES } from '../constants'

// preventivoIdInput accetta scalar (number) o ref<number>. unref() risolve
// entrambi i casi: consente al consumer di passare props.preventivoId
// reattivo se il valore puo' cambiare nel ciclo di vita dell'istanza.
// Nella pratica corrente (table expander + form panel) e' un props number
// stabile per istanza, ma la firma non si vincola al caso piu' restrittivo.
//
// `factoryOptions.soloAttivi` (default true): modalita' istanza-bound.
//   - true: l'expander tabella righe vede solo componenti `attivo=TRUE`.
//   - false: l'EDIT panel vede anche opzionali disattivati per il toggle
//     di riattivazione.
// Bound al factory: tutte le `load()` successive (incluse le ricariche
// post `update`/`remove`) usano la stessa modalita'. Esplicito > implicito.
export function usePreventivoRigaComponenti(preventivoIdInput, { soloAttivi = true } = {}) {
  const { emitDataChanged } = useTabEvents()
  const componenti = ref([])
  const loading = ref(false)
  const currentRigaId = ref(null)
  let _token = 0

  function pid() {
    return unref(preventivoIdInput)
  }

  // Scopo: Carica i componenti per `rigaId`. Aggiorna `componenti` reattivo
  //        + `currentRigaId` per consentire al template di sapere quale
  //        riga padre e' attualmente esposta. Ritorna la lista (utile per
  //        chain post-load). La modalita' `soloAttivi` e' fissata al factory.
  async function load(rigaId) {
    if (rigaId == null) {
      componenti.value = []
      currentRigaId.value = null
      return []
    }
    const tk = ++_token
    loading.value = true
    currentRigaId.value = rigaId
    try {
      const res = await listRigaComponenti(pid(), rigaId, { soloAttivi })
      // Token pattern: scarta risposte di richieste superate da una piu' nuova.
      if (tk !== _token) return componenti.value
      componenti.value = res.data?.data ?? []
      return componenti.value
    } finally {
      if (tk === _token) loading.value = false
    }
  }

  // Scopo: PATCH componente + reload sincrono. Errori si propagano al chiamante:
  //        il consumer (form) li mappa a banner inline / toast secondo le sue
  //        regole (es. L2 -> banner approvazione). Emit TAB_ENTITIES.PREVENTIVO:
  //        il prezzo padre cambia (trigger DB SUM componenti), altre tab che
  //        guardano lo stesso preventivo devono refreshare.
  async function update(rigaId, componenteId, payload) {
    const res = await updateRigaComponente(pid(), rigaId, componenteId, payload)
    await load(rigaId)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, pid())
    return res.data?.data
  }

  // Scopo: Soft delete + reload. Il trigger DB ricalcola il prezzo della riga
  //        padre come SUM residuo: il consumer ricarica anche le righe del
  //        preventivo per riflettere il nuovo prezzo padre.
  async function remove(rigaId, componenteId) {
    const res = await deleteRigaComponente(pid(), rigaId, componenteId)
    await load(rigaId)
    emitDataChanged(TAB_ENTITIES.PREVENTIVO, pid())
    return res.data?.data
  }

  function reset() {
    componenti.value = []
    currentRigaId.value = null
    _token++ // invalidate any in-flight load
  }

  return { componenti, loading, currentRigaId, load, update, remove, reset }
}

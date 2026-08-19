// Scopo: Fetch unica della situazione merce di un documento, condivisa dai due
// consumatori della stessa risposta: la barra `SituazioneMerceBar` (il
// riassunto in testata) e `SituazioneMerceContenuto` (il dettaglio in dialog).
//
// PERCHE' una sorgente sola — e qui pesa piu' che altrove: il riassunto dice
// «8 da accreditare» e la dialog elenca le righe che fanno quegli 8. Due query
// diverse potrebbero divergere, e un totale che smentisce il dettaglio e' peggio
// di nessun totale. La stessa risposta alimenta entrambi per costruzione.
// Stesso ragionamento (e stessa forma) di `useDocumentoPassaggi`.
//
// ⚠️ Su errore `loaded` resta false, ed e' la parte che conta: il §5.2 del
// brief pannello chiede che «tutto regolare» sia VISIBILMENTE diverso da «non
// ancora calcolato». Senza questo flag la barra mostrerebbe «nessuna pendenza»
// su dati mai arrivati — un vuoto positivo su un fallimento, cioe' la bugia
// piu' facile da raccontare in una schermata di riepilogo.
import { computed, ref, toValue, watch } from 'vue'
import { getSituazioneMerce } from './situazioneMerceApi'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useFetchVersion } from '../../../core/composables/useFetchVersion'

export function useSituazioneMerce(basePath, docId) {
  const data = ref(null)
  const loaded = ref(false)
  const { execute, loading } = useApiHandler()
  const { tag, isCurrent, invalidate } = useFetchVersion()

  // Scopo: carica la situazione del documento corrente. Il token di
  //        useFetchVersion scarta le risposte stantie sui cambi rapidi di
  //        documento (il drawer resta montato e l'id cambia sotto).
  async function load() {
    const id = toValue(docId)
    if (!id) return
    const token = tag()
    const result = await execute(() => getSituazioneMerce(toValue(basePath), id))
    if (!isCurrent(token) || result === null) return
    data.value = result
    loaded.value = true
  }

  // Cambio documento: azzera e ricarica. `immediate` copre il mount.
  watch(
    () => toValue(docId),
    (id) => {
      invalidate()
      data.value = null
      loaded.value = false
      if (id) load()
    },
    { immediate: true },
  )

  // Sezioni sempre presenti come array: il template itera senza guardie, e un
  // payload parziale non fa esplodere il rendering. Array COSTRUITI qui, non
  // presi da un default modulo-level: un oggetto condiviso fra tutte le
  // istanze e' un'aliasing silenzioso — basta che un consumer un giorno ordini
  // o muti «la sua» lista vuota perche' la mutazione viaggi fra documenti.
  const sezioni = computed(() => {
    const d = data.value ?? {}
    return {
      // ⚠️ `contesto` si propaga NUDO, senza ripiego: e' il campo che dice quale
      // lista e' il saldo del documento, e un default inventato qui sarebbe un
      // numero sbagliato invece di un avviso (vedi `_righeDelConto`).
      contesto: d.contesto ?? null,
      righe_ordine: d.righe_ordine ?? [],
      partite: d.partite ?? [],
      accrediti: d.accrediti ?? [],
      riconsegne: d.riconsegne ?? [],
    }
  })

  return { data, sezioni, loaded, loading, reload: load }
}

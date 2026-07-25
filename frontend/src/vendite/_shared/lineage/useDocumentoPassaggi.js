// Scopo: Fetch unica dei "passaggi" (genealogia/lineage) di un documento
// vendite, condivisa dai due consumatori della stessa risposta (regola del 2,
// 2026-07-25): la barra `DocumentoCollegamentiBar` (chip tipizzati dei
// collegamenti diretti) e il contenuto `LineagePassaggiContenuto` (grafo
// completo, in dialog o inline nei drawer commessa).
//
// PERCHE' una sorgente sola: i chip dicono "2 DDT · 1 Reso" e la dialog mostra
// gli stessi documenti. Se i due numeri venissero da query diverse potrebbero
// divergere (una fresca, una stantia) — e un contatore che smentisce il
// dettaglio è peggio di nessun contatore. Qui la stessa risposta alimenta
// entrambi per costruzione.
//
// Fetch EAGER (all'apertura del drawer, non all'expand del vecchio pannello):
// i chip devono poter segnalare PRIMA che l'utente chieda i dettagli. Costo
// misurato sul grafo dev: ~11 ms la direzione avanti, ~20 ms entrambe — rumore
// rispetto a detail+righe+indirizzi che il drawer già carica.
//
// Config: `basePath` (path lista del dominio, es. '/vendite/ordini') e `docId`
// (ref/getter della pk di dominio; null in CREATE → nessuna fetch).
import { ref, toValue, watch } from 'vue'
import { getPassaggi } from './lineageApi'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useFetchVersion } from '../../../core/composables/useFetchVersion'

export function useDocumentoPassaggi(basePath, docId) {
  const data = ref(null)
  const loaded = ref(false)
  const { execute, loading } = useApiHandler()
  const { tag, isCurrent, invalidate } = useFetchVersion()

  // Scopo: carica i passaggi del documento corrente. useApiHandler gestisce
  //        errori/toast; il token useFetchVersion scarta le risposte stantie
  //        sui cambi rapidi di documento. Su errore `loaded` resta false: i
  //        chip non mostrano mai "nessun collegamento" su dati mai arrivati
  //        (sarebbe un vuoto positivo su un fallimento).
  async function load() {
    const id = toValue(docId)
    if (!id) return
    const token = tag()
    const result = await execute(() => getPassaggi(toValue(basePath), id))
    if (!isCurrent(token) || result === null) return
    data.value = result
    loaded.value = true
  }

  // Cambio documento: azzera e ricarica. `immediate` copre il mount (il
  // contenuto dei drawer si smonta alla chiusura → riapertura = dati freschi).
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

  return { data, loaded, loading, reload: load }
}

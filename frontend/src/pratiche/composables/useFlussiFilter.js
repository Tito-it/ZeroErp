// Scopo: Composable per separare flussi in "da fare" e "completati".
// Logica centralizzata usata sia da PraticaFlussiPanel che da PraticaFlussiTab.
import { computed } from 'vue'
import { STATO_FLUSSO } from '../../core/constants'

const STATI_DA_FARE = [
  STATO_FLUSSO.DA_ESEGUIRE,
  STATO_FLUSSO.IN_CORSO,
  STATO_FLUSSO.SOSPESO,
  STATO_FLUSSO.ERRORE,
]
const STATI_COMPLETATI = [
  STATO_FLUSSO.COMPLETATO,
  STATO_FLUSSO.ANNULLATO,
]

/**
 * @param {import('vue').Ref<Array>} flussiRef - ref/computed con la lista flussi
 * @returns {{ flussiDaFare: ComputedRef, flussiCompletati: ComputedRef }}
 */
export function useFlussiFilter(flussiRef) {
  const flussiDaFare = computed(() =>
    flussiRef.value.filter(f => STATI_DA_FARE.includes(f.stato_codice_interno))
  )
  const flussiCompletati = computed(() =>
    flussiRef.value.filter(f => STATI_COMPLETATI.includes(f.stato_codice_interno))
  )
  return { flussiDaFare, flussiCompletati }
}

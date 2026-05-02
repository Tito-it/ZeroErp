// Scopo: Risolve l'id locale dell'utility di default a partire dal parametro
// `DEFAULT_UTILITY` (config.parameters), che stocca un codice_interno stabile
// (es. ENERGIA, GAS, IDRICO, FONIA) — non un id numerico.
//
// Il refactor 2026-05-02 (framework FK-surrogata config.parameter_fk_surrogate)
// ha rinominato DEFAULT_UTILITY_ID -> DEFAULT_UTILITY e migrato il
// default_value da id a codice_interno, applicando la convenzione generale
// "tabelle con codice_interno -> riferiti per codice_interno, non per id"
// (linee-guida-sql §6b). Questo composable nasconde la risoluzione ai drawer.
//
// Implementazione: legge il parametro dal `useParametersStore` (cache
// condivisa, single-flight, invalidation reattiva) e lo incrocia col lookup
// utilities-per-emittente per matchare codice_interno → id.
//
// Uso:
//   const { id: defaultUtilityId, load } = useUtilityDefaultId({ ruolo: 'CL' })
//   await load()
//   form.utility_id = defaultUtilityId.value  // id risolto, oppure null

import { ref, computed } from 'vue'
import { useParametersStore } from '../../stores/parameters'
import { lookupUtilitiesPerEmittente } from '../apiCore'

const PARAM_CODE = 'DEFAULT_UTILITY'

export function useUtilityDefaultId({ ruolo = null } = {}) {
  const store = useParametersStore()
  const utilities = ref([])
  // utilitiesFetched: la lookup utilities cambia raramente (non ha
  // invalidation), una sola fetch per istanza composable. Invece il
  // parametro DEFAULT_UTILITY puo' essere invalidato dallo store (override
  // admin via cross-tab broadcast): la sua "freshness" e' sempre derivata
  // da `store.has(PARAM_CODE)`, non dal flag locale.
  const utilitiesFetched = ref(false)
  let inFlight = null

  async function load() {
    if (inFlight) return inFlight
    // Short-circuit: parametro gia' in cache E utilities gia' caricate.
    // Se lo store ha invalidato il parametro (es. broadcast cross-tab),
    // store.has() ritorna false e procediamo al refetch.
    if (store.has(PARAM_CODE) && utilitiesFetched.value) return
    inFlight = (async () => {
      try {
        await store.ensure([PARAM_CODE])
        const codiceInterno = store.get(PARAM_CODE)
        if (codiceInterno && !utilitiesFetched.value) {
          const res = await lookupUtilitiesPerEmittente(ruolo)
          utilities.value = res.data?.data?.results || []
          utilitiesFetched.value = true
        }
      } catch {
        // Fallisce silente: il drawer parte con utility vuota e l'operatore
        // puo' selezionare manualmente.
      } finally {
        inFlight = null
      }
    })()
    return inFlight
  }

  // id locale risolto matchando codice_interno (dallo store, reattivo)
  // contro la lookup utilities. Reattivo: se lo store invalida il code
  // dopo un setOverride, il computed si aggiorna senza ulteriori azioni.
  const id = computed(() => {
    const codiceInterno = store.get(PARAM_CODE)
    if (!codiceInterno) return null
    const match = utilities.value.find((u) => u.codice_interno === codiceInterno)
    return match?.id ?? null
  })

  const codiceInterno = computed(() => store.get(PARAM_CODE))

  return { id, codiceInterno, load }
}

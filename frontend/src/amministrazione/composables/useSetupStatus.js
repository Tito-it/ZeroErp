// Scopo: Composable per caricare il setup status del refactor
// operatore-emittenti dall'endpoint /amm-software/setup-status/.
// Restituisce i 5 contatori usati dal banner UI "operatori non assegnati"
// e dalla logica di transizione (decisione D1 del WIP).
//
// Uso (in componente admin):
//   const { status, loading, load, hasOperatoriNonAssegnati } = useSetupStatus()
//   onMounted(load)
//   <OperatoriNonAssegnatiBanner v-if="hasOperatoriNonAssegnati" :count="status.operatori_non_assegnati" />

import { ref, computed } from 'vue'
import { getSetupStatus } from '../api/amministrazione'

/**
 * @returns {{
 *   status: Ref<Object>,
 *   loading: Ref<boolean>,
 *   loaded: Ref<boolean>,
 *   load: Function,
 *   hasOperatoriNonAssegnati: ComputedRef<boolean>,
 *   hasEmittenti: ComputedRef<boolean>
 * }}
 */
export function useSetupStatus() {
  const status = ref({
    emittenti_attivi: 0,
    operatori_totali: 0,
    operatori_assegnati: 0,
    operatori_admin_globali: 0,
    operatori_non_assegnati: 0,
  })
  const loading = ref(false)
  const loaded = ref(false)

  async function load(force = false) {
    if (loaded.value && !force) return
    loading.value = true
    try {
      const res = await getSetupStatus()
      status.value = res.data.data || status.value
      loaded.value = true
    } catch (err) {
      // Il setup status non e' bloccante: il banner non viene mostrato.
      // Loggiamo comunque per non mascherare endpoint rotti — il banner
      // serve a segnalare anomalie, non puo' essere lui stesso silente.
      // eslint-disable-next-line no-console
      console.warn('useSetupStatus: load failed', err)
    } finally {
      loading.value = false
    }
  }

  // Banner attivo se nel sistema esistono EF e ci sono ancora operatori
  // non assegnati (decisione Q4: "advise, don't enforce" durante transizione).
  const hasOperatoriNonAssegnati = computed(
    () => status.value.emittenti_attivi > 0 && status.value.operatori_non_assegnati > 0
  )

  const hasEmittenti = computed(() => status.value.emittenti_attivi > 0)

  return {
    status,
    loading,
    loaded,
    load,
    hasOperatoriNonAssegnati,
    hasEmittenti,
  }
}

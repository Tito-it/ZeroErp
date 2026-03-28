// Scopo: Composable per gestione campo codice in base a config.sistema_codici.
// Verifica se il codice e' generato automaticamente dal DB (usa_sequenza=true)
// o deve essere inserito manualmente dall'operatore.
//
// Uso:
//   const codice = useCodiceField('anagrafiche', 'fornitori')
//   codice.load()  // chiama API
//   codice.isAuto  // ref<boolean> — true se generato dal DB
//   codice.isEditable // computed — true se l'operatore deve digitare il codice
//   codice.prefisso // ref<string> — prefisso configurato (es. 'FRN-')

import { ref, computed } from 'vue'
import { lookupSistemaCodici } from '../apiCore'

export function useCodiceField(schema, tabella, colonna = 'codice') {
  const isAuto = ref(false)
  const prefisso = ref('')
  const separatore = ref('')
  const lunghezzaNumero = ref(0)
  const loaded = ref(false)

  // Scopo: Carica configurazione sistema codici dal backend.
  async function load() {
    try {
      const res = await lookupSistemaCodici(schema, tabella, colonna)
      const data = res.data?.data
      isAuto.value = !!data?.auto
      prefisso.value = data?.prefisso || ''
      separatore.value = data?.separatore || ''
      lunghezzaNumero.value = data?.lunghezza_numero || 0
    } catch {
      isAuto.value = false
    }
    loaded.value = true
  }

  // True se l'operatore deve inserire il codice manualmente
  const isEditable = computed(() => loaded.value && !isAuto.value)

  return {
    isAuto,
    isEditable,
    prefisso,
    separatore,
    lunghezzaNumero,
    loaded,
    load,
  }
}

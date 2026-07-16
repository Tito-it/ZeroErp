// Scopo: BB "toggle selezione con righe non selezionabili" (estratto
// 2026-07-15, ok Tid — uniforma i 4 pannelli-azione con selezione multipla:
// smistamento preventivi, evasione ordine, crea-reso DDT, ri-spedizione reso).
//
// PrimeVue 4 non ha più un predicato per-riga di selezionabilità sul
// DataTable (`isDataSelectable` rimosso): la Column selectionMode="multiple"
// rende OGNI riga spuntabile, incluse quelle già lavorate (smistate/evase/
// esaurite). Prima ogni pannello arrangiava un workaround diverso (setter che
// "rimbalza" nei preventivi, nessun guard nei pannelli BB). Qui vive la
// macchina unica: i template usano una Column checkbox CUSTOM il cui
// `:disabled` viene da `isSelectable`, e il guard di `toggleRow` è la difesa
// di coerenza (una riga non selezionabile non entra MAI in `selected`,
// qualunque cosa faccia il template).
//
// Config (tutti reattivi):
// - selected: Ref<row[]> — la selezione corrente (posseduta dal caller/BB).
// - selezionabili: Ref|Computed<row[]> — le sole righe lavorabili (residuo>0,
//   stato RESIDUA, ...): fuori da qui una riga non è né spuntabile né spuntata.
// - rowKey: chiave riga (default 'id').
import { computed } from 'vue'

export function useSelezioneToggle({ selected, selezionabili, rowKey = 'id' }) {
  const selectableKeys = computed(
    () => new Set(selezionabili.value.map(r => r[rowKey])),
  )
  const selectedKeys = computed(
    () => new Set(selected.value.map(r => r[rowKey])),
  )

  function isSelectable(row) {
    return selectableKeys.value.has(row[rowKey])
  }

  function isSelected(row) {
    return selectedKeys.value.has(row[rowKey])
  }

  // Guard: una riga non selezionabile non entra in selezione (no-op), anche
  // se il template dimenticasse il :disabled.
  function toggleRow(row) {
    if (!isSelectable(row)) return
    selected.value = isSelected(row)
      ? selected.value.filter(r => r[rowKey] !== row[rowKey])
      : [...selected.value, row]
  }

  // Header "seleziona tutto": riferito alle SOLE selezionabili.
  const allSelected = computed(
    () => selezionabili.value.length > 0
      && selezionabili.value.every(r => selectedKeys.value.has(r[rowKey])),
  )

  // Selezione parziale: alimenta lo stato `indeterminate` della checkbox
  // header (informazione che il selectionMode nativo dava e la Column custom
  // deve ristabilire).
  const anySelected = computed(
    () => selected.value.length > 0 && !allSelected.value,
  )

  function toggleAll() {
    selected.value = allSelected.value ? [] : [...selezionabili.value]
  }

  return { isSelectable, isSelected, toggleRow, toggleAll, allSelected, anySelected }
}

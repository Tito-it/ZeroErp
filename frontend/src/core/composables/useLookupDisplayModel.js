// Scopo: normalizza il modelValue di un AutoComplete server-side garantendo la
//        chiave `_display` letta da `optionLabel="_display"` (B6 2026-06-05,
//        regola del 2). Quando l'oggetto arriva da un restore in EDIT (lookup
//        by-id, auto-save bozza, loadDetail) e' ricco ma privo di `_display`
//        (calcolato solo nel `transform` delle suggestions): senza questa
//        normalizzazione AutoComplete cade sul toString → "[object Object]".
//
// Il `buildDisplay` resta caller-side (campi diversi per ogni lookup): il
// composable copre solo il pattern di re-iniezione, identico byte-per-byte fra
// BillingAccountLookup / IstanzaUtilityLookup / ArticoloLookup.
//
// Uso:
//   const displayedModel = useLookupDisplayModel(() => props.modelValue, buildDisplay)
//   <AutoComplete :modelValue="displayedModel" optionLabel="_display" ... />

import { computed } from 'vue'

export function useLookupDisplayModel(getModelValue, buildDisplay) {
  return computed(() => {
    const v = getModelValue()
    if (!v) return null
    if (v._display) return v
    return { ...v, _display: buildDisplay(v) }
  })
}

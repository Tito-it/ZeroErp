// Scopo: handler standard di chiusura drawer. Centralizza il pattern
// `emit('update:visible', false)` ripetuto in ogni drawer di progetto
// (vedi standard frontend §"Componente FormFooter").
//
// Uso base:
//   const onClose = useDrawerClose(emit)
//   // template: <FormFooter close-only @cancel="onClose" />
//
// Uso con evento secondario (alcuni drawer notificano il parent della
// chiusura per reset/cleanup oltre al toggle di `visible`):
//   const onClose = useDrawerClose(emit, 'cancelled')   // pratiche, anagrafiche, ecc.
//   const onClose = useDrawerClose(emit, 'annullato')   // SoggettoResolver
//
// Nota: il drawer DEVE dichiarare nel `defineEmits` sia `update:visible`
// sia l'eventuale evento secondario, altrimenti Vue emette un warning in
// dev. Il composable non lo verifica (impossibile sapere a runtime quali
// eventi siano dichiarati nel componente chiamante).

// Scopo: ritorna una funzione `onClose()` legata all'`emit` del componente.
//        Se `extraEvent` e' valorizzato, viene emesso subito dopo
//        `update:visible=false` come notifica al parent.
export function useDrawerClose(emit, extraEvent = null) {
  return () => {
    emit('update:visible', false)
    if (extraEvent) emit(extraEvent)
  }
}

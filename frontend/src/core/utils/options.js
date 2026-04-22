// Factory di options riutilizzabili per Select/Dropdown PrimeVue.
// Scopo: centralizzare i pattern ripetuti (bool tri-state, ecc.) per evitare
// duplicazione in 6+ SearchTable admin (pattern rilevato su listini v5).

// Scopo: Ritorna le 3 opzioni standard per un Select "tri-state bool"
// (tutti, si, no). Passare la funzione t di vue-i18n.
export function buildBoolOptions(t) {
  return [
    { value: null, label: t('common.all') },
    { value: true, label: t('common.yes') },
    { value: false, label: t('common.no') }
  ]
}

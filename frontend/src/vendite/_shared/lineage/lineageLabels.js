// Decodifiche i18n del lineage documenti, fail-visible (codice grezzo se la
// chiave manca — vocabolario estensibile DB-side, pattern labelOrCode).
// Estratto (regola del 2): era duplicato in LineagePassaggiPanel e
// LineageFrontieraChip.
import { labelOrCode } from '../../../core/utils/i18nLabel'

// Scopo: etichetta del tipo sorgente (config.sorgenti.codice_interno) per
// tappe/chip lineage. Firma (t, te) di useI18n come dashAreaLabel/dashFaseLabel.
export function lineageTipoLabel(t, te, codice) {
  return labelOrCode(t, te, `lineage.tipo_${String(codice ?? '').toLowerCase()}`, codice)
}

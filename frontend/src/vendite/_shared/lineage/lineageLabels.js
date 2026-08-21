// Decodifiche i18n del lineage documenti, fail-visible (codice grezzo se la
// chiave manca — vocabolario estensibile DB-side, pattern labelOrCode).
// Estratto (regola del 2): era duplicato in LineagePassaggiPanel e
// LineageFrontieraChip.
import { labelOrCode } from '../../../core/utils/i18nLabel'

// Scopo: etichetta del tipo sorgente (config.sorgenti.codice_interno) per
// tappe/chip lineage. Firma (t, te) di useI18n come dashAreaLabel/dashFaseLabel.
export function lineageTipoLabel(t, te, codice) {
  return labelOrCode(t, te, `vendite.lineage.tipo_${String(codice ?? '').toLowerCase()}`, codice)
}

// Scopo: ⭐ L'ETICHETTA DEL DOCUMENTO, che non e' sempre quella del suo TIPO.
// Fattura e nota di credito sono lo stesso `config.sorgenti.codice_interno`
// (FATTURA) e si distinguono solo per la NATURA: senza questa regola una
// commessa che ha generato entrambi mostra due volte «Fattura», e l'operatore
// non ha modo di sapere quale sia quale (rilievo in-app 2026-08-20, natura
// esposta dal DB il 2026-08-21).
//
// La natura, quando c'e', VINCE sul tipo — anche quando dice «FATTURA»: cosi'
// la regola e' una sola e non un caso speciale per la nota di credito. Per
// tutti i documenti non fiscali la natura e' NULL e si ricade sul tipo.
export function lineageDocumentoLabel(t, te, tipoCodice, naturaCodice) {
  if (naturaCodice) {
    return labelOrCode(
      t, te,
      `vendite.lineage.natura_${String(naturaCodice).toLowerCase()}`,
      naturaCodice,
    )
  }
  return lineageTipoLabel(t, te, tipoCodice)
}

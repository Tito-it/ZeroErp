// Helper puri per le righe con componenti BoM aggregati. La shape
// `{ is_composito, componenti }` arriva dalle funzioni di preview vendite
// (`fn_contratto_righe_preview`, `fn_preview_riga_componenti`): `componenti`
// e' un `jsonb_agg` dei figli. Estratti dalla "regola del 2" (2026-05-31):
// erano duplicati identici in `ContrattoRigheDrawer` e `OffertaEccezioniDrawer`.
// Funzioni pure (nessuno stato reattivo) -> util, non composable.
import { coerceJsonbToArray } from '../../../core/utils/meta'

// Normalizza il `jsonb_agg` dei figli (`row.componenti`) ad array. Coerce
// difensivo: psycopg puo' restituire il JSONB come STRINGA JSON invece che
// array gia' deserializzato — in quel caso `Array.isArray` fallirebbe e
// l'expander non comparirebbe pur essendoci i figli. `coerceJsonbToArray`
// normalizza stringa->array (pass-through se gia' array).
export function rowComponenti(row) {
  return coerceJsonbToArray(row?.componenti)
}

// Vero se la riga e' un bundle composito con almeno un componente figlio.
// Discrimina il chevron expander: visibile solo sui bundle.
export function hasBundleComponenti(row) {
  return row?.is_composito === true && rowComponenti(row).length > 0
}

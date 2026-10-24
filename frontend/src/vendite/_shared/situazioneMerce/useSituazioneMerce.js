// Scopo: Fetch unica della situazione merce di un documento, condivisa dai due
// consumatori della stessa risposta: la barra `SituazioneMerceBar` (il
// riassunto in testata) e `SituazioneMerceContenuto` (il dettaglio in dialog).
//
// PERCHE' una sorgente sola — e qui pesa piu' che altrove: il riassunto dice
// «8 da accreditare» e la dialog elenca le righe che fanno quegli 8. Due query
// diverse potrebbero divergere, e un totale che smentisce il dettaglio e' peggio
// di nessun totale. La stessa risposta alimenta entrambi per costruzione.
// Stesso ragionamento (e stessa forma) di `useDocumentoPassaggi`.
//
// ⚠️ Su errore `loaded` resta false, ed e' la parte che conta: il §5.2 del
// brief pannello chiede che «tutto regolare» sia VISIBILMENTE diverso da «non
// ancora calcolato». Senza questo flag la barra mostrerebbe «nessuna pendenza»
// su dati mai arrivati — un vuoto positivo su un fallimento, cioe' la bugia
// piu' facile da raccontare in una schermata di riepilogo.
//
// Il QUANDO leggere sta in `useLetturaDocumento` (2026-10-13, regola del 2 con
// `useDocumentoPassaggi`): con `versione` (il dettaglio del drawer ospite) la
// situazione si rilegge a ogni rilettura del drawer — evasione, reso, annullo,
// emissione — senza che il drawer se lo debba ricordare.
import { computed, toValue } from 'vue'
import { getSituazioneMerce } from './situazioneMerceApi'
import { useLetturaDocumento } from '../../../core/composables/useLetturaDocumento'

export function useSituazioneMerce(basePath, docId, versione) {
  const { dati: data, caricati: loaded, loading, rileggi } = useLetturaDocumento(
    (id) => getSituazioneMerce(toValue(basePath), id),
    { docId, versione },
  )

  // Sezioni sempre presenti come array: il template itera senza guardie, e un
  // payload parziale non fa esplodere il rendering. Array COSTRUITI qui, non
  // presi da un default modulo-level: un oggetto condiviso fra tutte le
  // istanze e' un'aliasing silenzioso — basta che un consumer un giorno ordini
  // o muti «la sua» lista vuota perche' la mutazione viaggi fra documenti.
  const sezioni = computed(() => {
    const d = data.value ?? {}
    return {
      // ⚠️ `contesto` si propaga NUDO, senza ripiego: e' il campo che dice quale
      // lista e' il saldo del documento, e un default inventato qui sarebbe un
      // numero sbagliato invece di un avviso (vedi `_righeDelConto`).
      contesto: d.contesto ?? null,
      righe_ordine: d.righe_ordine ?? [],
      partite: d.partite ?? [],
      accrediti: d.accrediti ?? [],
      riconsegne: d.riconsegne ?? [],
    }
  })

  return { data, sezioni, loaded, loading, reload: rileggi }
}

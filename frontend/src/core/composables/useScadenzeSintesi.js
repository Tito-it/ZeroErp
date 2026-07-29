// Scopo: building block "sintesi di un piano rate" — quale scadenza mostrare
//        quando un documento ne ha più di una, e con che conteggio.
//
// PERCHE' ESISTE. La domanda «fra cinque rate, quale data metto nella scheda?»
// e' una decisione di dominio, non una riga di template: se vive nei componenti,
// il drawer, la lista e il portale finiscono per dare risposte diverse sullo
// stesso documento. Qui c'e' una regola sola.
//
// ⚠️ LA SEMANTICA E' TEMPORALE, NON DI PAGAMENTO. La "prossima" e' la prossima
// **per data**, non «la prossima da incassare»: quest'ultima NON e' calcolabile
// nel modello attuale, perche' gli incassi (`pagamenti.vendite_movimenti`) sono
// legati alla FATTURA e non alla singola rata (`vendite.fatture_scadenze` non ha
// stato di pagamento, e non esiste una FK incasso -> scadenza). Il residuo si
// conosce solo per fattura, via `pagamenti.fn_get_saldo_fattura`.
// Conseguenza operativa: NON derivare da qui uno stato "scaduta/insoluta" ne'
// una colorazione di sollecito — su una fattura gia' incassata sarebbe falsa.
// Il flag `tuttePassate` dice solo che nessuna rata cade nel futuro.

import { computed, unref } from 'vue'

import { toDateString } from '../utils/date'

// Normalizza a 'YYYY-MM-DD': il BE manda stringhe ISO (DjangoJSONEncoder), ma
// il BB accetta anche Date per non obbligare il chiamante a convertire.
// `toDateString` usa l'ora locale (mai toISOString: shifta il giorno).
function _iso(value) {
  if (!value) return null
  if (typeof value === 'string') return value.substring(0, 10)
  return toDateString(value)
}

/**
 * Regola pura: da un piano rate alla sua sintesi.
 *
 * Scelta della rata da mostrare:
 *  - la prima con `data_scadenza >= oggi` (la prossima in ordine di tempo);
 *  - se sono tutte passate, l'ULTIMA in ordine di data — quella che descrive
 *    lo stato corrente del piano, non la piu' vecchia dimenticata a inizio lista.
 *
 * @param {Array} scadenze - righe `{numero_rata, data_scadenza, importo}`
 * @param {string|Date} [oggi] - override per i test; default = data odierna locale
 * @returns {{prossima: object|null, indice: number, count: number,
 *            totale: number, tuttePassate: boolean, rate: Array}}
 *          `indice` e' 1-based e serve al display "2/3" (0 se nessuna rata).
 */
export function sintesiScadenze(scadenze, oggi = undefined) {
  // Solo righe con una data utilizzabile: una rata senza data non e' collocabile
  // nel piano e falserebbe sia il conteggio sia la scelta della prossima.
  const list = (scadenze || []).filter((s) => _iso(s?.data_scadenza))
  const vuota = {
    prossima: null, indice: 0, count: 0, totale: 0, tuttePassate: false, rate: [],
  }
  if (!list.length) return vuota

  // Ordine per data e non per `numero_rata`: la data e' cio' su cui la regola
  // decide. Confronto fra stringhe ISO — lessicografico == cronologico.
  const rate = [...list].sort(
    (a, b) => _iso(a.data_scadenza).localeCompare(_iso(b.data_scadenza)),
  )
  const oggiIso = _iso(oggi) ?? toDateString(new Date())
  const idx = rate.findIndex((s) => _iso(s.data_scadenza) >= oggiIso)
  const tuttePassate = idx === -1
  const posizione = tuttePassate ? rate.length - 1 : idx

  return {
    prossima: rate[posizione],
    indice: posizione + 1,
    count: rate.length,
    totale: rate.reduce((acc, s) => acc + Number(s.importo || 0), 0),
    tuttePassate,
    rate,
  }
}

/**
 * Wrapper reattivo della regola. `scadenze` puo' essere array, ref o computed:
 * viene dereffato al ricalcolo, così il padre puo' sostituire il piano rate
 * (cambio documento) senza reistanziare nulla.
 *
 * @param {import('vue').Ref<Array>|Array} scadenze
 * @returns {import('vue').ComputedRef} sintesi (vedi `sintesiScadenze`)
 */
export function useScadenzeSintesi(scadenze) {
  return computed(() => sintesiScadenze(unref(scadenze)))
}

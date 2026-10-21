// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Un lookup del catalogo che porta l'ETICHETTA riga per riga
//        (`etichetta_key`, l'indirizzo i18n che il DB dichiara — come
//        `config.tipi_entita`, `config.registri_giornale`,
//        `config.eventi_dominio`), reso fail-visible con `labelOrCode`:
//        la cache condivisa per chiave, l'etichetta di un codice gia' in
//        riga, e le opzioni di una tendina con la voce «tutti» in testa.
// Note: Estratto 2026-09-19 (regola del 2, ok Tid): le due tendine del
//        giornale trasversale — «Entita'» (lookup dedicato) e «Registro»
//        (lookup generico specializzato) — erano la stessa forma scritta due
//        volte nella stessa view: `useGlobalLookup` + una `find` sul codice
//        + `labelOrCode` sulla chiave + le opzioni calcolate.
//        ⚠️ NON e' un `<LookupSelect>`: quello rende `descrizione` (un
//        testo italiano del seed), qui si rende l'INDIRIZZO i18n che la riga
//        porta — la differenza fra un testo e una traduzione.
//        ⚠️ Il ripiego e' il CODICE GREZZO, mai una cella vuota ne' il path
//        della chiave: un codice non piu' fra i vivi (una riga vecchia del
//        diario su un registro ritirato) si legge lo stesso.
// ------------------------------------------------------------

import { computed, unref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGlobalLookup } from './useGlobalLookup'
import { useLookupCodici } from './useLookupCodici'
import { labelOrCode } from '../utils/i18nLabel'

/**
 * Lookup del catalogo con l'etichetta dichiarata dal DB.
 *
 * @param {Object} sorgente - UNA delle due forme:
 *   - `{ rel, includiObsoleti?, limit? }` → il lookup GENERICO di quel
 *     `rel`, chiave e fetch composte da `useLookupCodici` (stessa entry di
 *     un `<LookupSelect rel>` sullo stesso insieme, per costruzione);
 *   - `{ chiave, fetcher, transform? }` → un lookup DEDICATO (es.
 *     `lookupTipiEntita`) nella cache di `useGlobalLookup`. ⚠️ Stessa chiave
 *     = stesso insieme, o il primo montato vince in silenzio.
 * @param {Object} opzioni
 * @param {string} opzioni.campoCodice - il campo che porta il codice della
 *   riga: `codice` (default) o `codice_interno` — la chiave STABILE del
 *   lookup generico, quella che il backend valida.
 * @param {string} opzioni.campoEtichettaKey - il campo con l'indirizzo i18n
 *   (default `etichetta_key`)
 * @param {string|Function|import('vue').Ref} opzioni.tutti - l'etichetta
 *   della voce «tutti» (`value: null`) in testa alle opzioni; assente =
 *   nessuna voce. Una funzione (`() => t('…')`) resta reattiva al locale.
 * @param {boolean} opzioni.immediate - carica al mount (default true)
 * @returns {{ items, loading, loaded, error, load, reload, etichetta, opzioni }}
 */
export function useLookupEtichettato(sorgente, {
  campoCodice = 'codice',
  campoEtichettaKey = 'etichetta_key',
  tutti = null,
  immediate = true,
} = {}) {
  const { t, te } = useI18n()
  if (import.meta.env.DEV && !sorgente?.rel === !sorgente?.fetcher) {
    console.warn('[useLookupEtichettato] passare esattamente uno tra `rel` e `chiave`+`fetcher`.')
  }
  const lookup = sorgente?.rel
    ? useLookupCodici(sorgente.rel, {
        includiObsoleti: sorgente.includiObsoleti,
        limit: sorgente.limit,
        immediate,
      })
    : useGlobalLookup(sorgente.chiave, sorgente.fetcher, {
        immediate,
        ...(sorgente.transform ? { transform: sorgente.transform } : {}),
      })

  // L'indice per codice, ricalcolato quando arriva il catalogo: `etichetta`
  // gira per cella di una lista e per opzione di una tendina, e una `find`
  // lineare a ogni chiamata costerebbe il quadrato del catalogo.
  const perCodice = computed(() => new Map(
    (lookup.items.value || []).filter(Boolean).map((r) => [r[campoCodice], r]),
  ))

  // Scopo: l'etichetta di un codice — dalla riga del catalogo che porta la
  //        chiave dichiarata dal DB; il codice grezzo se la riga non c'e'
  //        (fail-visible). Reattiva al locale perche' `t`/`te` sono quelli
  //        del componente che monta.
  function etichetta(codice) {
    if (codice == null) return ''
    const riga = perCodice.value.get(codice)
    return riga ? labelOrCode(t, te, riga[campoEtichettaKey], codice) : codice
  }

  // Scopo: risolve l'etichetta «tutti» in ogni forma ammessa.
  function etichettaTutti() {
    const v = typeof tutti === 'function' ? tutti() : unref(tutti)
    return v ?? null
  }

  // Le opzioni di una tendina `{ value, label }`: la voce «tutti» (se chiesta)
  // piu' il catalogo, etichettato.
  const opzioni = computed(() => {
    const testa = etichettaTutti()
    return [
      ...(testa != null ? [{ value: null, label: testa }] : []),
      ...(lookup.items.value || []).map((r) => ({
        value: r[campoCodice],
        label: etichetta(r[campoCodice]),
      })),
    ]
  })

  return { ...lookup, etichetta, opzioni }
}

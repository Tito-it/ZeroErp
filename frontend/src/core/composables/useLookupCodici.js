// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Il lookup GENERICO (`GET /core/lookup/codici/?rel=…`) nella cache
//        condivisa di `useGlobalLookup`: la chiave e la fetch di un `rel`
//        composte in UN posto, cosi' due consumatori dello stesso insieme
//        (un `<LookupSelect>` e una preselezione, una home e un drawer)
//        condividono la stessa entry per costruzione — non perche' hanno
//        ricopiato la stessa stringa.
// Note: Estratto 2026-09-19 (regola del 2, rilettura critica): la coppia
//        «`<rel>::no-obsoleti`» + `() => lookupCodici(rel, { page_size: 200,
//        includi_obsoleti: false })` era scritta identica in `LookupSelect`,
//        `PraticaDrawer`, `PraticheHome` e `GiornaleListView`, col `200`
//        magico in ciascuna. ⛔ La chiave e' un CONTRATTO: stessa chiave =
//        stesso insieme. Un `rel` con e senza obsoleti sono due insiemi, e
//        con la stessa chiave il primo montato vincerebbe in silenzio
//        (`feedback_estrarre_non_condividere_stato`) — per questo il
//        suffisso lo compone `chiaveLookupCodici`, e nessuno lo scrive a mano.
// ------------------------------------------------------------

import { lookupCodici } from '../apiCore'
import { useGlobalLookup } from './useGlobalLookup'

// Il cap del lookup generico (api.md §Paginazione: `limit` max 200): una
// tabella di configurazione si legge intera, in una pagina.
// ⭐ `limit` e non `page_size` dal 2026-10-21 (un dialetto solo): il backend
//    rifiuta `page_size` con un 400.
export const LOOKUP_CODICI_LIMIT = 200

// Scopo: la chiave di cache di un `rel` del lookup generico. Con gli obsoleti
//        esclusi e' un altro insieme, quindi un'altra chiave.
export function chiaveLookupCodici(rel, { includiObsoleti = true } = {}) {
  return includiObsoleti ? rel : `${rel}::no-obsoleti`
}

// Scopo: la fetch di un `rel` del lookup generico. `includi_obsoleti` viaggia
//        solo quando e' `false`: il default del backend e' «tutto», e non si
//        manda un parametro per dire il default.
export function fetchLookupCodici(rel, { includiObsoleti = true, limit = LOOKUP_CODICI_LIMIT } = {}) {
  return () => lookupCodici(rel, {
    limit,
    ...(includiObsoleti ? {} : { includi_obsoleti: false }),
  })
}

/**
 * Lookup generico di un `rel`, nella cache condivisa per chiave.
 *
 * @param {string} rel - `schema.tabella` nella lista del lookup (`config.tabelle_gestibili`)
 * @param {Object} opzioni
 * @param {boolean} opzioni.includiObsoleti - default true (tutto); `false` =
 *   la «selezione per il nuovo», senza le voci con `obsoleto_dal <= oggi`
 * @param {number} opzioni.limit - default `LOOKUP_CODICI_LIMIT`
 * @param {boolean} opzioni.immediate - carica al mount (default false, come
 *   `useGlobalLookup`)
 * @param {Function} opzioni.transform - trasforma la risposta (default:
 *   envelope `r.data.data.results`)
 * @returns lo stesso oggetto di `useGlobalLookup`
 */
export function useLookupCodici(rel, { includiObsoleti = true, limit, immediate = false, transform } = {}) {
  const lookupOptions = { immediate }
  if (transform) lookupOptions.transform = transform
  return useGlobalLookup(
    chiaveLookupCodici(rel, { includiObsoleti }),
    fetchLookupCodici(rel, { includiObsoleti, limit }),
    lookupOptions,
  )
}

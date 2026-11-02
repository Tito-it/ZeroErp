// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: L'indirizzo LIBERO nel form degli indirizzi (soggetto, cliente,
//        fornitore): i suoi campi, la FORMA che decide lo stato scelto, la
//        validazione e il payload. Una sede sola per il composable del form
//        (validazione, payload, snapshot) e per il componente (quali campi
//        mostrare).
// Note: ⭐ La regola e' del DB (guard `anagrafiche.trgfn_indirizzi_guard_forma_libera`,
//       D-2 di Tid, 2026-10-18): sempre via e stato; poi, se lo stato ha il
//       catalogo dei comuni completo (`catalogo_comuni_completo`, oggi
//       l'Italia), comune e CAP dall'elenco — e niente localita', codice
//       postale, regione; altrimenti la localita' obbligatoria, codice
//       postale, regione e sotto-localita' facoltativi. Qui la si SPECCHIA
//       perche' l'operatore veda il campo che manca prima di salvare; il
//       rifiuto vero resta del DB, col campo nel canale COLUMN.
//       ⛔ La forma si LEGGE dal flag dello stato (la tendina degli stati lo
//       porta), non si ricalcola da un codice ISO.
// ------------------------------------------------------------

// I campi dell'indirizzo libero e il loro valore vuoto. `sublocality` (frazione,
// quartiere) vale in tutte e due le forme.
export const CAMPI_LIBERO = Object.freeze({
  indirizzo_libero: '',
  stato_id: null,
  locality: '',
  postal_code: '',
  administrative_area: '',
  sublocality: '',
})

// Scopo: I campi liberi presi da `src` (form, snapshot, riga dell'API), col
//        loro vuoto dove mancano.
export function campiLiberi(src = {}) {
  const out = {}
  for (const [k, vuoto] of Object.entries(CAMPI_LIBERO)) {
    out[k] = src[k] ?? vuoto
  }
  return out
}

// Scopo: Scrive nel form reattivo i campi liberi di `src` (vuoti dove mancano).
export function assegnaCampiLiberi(form, src = {}) {
  Object.assign(form, campiLiberi(src))
}

// Scopo: La riga dello stato `statoId` nella tendina degli stati, o null.
export function statoDi(stati, statoId) {
  if (!statoId || !Array.isArray(stati)) return null
  return stati.find((s) => s.id === statoId) || null
}

// Scopo: La forma «del catalogo» (comune e CAP dall'elenco) o quella estera,
//        dal flag dello stato. Senza stato: nessuna forma da imporre.
export function isFormaCatalogo(stato) {
  return stato?.catalogo_comuni_completo === true
}

const pieno = (v) => (typeof v === 'string' ? v.trim() !== '' : v !== null && v !== undefined)

// Scopo: I campi che mancano all'indirizzo libero `dati` (form o snapshot,
//        con `comune_id` e `codice_postale_id` della parte geografica), nella
//        forma dello `stato` scelto. Stesso ordine del guard: via, stato, poi
//        i campi della forma.
export function validaLibero(dati, stato) {
  const errori = []
  if (!pieno(dati.indirizzo_libero)) errori.push('indirizzo_libero')
  // Senza stato, o con uno stato che la tendina non porta (non ancora
  // caricata, o fallita), la forma non si sa: non si indovina. Si ferma sullo
  // stato invece di chiedere la localita' a un indirizzo italiano.
  if (!dati.stato_id || !stato) {
    errori.push('stato_id')
    return errori
  }
  if (isFormaCatalogo(stato)) {
    if (!dati.comune_id) errori.push('comune_id')
    if (!dati.codice_postale_id) errori.push('codice_postale_id')
  } else if (!pieno(dati.locality)) {
    errori.push('locality')
  }
  return errori
}

const testo = (v) => (typeof v === 'string' ? v.trim() || null : v ?? null)

// Scopo: Il payload dell'indirizzo libero: via, stato e SOLO i campi della
//        forma dello stato. I campi dell'altra forma non viaggiano: il guard
//        li rifiuterebbe (`E_INDIRIZZO_CAMPO_ALTRA_FORMA`).
export function payloadLibero(dati, stato) {
  const payload = {
    indirizzo_libero: testo(dati.indirizzo_libero),
    stato_id: dati.stato_id,
    sublocality: testo(dati.sublocality),
  }
  if (isFormaCatalogo(stato)) {
    payload.comune_id = dati.comune_id ?? null
    payload.codice_postale_id = dati.codice_postale_id ?? null
  } else {
    payload.locality = testo(dati.locality)
    payload.postal_code = testo(dati.postal_code)
    payload.administrative_area = testo(dati.administrative_area)
  }
  return payload
}

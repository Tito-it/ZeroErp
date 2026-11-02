// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: ⭐ COME SI DICE UNA SCORCIATOIA A VIDEO (2026-10-04, ok Tid). La
//        forma e' una sola, «azione (tasto)» — «Chiudi (Esc)», «Salva
//        (Ctrl+S)» — quella dei programmi che l'operatore conosce gia'. La
//        usano la X di `AppDrawer` e il Salva di `FormFooter`: una scorciatoia
//        che funziona e non si dice non esiste per chi non la sa.
//
// ⭐ MULTILINGUA: anche il NOME del tasto si traduce (`common.tasti.*`), non
//    solo l'azione — la tastiera tedesca scrive «Strg», non «Ctrl». E la
//    forma «azione (tasto)» e' anch'essa una frase (`common.con_scorciatoia`):
//    una lingua puo' volerla diversa.
// ⚠️ Il tasto dipende anche dalla MACCHINA: su Mac il Salva e' ⌘S
//    (`FormFooter` accetta `metaKey`), e scrivere «Ctrl+S» li' sarebbe dire
//    un tasto che l'operatore non preme. Chiave `<CODICE>_MAC`, se c'e'.
// ⛔ Qui si DICE il tasto, non lo si aggancia: i binding restano dove sono
//    (`SHORTCUTS` per quelli globali, `FormFooter` per Ctrl+S, PrimeVue per
//    Esc). Chi aggiunge una scorciatoia mostrata aggiunge qui il codice e le
//    sue chiavi nei locales.

function suMac() {
  if (typeof navigator === 'undefined') return false
  const piattaforma = navigator.userAgentData?.platform || navigator.platform || ''
  return /mac/i.test(piattaforma)
}

// I tasti che l'interfaccia DICHIARA: il codice e' la chiave nei locales.
export const TASTO = Object.freeze({
  ESC: 'ESC',
  SALVA: 'SALVA',
  // I tasti funzione delle liste (`useScorciatoie`): il codice e' il
  // nome del tasto, ma passa lo stesso dai locales (una tastiera puo'
  // chiamarli diversamente, e la regola resta una).
  F2: 'F2',
  F4: 'F4',
  F5: 'F5',
  F6: 'F6',
  F8: 'F8',
  F9: 'F9',
})

// Scopo: il nome del tasto, tradotto; su Mac la variante `_MAC` se esiste.
//        `t`/`te` dal chiamante, per restare reattivi al cambio lingua.
export function nomeTasto(t, te, codice, mac = suMac()) {
  const chiaveMac = `common.tasti.${codice}_MAC`
  return mac && te(chiaveMac) ? t(chiaveMac) : t(`common.tasti.${codice}`)
}

// Scopo: l'etichetta «azione (tasto)», tradotta (`common.con_scorciatoia`).
export function conScorciatoia(t, te, azione, codice, mac = suMac()) {
  return t('common.con_scorciatoia', { azione, tasto: nomeTasto(t, te, codice, mac) })
}

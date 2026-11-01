// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: RACCOGLIE in un oggetto piatto i valori dei form inline di
//        un'anagrafica — contatto, indirizzo, dati societari — per il
//        confronto «modifiche non salvate» del BB `useDrawerFormPreserve`.
//        Estratto il 2026-09-26 (regola del 2, ok Tid): lo stesso pezzo
//        serviva a ClienteDrawer, FornitoreDrawer, SoggettoDrawer e
//        IndirizziSoggettoDrawer.
// Note: ⭐ Oggetto PIATTO, con le chiavi prefissate (`contatto.email`): il BB
//       confronta campo per campo con la sua regola dei vuoti (null = '' =
//       spazi); un oggetto annidato si confronterebbe per JSON, e un campo
//       ripulito da '' a null risulterebbe una modifica.
//       ⚠️ Dell'indirizzo NON si raccolgono:
//       - `tipo_indirizzo_codice_interno` e `_isLibera`: dicono QUALE tipo e in che
//         modalita' si sta compilando, non cosa si salva. La matrice li scrive
//         da se' quando arriva (in modo asincrono, dopo l'apertura), e da soli
//         non salvano nulla. I tipi gia' compilati si contano in `compilati`.
//       - `_comune_obj` e `via_obj`: decorazioni del lookup. Della via basta
//         l'identita' (stradario o stradario generale).
// ------------------------------------------------------------

const INDIRIZZO_ESCLUSI = new Set(['tipo_indirizzo_codice_interno', '_isLibera', '_comune_obj', 'via_obj'])

// Scopo: copia le chiavi di `sorgente` in `dest` col prefisso dato.
function _conPrefisso(dest, prefisso, sorgente, esclusi = null) {
  for (const [k, v] of Object.entries(sorgente)) {
    if (esclusi?.has(k)) continue
    dest[`${prefisso}.${k}`] = v
  }
}

// `contatto`       il composable `useContattoForm` (o null)
// `indirizzo`      il composable `useIndirizzoSoggettoForm` (o null)
// `datiSocietari`  il composable `useDatiSocietariForm` (o null)
export function raccogliFormInline({ contatto = null, indirizzo = null, datiSocietari = null } = {}) {
  const valori = {}
  if (contatto) _conPrefisso(valori, 'contatto', contatto.form)
  if (indirizzo) {
    const f = indirizzo.form
    _conPrefisso(valori, 'indirizzo', f, INDIRIZZO_ESCLUSI)
    valori['indirizzo.via'] = f.via_obj?.stradario_id ?? f.via_obj?.stradario_generale_id ?? null
    // I tipi gia' compilati e messi da parte cambiando tipo (multi-tipo):
    // anche loro vanno al Salva.
    valori['indirizzo.compilati'] = indirizzo.tipiStato.value
      .filter((s) => s.compilato)
      .map((s) => s.codice)
  }
  if (datiSocietari) _conPrefisso(valori, 'dati_societari', datiSocietari.form)
  return valori
}

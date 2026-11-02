// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: UN VALORE PER RIGA SCELTA — la meta' «valore» di ogni macchina
//        «selezione + quantita'/importo per riga»: la mappa chiave → valore,
//        seminata da una PROPOSTA (il residuo, lo spazio), sovrascrivibile
//        dall'operatore, che al Salva diventa il payload.
// Note: ⭐ Estratto il 2026-09-17 alla SECONDA occorrenza (regola del 2, ok
//       Tid — Q-1 del piano D19). La prima e' `qtaMap` in
//       `vendite/_shared/righe/useRigheSelezioneQta` (evasione ordine, crea
//       reso, ri-consegna: una QUANTITA' per riga, proposta dal residuo); la
//       seconda e' il picker delle rate della distinta (un IMPORTO per rata,
//       proposto dallo spazio). Stesso schema — mappa, seme, override,
//       payload — su due telai diversi.
//
//       ⛔ NON sa niente di selezione, ed e' il punto: si COMPONE con entrambi i
//       telai — `useSelezioneToggle` per le liste INTERE (i dialog, dove la
//       selezione e' un sottoinsieme di cio' che si vede) e `useSelezioneLista`
//       per le liste PAGINATE (dove attraversa le pagine e va potata). Un BB
//       che portasse dentro anche la selezione sarebbe la terza copia di uno
//       dei due telai.
//
//       ⚠️ `useRigheSelezioneQta` NON e' stato migrato in questo giro (decisione
//       di Tid, 2026-09-17): ci passa quando lo si riapre, e il debito e'
//       dichiarato qui e nel catalogo. Le differenze che quella migrazione
//       dovra' assorbire sono due e sono di dominio, non di schema: il
//       predicato `> 0` (quantita') contro `!== 0` (importo con segno), e
//       `coversAllResiduo`, che e' un fatto del residuo e non del valore.
//
//       ⭐ IL SEGNO RESTA. Sulla nota di credito lo spazio e' NEGATIVO ed e' un
//       importo legittimo (il rimborso): il BB non filtra per segno, e
//       `buildPayload` scarta di default il solo `null` — «non compilato» —
//       non lo zero, che e' un valore che l'operatore ha scritto e che il
//       database rifiutera' con la sua frase, per riga. Chi vuole altro passa
//       `includi`.
//
//       ⚠️ `sincronizza(righe)` e' IDEMPOTENTE e non ri-propone: una riga gia'
//       nella mappa tiene il valore che ha — anche se l'operatore l'ha
//       cambiato — e una riga uscita dalla selezione esce dalla mappa. Se
//       rientra, riparte dalla proposta: e' il comportamento che un operatore
//       si aspetta da una casella che ha appena rispuntato.
//
//       ⛔ La mappa si SOSTITUISCE, mai si muta in place (stessa trappola di
//       `useRigheInGiro`): un `.set` sull'oggetto dentro il ref non cambia
//       l'identita' e i computed a valle non si rieseguono — celle che non si
//       aggiornano, senza errori.
// ------------------------------------------------------------

import { computed, ref } from 'vue'

// Params:
//   - rowKey:   la chiave della riga (`id`, `scadenza_id`).
//   - proponi:  (riga) → valore proposto, o `null` se non c'e' niente da
//               proporre (la proposta e' del dominio: residuo, spazio, …).
export function useSelezioneConValore({ rowKey = 'id', proponi = () => null } = {}) {
  const valori = ref({})

  // Scopo: allinea la mappa alle righe scelte — entra chi manca (con la
  //        proposta), esce chi non c'e' piu'. Non tocca chi c'e' gia'.
  function sincronizza(righe) {
    const prossima = {}
    let nuove = false
    for (const r of righe ?? []) {
      const chiave = r[rowKey]
      if (Object.hasOwn(valori.value, chiave)) {
        prossima[chiave] = valori.value[chiave]
      } else {
        prossima[chiave] = proponi(r)
        nuove = true
      }
    }
    // Niente di nuovo e niente di uscito (`prossima` e' un sottoinsieme della
    // mappa: stessa lunghezza = stesso insieme) → la mappa resta la stessa,
    // e i computed a valle non si rieseguono per niente.
    if (!nuove && Object.keys(prossima).length === Object.keys(valori.value).length) return
    valori.value = prossima
  }

  function valoreDi(chiave) {
    return valori.value[chiave] ?? null
  }

  // Scopo: il valore scritto dall'operatore. `null` = casella svuotata.
  function imposta(chiave, valore) {
    valori.value = { ...valori.value, [chiave]: valore }
  }

  // Scopo: torna alla proposta per una riga (l'operatore ci ha ripensato).
  function riproponi(riga) {
    imposta(riga[rowKey], proponi(riga))
  }

  function azzera() {
    valori.value = {}
  }

  // Le chiavi senza un valore: e' cio' che tiene spento il Salva, invece di
  // saltare in silenzio una riga che l'operatore credeva di aver mandato.
  const incompleti = computed(
    () => Object.keys(valori.value).filter((k) => valori.value[k] == null),
  )

  // Scopo: il payload delle righe scelte, `mapRow(riga, valore)` per ciascuna.
  //        `includi(valore, riga)` decide chi entra: di default tutto cio' che
  //        NON e' `null` — lo zero e il negativo sono valori scritti.
  function buildPayload(righe, mapRow, { includi = (v) => v != null } = {}) {
    const out = []
    for (const r of righe ?? []) {
      const v = valoreDi(r[rowKey])
      if (!includi(v, r)) continue
      out.push(mapRow(r, v))
    }
    return out
  }

  return { valori, sincronizza, valoreDi, imposta, riproponi, azzera, incompleti, buildPayload }
}

// ------------------------------------------------------------
// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// ------------------------------------------------------------
// Scopo: LA FOTOGRAFIA DI UN DIALOG CON CAMPI — perche' uscirne (X, ESC,
//        maschera, Annulla) chieda solo se qualcosa e' cambiato. Nata il
//        2026-10-03 (D-14 di work-done/analisi-fe-chrome-drawer.md,
//        Tid: «nessuna eccezione»): 44 dialog con campi si chiudevano in
//        silenzio, buttando cio' che si era scritto.
//
// ⭐ E' `useDrawerFormPreserve` con le due cose che un dialog ha sempre:
//    - lo STATO sta quasi mai in un `form` solo — una data, un motivo, una
//      selezione, dei file — e lo si passa come getter, che diventa un
//      computed: `() => ({ data: data.value, motivo: motivo.value })`;
//    - la fotografia si prende ALL'APERTURA, dopo il giro di watch con cui il
//      dialog si prepara (`nextTick`).
//
// ⚠️ Un dialog che all'apertura CARICA dei dati (fetch) e li scrive nello stato
//    passa `fissaAllApertura: false` e chiama `fissa()` a caricamento finito:
//    fissata prima, la fotografia vedrebbe i dati arrivati come «modifiche» e
//    chiederebbe anche a chi non ha toccato niente.
//
// Uso:
//   const { chiudiConConferma } = useFotografiaDialog(
//     () => ({ data: dataChiusura.value, motivo: motivo.value }),
//     { visibile: () => props.visible },
//   )
//   <AppDialog … :conferma-uscita="chiudiConConferma">
import { computed, nextTick, watch } from 'vue'
import { useDrawerFormPreserve } from './useDrawerFormPreserve'

export function useFotografiaDialog(stato, { visibile, fissaAllApertura = true } = {}) {
  const fotografia = useDrawerFormPreserve(computed(stato), { visibile })
  if (fissaAllApertura) {
    watch(
      () => Boolean(visibile()),
      (aperto) => {
        if (aperto) nextTick(() => fotografia.fissa())
      },
      { immediate: true },
    )
  }
  return fotografia
}

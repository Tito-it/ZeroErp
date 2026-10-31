// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// Doc: JavaScript
// Scopo: Le due regole pure del tetto d'area, per la SOLA anteprima
//        (brief-db-permessi-tetto-area §7.3, Tid 2026-10-04): mostrare
//        «limitata dall'area» mentre l'admin cambia i valori, prima del
//        salvataggio. Consumer: il pannello permessi dell'operatore
//        (`OperatorePermessiTab`) e, dal 2026-10-31, il profilo del reparto
//        (`RepartoProfiloEditor`).
//        ⛔ Sui valori SALVATI nessuno dei due la usa: l'operatore legge
//        `permessi-effettivi`, il reparto `limitata_da_area` della lettura del
//        profilo, entrambi calcolati a DB (decisione Tid «sola regola DB»).
// Note: ⛔ NON e' la sede della regola. La sede e' il DB:
//       `script.fn_area_consente_azione` e `script.fn_livello_con_tetto_area`,
//       lette dai resolver, dalle mappe di `/me/` e dal pannello (endpoint
//       `permessi-effettivi`). Qui ce n'e' una copia DICHIARATA, ammessa solo
//       per l'anteprima di valori non ancora salvati; dopo il salvataggio il
//       pannello torna a leggere il DB.
//       Presidio della copia: `tettoArea.spec.js` riproduce i casi 3 e 4 del
//       pgTAP `test-permessi-tetto-area-v1`. Se la regola cambia a DB, cambia
//       quel pgTAP, e lo spec va riallineato nello stesso giro.
// ------------------------------------------------------------

import { LIVELLO_ACCESSO } from '../core/constants'

// ⛔ L'ordine dell'enum `config.livello_accesso` e' TUTTO < LETTURA < BLOCCATO:
//    il rango cresce con la RESTRIZIONE. E' il verso controintuitivo che rende
//    pericolosa una copia scritta a memoria.
const RANGO = {
  [LIVELLO_ACCESSO.TUTTO]: 1,
  [LIVELLO_ACCESSO.LETTURA]: 2,
  [LIVELLO_ACCESSO.BLOCCATO]: 3,
}

// Scopo: Copia di `script.fn_area_consente_azione`: il livello d'area arriva
//        al minimo che l'azione dichiara? NULL (o un valore sconosciuto) da
//        qualunque parte vale no (fail-closed).
export function areaConsenteAzione(livelloArea, livelloMinimo) {
  const area = RANGO[livelloArea]
  const minimo = RANGO[livelloMinimo]
  if (area == null || minimo == null) return false
  return area <= minimo
}

// Scopo: Copia di `script.fn_livello_con_tetto_area`: il piu' restrittivo fra
//        lo specifico e l'area. Senza specifico vale l'area; area NULL vale
//        BLOCCATO (fail-closed).
export function livelloConTettoArea(livelloSpecifico, livelloArea) {
  const area = RANGO[livelloArea] != null ? livelloArea : LIVELLO_ACCESSO.BLOCCATO
  if (RANGO[livelloSpecifico] == null) return area
  return RANGO[livelloSpecifico] >= RANGO[area] ? livelloSpecifico : area
}

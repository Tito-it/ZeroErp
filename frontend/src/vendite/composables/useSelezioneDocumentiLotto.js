// ------------------------------------------------------------
// SPDX-License-Identifier: GPL-3.0-or-later
// Copyright (C) 2026 Tid (Michele Carlo Titini)
// ------------------------------------------------------------
import { useI18n } from 'vue-i18n'
import { useSelezioneLista } from '../../core/composables/useSelezioneLista'
import { motivoUscitaBloccata } from '../uscitaDalGiro'

// Scopo: quali DOCUMENTI di un lotto si possono togliere dal giro in un colpo
//        solo — la selezione della scheda «Documenti presi in carico».
//
// ⭐ È un consumatore SOTTILE del telaio: qui vive solo il DOMINIO — chi è
//    spuntabile e perché no — mentre prune, seleziona-tutto-in-pagina e la
//    composizione di `perLista` stanno in `useSelezioneLista`. È la lezione
//    già pagata due volte: attorno a quel telaio le copie scritte a mano
//    divergevano sul `toggleAll`, che su una lista PAGINATA butta via quanto
//    spuntato nelle pagine precedenti.
//
// ⛔ IL PREDICATO NON SI RISCRIVE: «si può togliere?» lo dice il database in
//    riga (`uscita_blocco_reason`, dalla stessa `fn_check_*` con cui rifiuta).
//    Qui si legge, non si ricalcola — altrimenti la casella e il rifiuto
//    direbbero due cose diverse.
export function useSelezioneDocumentiLotto({ righeVisibili, abilitata }) {
  const { t, te } = useI18n()

  // Sede UNICA del predicato: il telaio lo gira alle caselle, al
  // seleziona-tutto, al guard del toggle e al prune.
  const selezionabile = (row) => !row?.uscita_blocco_reason

  // ⛔ E NEMMENO IL MOTIVO SI RISCRIVE: la traduzione della riga sta in
  //    `motivoUscitaBloccata`, che è la stessa sorgente da cui le due azioni di
  //    riga prendono il loro tooltip. Casella spenta e voce spenta devono dire
  //    la stessa frase, e l'unico modo perché non possano divergere è che la
  //    frase sia una.
  const motivoNonSelezionabile = (row) => motivoUscitaBloccata(t, te, row)

  // ⛔ Niente `escludiOvunque` né `sorveglia`: qui non c'è stato FUORI dalla
  //    riga — la selezionabilità è un campo che il backend consegna, quindi il
  //    prune della pagina basta. Aggiungerli «per simmetria» col gemello dei
  //    lotti sarebbe sorvegliare qualcosa che non cambia.
  return useSelezioneLista({
    righeVisibili,
    abilitata,
    selezionabile,
    motivoNonSelezionabile,
    rowKey: 'gruppo_key',
  })
}

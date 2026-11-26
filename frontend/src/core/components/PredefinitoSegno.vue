<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL segno «e' il predefinito» di una voce (contatto, conto bancario,
//        magazzino, modello di documento, billing account dell'emittente):
//        la puntina `MANAGE_ICONS.PREDEFINITO` col tooltip, nel colore
//        `--app-predefinito-color`. Sul falso e sul null non rende niente: il
//        predefinito e' UNO, e il segno si legge solo dove c'e'.
//
// Estratto il 2026-11-26 alla terza occorrenza (regola del 2, ok Tid): la
// puntina con la sua classe scoped stava nel drawer dei conti bancari
// (`.conto-predefinito`, con un `font-size` suo) e in quello dei contatti
// (`.contatto-predefinito`), e serviva al riepilogo contatti del soggetto.
// Nello stesso giro le liste che lo dicevano in altro modo — Tag «Predefinito»
// (magazzini), Tag «Si'» (modelli di documento), Badge «Default» (billing
// account dell'emittente) — sono passate a questo: lo stesso fatto ha una
// resa sola ovunque, e l'icona non si usa con un altro significato.
//
// ⛔ Non e' `SiNoTag`: quello dice un fatto vero o falso di OGNI riga. Questo
//    marca la sola voce scelta fra le altre, e il falso non si scrive.
// ⛔ Non e' l'AZIONE «Rendi predefinito»: quella e' un pulsante con la stessa
//    icona (`MANAGE_ICONS.PREDEFINITO`) e la sua etichetta, sulle voci che
//    non lo sono.
// ⭐ In una `<ListaConfigurabile>` e' la resa di `formato = predefinito` in
//    `CellaConfigurabile`: una colonna «predefinito» e' una riga di
//    `ui.lista_colonna`, non uno slot.
import { useI18n } from 'vue-i18n'
import { MANAGE_ICONS } from '../constants'

defineProps({
  // Il booleano gia' risolto dal caller (non il path del campo).
  // ⚠️ `type: null` e non `Boolean`, come `SiNoTag`: un valore assente resta
  //    assente, senza il boolean casting di Vue.
  value: { type: null, default: null },
})

const { t } = useI18n()
</script>

<template>
  <i v-if="value"
    class="predefinito-segno" :class="MANAGE_ICONS.PREDEFINITO"
    role="img" :aria-label="t('common.predefinito')"
    v-tooltip.top="t('common.predefinito')" />
</template>

<style scoped>
.predefinito-segno {
  color: var(--app-predefinito-color);
}
</style>

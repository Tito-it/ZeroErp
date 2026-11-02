<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL Tag «Sì» / «No» di un booleano-DATO in lista o in scheda:
//        `info` sul vero, `secondary` sul falso, VUOTO sul null.
//
// Estratto il 2026-09-14 alla terza occorrenza (regola del 2, ok Tid): lo
// stesso ternario
//   <Tag :value="x ? t('common.yes') : t('common.no')"
//        :severity="x ? 'info' : 'secondary'" />
// stava in tre slot `#cell-*` (lista articoli x2, categorie clienti), e uno
// dei tre sovrascriveva una colonna che a catalogo aveva GIA' `formato=yesno`
// — il formatter rendeva testo, chi voleva il Tag se lo riscriveva. Da qui
// `CellaConfigurabile` rende `yesno` con questo componente: un booleano in
// lista e' una riga di `ui.lista_colonna`, non uno slot.
//
// ⛔ Non e' `AttivoTag`: quello dice lo STATO di un record (verde/arancio,
//    «Attivo»/«Non attivo», con le sue conseguenze sulle azioni di riga).
//    Questo dice un FATTO («partecipa alle promo?», «gestito a magazzino?»):
//    il vero e' un'informazione, non una salute — per questo e' blu e non verde.
// ⚠️ `null` NON e' «No»: e' «non lo so» (una colonna nullable, un'anteprima
//    senza il dato) e resta vuoto — la stessa disciplina di `giorni_ritardo`.
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'

defineProps({
  // Il booleano gia' risolto dal caller (non il path del campo).
  // ⚠️ `type: null` e non `Boolean`, come `MatriceOverride.readonly`: col
  //    boolean casting di Vue un valore assente arriverebbe `false`, cioe' «No»
  //    su una cella che non ha il dato — e il vuoto e' l'informazione.
  value: { type: null, default: null },
})

const { t } = useI18n()
</script>

<template>
  <Tag v-if="value != null"
    :value="value ? t('common.yes') : t('common.no')"
    :severity="value ? 'info' : 'secondary'" />
</template>

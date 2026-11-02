<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista stati (nazioni) (`config.stati`, lista 93, tabella
//        `config.stati`): sigla e prefisso telefonico ci sono, spenti di default.
//        La ricerca parte da UN carattere (codici ISO): e' la soglia della lista.
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo i valori che distinguono questa lista dalle altre cinque
//    geografiche. Fino a quel giorno ognuna ricopiava lo stesso scheletro.
import { useI18n } from 'vue-i18n'
import { useStatiStore } from '../stores/stati'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useStatiStore()
</script>

<template>
  <ListaPaginaSemplice
    :store="store"
    codice="config.stati"
    :tab-entity="TAB_ENTITIES.STATO"
    :search-placeholder="t('geo.search_stato')"
    new-tooltip-key="geo.nuovo_stato"
    default-sort-field="descrizione"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  ></ListaPaginaSemplice>
</template>

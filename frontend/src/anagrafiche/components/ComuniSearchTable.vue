<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista comuni (`config.comuni`, lista 94, vista `config.vw_comuni_lista`).
// ⚠️ Sola creazione: la riga NON apre un drawer (nessuna modifica del comune da
//    qui), quindi `righe-cliccabili` spento e nessun `row-click`.
// Riusabile da: tab X in IndirizziView, futuro filtri clienti/fornitori.
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo i valori che distinguono questa lista dalle altre cinque
//    geografiche. Fino a quel giorno ognuna ricopiava lo stesso scheletro.
import { useI18n } from 'vue-i18n'
import { useComuniStore } from '../stores/comuni'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['new'])
const { t } = useI18n()
const store = useComuniStore()
</script>

<template>
  <ListaPaginaSemplice
    :store="store"
    codice="config.comuni"
    :tab-entity="TAB_ENTITIES.COMUNE"
    :search-placeholder="t('indirizzi.search_comune')"
    new-tooltip-key="indirizzi.nuovo_comune"
    default-sort-field="descrizione"
    :righe-cliccabili="false"
    @new="emit('new')"
  ></ListaPaginaSemplice>
</template>

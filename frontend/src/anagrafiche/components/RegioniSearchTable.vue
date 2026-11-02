<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista regioni (`config.regioni`, lista 91, vista `config.vw_regioni_lista`):
//        colonne, ordine e visibilita' dal catalogo, personalizzazione per utente.
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo i valori che distinguono questa lista dalle altre cinque
//    geografiche. Fino a quel giorno ognuna ricopiava lo stesso scheletro.
import { useI18n } from 'vue-i18n'
import { useRegioniStore } from '../stores/regioni'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useRegioniStore()
</script>

<template>
  <ListaPaginaSemplice
    :store="store"
    codice="config.regioni"
    :tab-entity="TAB_ENTITIES.REGIONE"
    :search-placeholder="t('geo.search_regione')"
    new-tooltip-key="geo.nuova_regione"
    default-sort-field="descrizione"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  ></ListaPaginaSemplice>
</template>

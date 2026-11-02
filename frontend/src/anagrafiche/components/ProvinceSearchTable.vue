<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista province (`config.province`, lista 92, vista
//        `config.vw_province_lista`). La ricerca parte da UN carattere (sigla):
//        e' la soglia della lista a catalogo.
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo i valori che distinguono questa lista dalle altre cinque
//    geografiche. Fino a quel giorno ognuna ricopiava lo stesso scheletro.
import { useI18n } from 'vue-i18n'
import { useProvinceStore } from '../stores/province'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { TAB_ENTITIES } from '../../core/constants'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useProvinceStore()
</script>

<template>
  <ListaPaginaSemplice
    :store="store"
    codice="config.province"
    :tab-entity="TAB_ENTITIES.PROVINCIA"
    :search-placeholder="t('geo.search_provincia')"
    new-tooltip-key="geo.nuova_provincia"
    default-sort-field="descrizione"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  ></ListaPaginaSemplice>
</template>

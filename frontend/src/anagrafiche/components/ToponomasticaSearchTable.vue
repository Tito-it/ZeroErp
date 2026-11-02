<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista toponomastica (tipi di strada) (`config.toponomastica`, lista 96,
//        tabella `config.toponomastica`), con la colonna stato come `AttivoTag`.
// Riusabile da: tab X in IndirizziView, futuro gestione stradario.
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo i valori che distinguono questa lista dalle altre cinque
//    geografiche. Fino a quel giorno ognuna ricopiava lo stesso scheletro.
import { useI18n } from 'vue-i18n'
import { useToponomasticaStore } from '../stores/toponomastica'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { TAB_ENTITIES } from '../../core/constants'
import AttivoTag from '../../core/components/AttivoTag.vue'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useToponomasticaStore()
</script>

<template>
  <ListaPaginaSemplice
    :store="store"
    codice="config.toponomastica"
    :tab-entity="TAB_ENTITIES.TOPONOMASTICA"
    :search-placeholder="t('indirizzi.search_toponomastica')"
    new-tooltip-key="indirizzi.nuova_toponomastica"
    default-sort-field="descrizione"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  >
    <template #cell-attivo="{ data }">
      <AttivoTag
        :active="data.attivo"
        :active-label="t('indirizzi.attivo')"
        :inactive-label="t('indirizzi.non_attivo')"
      />
    </template>
  </ListaPaginaSemplice>
</template>

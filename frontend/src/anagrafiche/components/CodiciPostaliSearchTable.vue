<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista codici postali (`config.codici_postali`, lista 95, vista
//        `config.vw_codici_postali_lista`) con filtro per comune.
// ⏳ La lista non porta ancora la provincia (due comuni omonimi non si
//    distinguono): deciso che la mostri, richiesta al DB in
//    brief-db-liste-datatable-grezze §9.2, ricaduta BE in §9.3.
// ⭐ La pagina e' `<ListaPaginaSemplice>` (2026-09-27, regola del 2, ok Tid):
//    qui restano solo i valori che distinguono questa lista dalle altre cinque
//    geografiche. Fino a quel giorno ognuna ricopiava lo stesso scheletro.
import { useI18n } from 'vue-i18n'
import { useCodiciPostaliStore } from '../stores/codiciPostali'
import ListaPaginaSemplice from '../../core/components/ListaPaginaSemplice.vue'
import { TAB_ENTITIES } from '../../core/constants'
import { computed } from 'vue'
import ComuneAutocomplete from './ComuneAutocomplete.vue'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useCodiciPostaliStore()

// ⛔ Il valore a video E' quello dello store, non una copia locale: «Pulisci
//    filtri» (`azzeraFiltri`) scrive lo store, e una ref qui avrebbe lasciato
//    il comune nella casella sopra una lista gia' intera.
const comuneFilter = computed(() => store.filters.comune_id ?? null)
</script>

<template>
  <ListaPaginaSemplice
    :store="store"
    codice="config.codici_postali"
    :tab-entity="TAB_ENTITIES.CODICE_POSTALE"
    :search-placeholder="t('indirizzi.search_cap')"
    new-tooltip-key="indirizzi.nuovo_cap"
    default-sort-field="comune_descrizione"
    @row-click="(riga) => emit('row-click', riga)"
    @new="emit('new')"
  >
    <template #filtri="{ applyFilters }">
      <ComuneAutocomplete
        class="app-filter-w-lg"
        :model-value="comuneFilter"
        @update:model-value="(id) => { store.filters.comune_id = id; applyFilters() }"
      />
    </template>
  </ListaPaginaSemplice>
</template>

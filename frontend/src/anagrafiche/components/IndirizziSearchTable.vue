<script setup>
// Scopo: Lista indirizzi configurabile
//        (`<ListaConfigurabile codice="anagrafiche.indirizzi">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente. Lista a ricerca obbligatoria: resta nascosta
//        finche' non si e' cercato. Nessun export: il dominio non ha endpoint.
import {ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useIndirizziStore } from '../stores/indirizzi'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import ComuneAutocomplete from '../../core/components/ComuneAutocomplete.vue'
import InputText from 'primevue/inputtext'
import AttivoTag from '../../core/components/AttivoTag.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import FiltriLista from '../../core/components/FiltriLista.vue'

const emit = defineEmits(['row-click', 'new'])
const { t } = useI18n()
const store = useIndirizziStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  mostraLista, mostraSearchHint,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'indirizzi.nuovo_indirizzo',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'indirizzo_normalizzato' },
})

const comuneFilter = ref(null)

useTabFreshness(store, TAB_ENTITIES.INDIRIZZO)
// La lista parte vuota — salvo che arrivi con search precaricata da URL/context.
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})

function onComuneChange(id) {
  comuneFilter.value = id
  store.filters.comune_id = id
  applyFilters()
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) {
  emit('row-click', data)
}
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText
            v-model="searchText"
            class="app-filter-w-lg"
            :placeholder="t('indirizzi.search_indirizzo')"
          />
        </template>
        <ComuneAutocomplete
          class="app-filter-w-lg"
          :model-value="comuneFilter"
          @update:model-value="onComuneChange"
        />
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <!-- Placeholder: nessuna ricerca effettuata -->
    <SearchHint v-if="mostraSearchHint" />

    <ListaConfigurabile
      v-show="mostraLista"
      ref="listaRef"
      codice="anagrafiche.indirizzi"
      data-key="indirizzo_dettaglio_id"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      @config-loaded="onConfigLoaded"
    >
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" :active-label="t('indirizzi.attivo')"
          :inactive-label="t('indirizzi.non_attivo')" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>

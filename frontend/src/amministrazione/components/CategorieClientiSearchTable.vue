<script setup>
// Scopo: Lista admin categorie cliente, configurabile
//        (`<ListaConfigurabile codice="anagrafiche.categorie_clienti">`):
//        colonne, ordine e visibilita' dal catalogo `ui.lista_colonna`, con
//        ritiro dinamico e personalizzazione per utente.
//        Nessun export: il dominio non ha endpoint (lo scaffolding omette
//        l'azione da se', non ricevendo `exportFn`).
import {ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCategorieClientiStore } from '../stores/categorieClienti'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useCategorieClientiStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'amministrazione.categorie_clienti.new',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'ordinamento' },
})

const attivoFilter = ref(true)
const partecipaPromoFilter = ref(null)

const boolOptions = buildBoolOptions(t)

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

function onPartecipaPromoChange() {
  store.filters.partecipa_promo = partecipaPromoFilter.value
  applyFilters()
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

useTabFreshness(store, TAB_ENTITIES.CATEGORIE_CLIENTI)
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters" :inert="perimetroBloccato">
        <InputText
          v-model="searchText"
          :placeholder="t('amministrazione.categorie_clienti.search_placeholder')"
        />
        <Select
          v-model="partecipaPromoFilter"
          :options="boolOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.categorie_clienti.filter_partecipa_promo')"
          @change="onPartecipaPromoChange"
          style="width: 180px;"
        />
        <Select
          v-model="attivoFilter"
          :options="boolOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('common.attivo')"
          @change="onAttivoChange"
          style="width: 120px;"
        />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="anagrafiche.categorie_clienti"
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
      <!-- ⛔ Nessuno slot per `partecipa_promo` (220): e' `formato=yesno` a
           catalogo e lo rende `SiNoTag` dal BB. Fino al 2026-09-14 qui c'era
           lo stesso Tag scritto a mano SOPRA quel formato. -->
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>

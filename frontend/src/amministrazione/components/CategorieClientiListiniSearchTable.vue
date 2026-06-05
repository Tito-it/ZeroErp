<script setup>
// Scopo: DataTable matrice pricing v5 categoria_cliente x utility x emittente
//        x classe_utenza (opz) -> listino con variazione opzionale.
//        Pattern identico a UtilitiesTipiRuoloSearchTable.
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCategorieClientiListiniStore } from '../stores/categorieClientiListini'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import { useLookup } from '../../core/composables/useLookup'
import { listEmittentiFiscali } from '../api/amministrazione'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useCategorieClientiListiniStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'valido_dal'
})

const emittentiLookup = useLookup(listEmittentiFiscali, { immediate: true })

const attivoFilter = ref(true)
const categoriaFilter = ref(null)
const utilityFilter = ref(null)
const emittenteFilter = ref(null)
const listinoFilter = ref(null)

const boolOptions = buildBoolOptions(t)
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: reload,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('amministrazione.matrice_categorie_listini.new_row'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

function onCategoriaChange(value) {
  store.filters.categoria_cliente_id = value ?? null
  applyFilters()
}

function onUtilityChange(value) {
  store.filters.utility_id = value ?? null
  applyFilters()
}

function onEmittenteChange(event) {
  store.filters.emittente_soggetto_ruolo_id = event.value ?? null
  applyFilters()
}

function onListinoChange(value) {
  store.filters.listino_id = value ?? null
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, TAB_ENTITIES.CATEGORIE_CLIENTI_LISTINI)
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('amministrazione.matrice_categorie_listini.search_placeholder')"
        />
        <LookupSelect
          v-model="categoriaFilter"
          @change="onCategoriaChange"
          rel="anagrafiche.categorie_clienti"
          :placeholder="t('amministrazione.matrice_categorie_listini.filter_categoria')"
          showClear
          style="min-width: 180px;"
        />
        <LookupSelect
          v-model="utilityFilter"
          @change="onUtilityChange"
          rel="config.utilities"
          :placeholder="t('amministrazione.matrice_categorie_listini.filter_utility')"
          showClear
          style="min-width: 160px;"
        />
        <Select
          v-model="emittenteFilter"
          :options="emittentiLookup.items.value"
          option-label="ragione_sociale"
          option-value="soggetto_ruolo_id"
          :placeholder="t('amministrazione.matrice_categorie_listini.filter_emittente')"
          show-clear
          filter
          @change="onEmittenteChange"
          style="min-width: 200px;"
        />
        <LookupSelect
          v-model="listinoFilter"
          @change="onListinoChange"
          rel="vendite.listini"
          :placeholder="t('amministrazione.matrice_categorie_listini.filter_listino')"
          showClear
          style="min-width: 160px;"
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
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy
      removable-sort
      striped-rows
      scrollable
      scrollHeight="flex"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      selection-mode="single"
      data-key="id"
    >
      <Column
        field="categoria_codice"
        :header="t('amministrazione.matrice_categorie_listini.col_categoria')"
        sortable
        style="width: 130px;"
      />
      <Column
        field="utility_codice"
        :header="t('amministrazione.matrice_categorie_listini.col_utility')"
        sortable
        style="width: 120px;"
      />
      <Column
        field="emittente_ragione_sociale"
        :header="t('amministrazione.matrice_categorie_listini.col_emittente')"
        sortable
        style="min-width: 200px;"
      />
      <Column
        field="classe_utenza_codice"
        :header="t('amministrazione.matrice_categorie_listini.col_classe_utenza')"
        sortable
        style="width: 140px;"
      >
        <template #body="{ data }">
          {{ data.classe_utenza_codice || '—' }}
        </template>
      </Column>
      <Column
        field="listino_codice"
        :header="t('amministrazione.matrice_categorie_listini.col_listino')"
        sortable
        style="min-width: 160px;"
      />
      <Column
        field="tipo_variazione"
        :header="t('amministrazione.matrice_categorie_listini.col_variazione')"
        style="width: 180px;"
      >
        <template #body="{ data }">
          <span v-if="data.tipo_variazione">
            {{ data.tipo_variazione }}: {{ data.valore_variazione }}
          </span>
          <span v-else>—</span>
        </template>
      </Column>
      <Column
        field="valido_dal"
        :header="t('amministrazione.matrice_categorie_listini.col_valido_dal')"
        sortable
        style="width: 120px;"
      />
      <Column
        field="valido_al"
        :header="t('amministrazione.matrice_categorie_listini.col_valido_al')"
        sortable
        style="width: 120px;"
      >
        <template #body="{ data }">
          {{ data.valido_al || '—' }}
        </template>
      </Column>
      <Column
        field="attivo"
        :header="t('amministrazione.matrice_categorie_listini.col_attivo')"
        sortable
        style="width: 100px;"
      >
        <template #body="{ data }">
          <AttivoTag :active="data.attivo" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>

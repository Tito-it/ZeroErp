<script setup>
// Scopo: DataTable admin promo articoli (vendite.promo_articoli).
//        STADIO 0 resolver v5: overlay temporale (articolo, uom) -> batte
//        listini e matrice categoria. Unico livello con PREZZO_FISSO.
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePromoArticoliStore } from '../stores/promoArticoli'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
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
const store = usePromoArticoliStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'valido_dal'
})

const attivoFilter = ref(true)
const uomFilter = ref(null)
const tipoVariazioneFilter = ref(null)

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
    tooltip: t('vendite.promo_articoli.new'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

const tipoVariazioneOptions = [
  { value: null, label: t('common.all') },
  { value: 'PERCENTUALE', label: 'PERCENTUALE' },
  { value: 'VALORE_FISSO', label: 'VALORE_FISSO' },
  { value: 'PREZZO_FISSO', label: 'PREZZO_FISSO' }
]

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}
function onUomChange(value) {
  store.filters.uom_id = value ?? null
  applyFilters()
}
function onTipoVariazioneChange() {
  store.filters.tipo_variazione = tipoVariazioneFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

useTabFreshness(store, TAB_ENTITIES.PROMO_ARTICOLI)
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
          :placeholder="t('vendite.promo_articoli.search_placeholder')"
        />
        <LookupSelect
          v-model="uomFilter"
          @change="onUomChange"
          rel="catalogo.unita_misura"
          :placeholder="t('vendite.promo_articoli.filter_uom')"
          showClear
          style="min-width: 160px;"
        />
        <Select
          v-model="tipoVariazioneFilter"
          :options="tipoVariazioneOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('vendite.promo_articoli.filter_tipo_variazione')"
          @change="onTipoVariazioneChange"
          style="width: 160px;"
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
        field="codice"
        :header="t('vendite.promo_articoli.col_codice')"
        sortable
        style="width: 140px;"
      />
      <Column
        field="descrizione"
        :header="t('vendite.promo_articoli.col_descrizione')"
        sortable
        style="min-width: 200px;"
      />
      <Column
        field="articolo_codice"
        :header="t('vendite.promo_articoli.col_articolo')"
        sortable
        style="min-width: 180px;"
      >
        <template #body="{ data }">
          {{ data.articolo_codice }} — {{ data.articolo_descrizione }}
        </template>
      </Column>
      <Column
        field="uom_codice"
        :header="t('vendite.promo_articoli.col_uom')"
        sortable
        style="width: 100px;"
      />
      <Column
        field="tipo_variazione"
        :header="t('vendite.promo_articoli.col_variazione')"
        style="width: 200px;"
      >
        <template #body="{ data }">
          <span>{{ data.tipo_variazione }}: {{ data.valore_variazione }}</span>
        </template>
      </Column>
      <Column
        field="valido_dal"
        :header="t('vendite.promo_articoli.col_valido_dal')"
        sortable
        style="width: 120px;"
      />
      <Column
        field="valido_al"
        :header="t('vendite.promo_articoli.col_valido_al')"
        sortable
        style="width: 120px;"
      />
      <Column
        field="attivo"
        :header="t('vendite.promo_articoli.col_attivo')"
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

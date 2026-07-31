<script setup>
// Scopo: Lista admin della matrice tipi_ruolo x tipi_indirizzo, configurabile
//        (`<ListaConfigurabile codice="config.tipi_ruolo_tipi_indirizzo">`):
//        colonne, ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro
//        dinamico e personalizzazione per utente. Editing inline (obbligatorio,
//        fallback, attivo) negli slot di cella. `valido_dal`/`valido_al` sono resi
//        dal `formato=date_short` del catalogo, non da uno slot.
//        Nessun export: il dominio non ha endpoint.
import {ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTipiRuoloTipiIndirizzoStore } from '../stores/tipiRuoloTipiIndirizzo'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly, useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import LookupSelect from '../../core/components/LookupSelect.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = useTipiRuoloTipiIndirizzoStore()
const isReadonly = useInjectReadonly()
const isBlocked = useInjectBlocked()
const { execute } = useApiHandler()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'amministrazione.matrice_indirizzi_ruoli.new_row',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'tipo_ruolo_descrizione' },
})

useTabFreshness(store, TAB_ENTITIES.TIPI_RUOLO_TIPI_INDIRIZZO)

const tipoRuoloFilter = ref(store.filters.tipo_ruolo_id)
const tipoIndirizzoFilter = ref(store.filters.tipo_indirizzo_id)
const attivoFilter = ref(true)

const boolOptions = buildBoolOptions(t)

const fallbackOptionsByRow = ref({})
const fallbackOptionsLoadingByRow = ref({})

// Scopo: opzioni fallback inline, riusando gli stessi metadata del drawer
// (`fallback_options` calcolate dal backend sul detail: no self-ref + no cicli).
function fallbackOptions(row) {
  if (fallbackOptionsByRow.value[row.id]) return fallbackOptionsByRow.value[row.id]
  if (!row.fallback_tipo_indirizzo_id) return []
  return [{
    tipo_indirizzo_id: row.fallback_tipo_indirizzo_id,
    codice: row.fallback_codice,
    descrizione: row.fallback_descrizione || row.fallback_codice
  }]
}

async function loadFallbackOptions(row) {
  if (fallbackOptionsByRow.value[row.id] || fallbackOptionsLoadingByRow.value[row.id]) return
  fallbackOptionsLoadingByRow.value[row.id] = true
  try {
    const detail = await store.fetchDetail(row.id)
    fallbackOptionsByRow.value[row.id] = Array.isArray(detail?.fallback_options)
      ? detail.fallback_options
      : []
  } finally {
    fallbackOptionsLoadingByRow.value[row.id] = false
  }
}

function onTipoRuoloChange() {
  store.filters.tipo_ruolo_id = tipoRuoloFilter.value
  applyFilters()
}
function onTipoIndirizzoChange() {
  store.filters.tipo_indirizzo_id = tipoIndirizzoFilter.value
  applyFilters()
}
function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}

async function changeFallback(row, newFallbackId) {
  const result = await execute(
    () => store.update(row.id, { fallback_tipo_indirizzo_id: newFallbackId || null }),
    { successMessage: t('amministrazione.matrice_indirizzi_ruoli.saved') }
  )
  if (result !== null) {
    row.fallback_tipo_indirizzo_id = result.fallback_tipo_indirizzo_id
    row.fallback_codice = result.fallback_codice
    row.fallback_descrizione = result.fallback_descrizione
    fallbackOptionsByRow.value[row.id] = Array.isArray(result.fallback_options)
      ? result.fallback_options
      : fallbackOptionsByRow.value[row.id]
  }
}

async function toggleObbligatorio(row) {
  if (isReadonly.value) return
  const result = await execute(
    () => store.update(row.id, { obbligatorio: !row.obbligatorio }),
    { successMessage: t('amministrazione.matrice_indirizzi_ruoli.saved') }
  )
  if (result !== null) {
    Object.assign(row, result)
  }
}

async function toggleAttivo(row) {
  if (isReadonly.value) return
  const result = await execute(
    () => store.update(row.id, { attivo: !row.attivo }),
    { successMessage: t('amministrazione.matrice_indirizzi_ruoli.saved') }
  )
  if (result !== null) {
    Object.assign(row, result)
  }
}

onMounted(() => { if (!store.hasSearched) store.fetchList() })
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('amministrazione.matrice_indirizzi_ruoli.search_placeholder')"
          @keydown.enter="applyFilters" />
        <LookupSelect v-model="tipoRuoloFilter" rel="config.tipi_ruoli"
          :placeholder="t('amministrazione.matrice_indirizzi_ruoli.filter_tipo_ruolo')"
          show-clear @change="onTipoRuoloChange" />
        <LookupSelect v-model="tipoIndirizzoFilter" rel="config.tipi_indirizzi"
          :placeholder="t('amministrazione.matrice_indirizzi_ruoli.filter_tipo_indirizzo')"
          show-clear @change="onTipoIndirizzoChange" />
        <Select v-model="attivoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('common.attivo')" @change="onAttivoChange" style="width: 120px;" />
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
      codice="config.tipi_ruolo_tipi_indirizzo"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="data => emit('row-click', data)"
      @config-loaded="onConfigLoaded"
    >
      <!-- Editing inline (pattern matrice slot/override): ToggleSwitch e Select
           vivono in cella. `@click.stop` sul wrapper: il click sul controllo non
           deve propagarsi come row-click e aprire il drawer. Gli slot valgono
           anche per la riga di espansione quando la colonna viene ritirata. -->
      <template #cell-obbligatorio="{ data }">
        <div @click.stop>
          <ToggleSwitch
            :modelValue="data.obbligatorio"
            :disabled="isReadonly"
            @update:modelValue="toggleObbligatorio(data)"
          />
        </div>
      </template>
      <template #cell-fallback_codice="{ data }">
        <div @click.stop>
          <Select
            :modelValue="data.fallback_tipo_indirizzo_id"
            @before-show="loadFallbackOptions(data)"
            @focus="loadFallbackOptions(data)"
            @update:modelValue="val => changeFallback(data, val)"
            :options="fallbackOptions(data)"
            option-label="descrizione"
            option-value="tipo_indirizzo_id"
            :placeholder="t('amministrazione.matrice_indirizzi_ruoli.no_fallback')"
            :disabled="isReadonly || fallbackOptionsLoadingByRow[data.id]"
            show-clear
            filter
            class="w-full"
            style="min-width: 150px;"
          />
        </div>
      </template>
      <template #cell-attivo="{ data }">
        <div @click.stop>
          <ToggleSwitch
            :modelValue="data.attivo"
            :disabled="isReadonly"
            @update:modelValue="toggleAttivo(data)"
          />
        </div>
      </template>

      <template #empty>
        <div class="app-empty-state">{{ t('common.empty_list') }}</div>
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>

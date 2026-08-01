<script setup>
// Scopo: Lista articoli configurabile
//        (`<ListaConfigurabile codice="catalogo.articoli">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente. Lista a ricerca obbligatoria: resta
//        nascosta finche' non si e' cercato. Nessun export: il dominio non ha
//        endpoint (lo scaffolding omette l'azione da se').
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticoliStore } from '../stores/articoli'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import { labelOrCode } from '../../core/utils/i18nLabel'

const emit = defineEmits(['new', 'row-click', 'manage-uom', 'manage-bom', 'manage-note'])
const { t, te } = useI18n()
const store = useArticoliStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'catalogo.nuovo_articolo',
  onNew: () => emit('new'),
  // Allineato al preset del seed (`codice asc`); lo store parte gia' da qui.
  searchTableOptions: { defaultSortField: 'codice' },
})

const attivoFilter = ref(true)
const compositoFilter = ref(null)
const tipologiaFilter = ref(null)
const gruppoFilter = ref(null)

const boolOptions = buildBoolOptions(t)
const attivoOptions = [
  { value: true, label: t('common.active') },
  { value: false, label: t('common.inactive') },
]

function onAttivoChange() {
  store.filters.attivo = attivoFilter.value
  applyFilters()
}
function onCompositoChange() {
  store.filters.is_composito = compositoFilter.value
  applyFilters()
}
function onTipologiaChange() {
  store.filters.tipo_voce_id = tipologiaFilter.value
  applyFilters()
}
function onGruppoChange() {
  store.filters.gruppo_voce_id = gruppoFilter.value
  applyFilters()
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

// Scopo: azioni di riga dell'articolo (sub-drawer gestionali).
// Capability BoM (Fase 6) letta dalla vista DB: data.puo_gestire_bom +
// data.motivo_non_gestibile_bom. Tooltip mostra il motivo quando disabled.
function manageBomTooltip(data) {
  if (data.puo_gestire_bom) return t('catalogo.gestisci_bom')
  const motivo = data.motivo_non_gestibile_bom
  if (!motivo) return t('catalogo.gestisci_bom')
  // Difensivo: se il DB introduce un nuovo motivo non mappato i18n,
  // fallback alla label generica invece di mostrare la chiave raw.
  const key = `catalogo.motivo_${motivo.toLowerCase()}`
  return labelOrCode(t, te, key, t('catalogo.gestisci_bom'))
}

function buildRowActions(data) {
  return [
    {
      key: 'manage-uom',
      label: t('catalogo.gestisci_uom'),
      icon: MANAGE_ICONS.UOM,
      command: () => emit('manage-uom', data),
    },
    {
      key: 'manage-bom',
      label: t('catalogo.gestisci_bom'),
      icon: MANAGE_ICONS.BOM,
      disabled: !data.puo_gestire_bom,
      tooltip: manageBomTooltip(data),
      command: () => emit('manage-bom', data),
    },
    {
      key: 'manage-note',
      label: t('catalogo.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => emit('manage-note', data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.ARTICOLO)
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText v-model="searchText" :placeholder="t('catalogo.search_placeholder')" />
        <Select v-model="attivoFilter" :options="attivoOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_attivo')" @change="onAttivoChange" style="width: 130px;" />
        <Select v-model="compositoFilter" :options="boolOptions" option-label="label" option-value="value"
          :placeholder="t('catalogo.filtro_composito')" show-clear @change="onCompositoChange" style="width: 160px;" />
        <LookupSelect v-model="tipologiaFilter" rel="vendite.articoli_tipologie"
          :placeholder="t('catalogo.filtro_tipologia')" show-clear @change="onTipologiaChange" style="width: 150px;" />
        <LookupSelect v-model="gruppoFilter" rel="vendite.articoli_gruppi"
          :placeholder="t('catalogo.filtro_gruppo')" show-clear @change="onGruppoChange" style="width: 150px;" />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <SearchHint v-if="!store.hasSearched && !store.loading" />

    <ListaConfigurabile
      v-show="store.hasSearched || store.loading"
      ref="listaRef"
      codice="catalogo.articoli"
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
      <template #cell-codice="{ data }">
        <span class="codice-truncate" :title="data.codice">{{ data.codice }}</span>
      </template>
      <!-- La colonna IVA porta `iva_ref_id` come campo (e' quello che il seed
           dichiara), ma a video vale l'aliquota: senza slot si vedrebbe l'id. -->
      <template #cell-iva_ref_id="{ data }">
        {{ data.iva_aliquota_iva != null ? `${data.iva_aliquota_iva}%` : '' }}
      </template>
      <template #cell-is_solo_componente="{ data }">
        <Tag :value="data.is_solo_componente ? t('common.yes') : t('common.no')"
          :severity="data.is_solo_componente ? 'info' : 'secondary'" />
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>

      <template #actions="{ data, compact }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" :force-compact="compact" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>

<style scoped>
/* Solo il codice (identificatore) tronca con ellipsis: e' un token,
   andare a capo non ha senso. La descrizione invece wrappa per parole
   in modo naturale (default browser, white-space: normal): la cella
   cresce in altezza su schermi stretti, niente sovrapposizioni. */
.codice-truncate {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

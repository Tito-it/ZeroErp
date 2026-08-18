<script setup>
// Scopo: Lista admin promo articoli configurabile
//        (`<ListaConfigurabile codice="vendite.promo_articoli">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro
//        dinamico e personalizzazione per utente.
//        STADIO 0 resolver v5: overlay temporale (articolo, uom) -> batte
//        listini e matrice categoria. Unico livello con PREZZO_FISSO.
//        Nessun export: il dominio non ha endpoint (lo scaffolding omette
//        l'azione da se', non ricevendo `exportFn`).
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePromoArticoliStore } from '../stores/promoArticoli'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'

const emit = defineEmits(['new', 'row-click'])
const { t } = useI18n()
const store = usePromoArticoliStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'vendite.promo_articoli.new',
  onNew: () => emit('new'),
  // `valido_al` DESC: regola di dominio sulle liste con date di validita'
  // (vedi lo store, che porta la stessa scelta e il perche' della direzione).
  searchTableOptions: { defaultSortField: 'valido_al', defaultSortOrder: 'desc' },
})

const attivoFilter = ref(true)
const uomFilter = ref(null)
const tipoVariazioneFilter = ref(null)

const boolOptions = buildBoolOptions(t)

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

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

useTabFreshness(store, TAB_ENTITIES.PROMO_ARTICOLI)
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
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="vendite.promo_articoli"
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
      <template #cell-articolo_codice="{ data }">
        {{ data.articolo_codice }} — {{ data.articolo_descrizione }}
      </template>
      <!-- Cella composita: il tipo da solo non basta a leggere la promo, serve
           il valore accanto. E' il motivo per cui nel seed la colonna e'
           `ordinabile=f` e la voce non sta in whitelist. -->
      <template #cell-tipo_variazione="{ data }">
        <span>{{ data.tipo_variazione }}: {{ data.valore_variazione }}</span>
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>

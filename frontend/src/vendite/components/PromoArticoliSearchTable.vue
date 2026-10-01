<script setup>
// Scopo: Lista admin promo articoli configurabile
//        (`<ListaConfigurabile codice="vendite.promo_articoli">`): colonne,
//        ordine e visibilita' dal catalogo `ui.lista_colonna`, con ritiro
//        dinamico e personalizzazione per utente.
//        STADIO 0 resolver v5: overlay temporale (articolo, uom) -> batte
//        listini e matrice categoria. Unico livello con PREZZO_FISSO.
//        Nessun export: il dominio non ha endpoint (lo scaffolding omette
//        l'azione da se', non ricevendo `exportFn`).
import { onMounted } from 'vue'
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
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'

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

// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: tipoVariazioneFilter, onChange: onTipoVariazioneChange } = bindSelect('tipo_variazione')
const { value: uomFilter, onChange: onUomChange } = bindSelect('uom_id')

const boolOptions = buildBoolOptions(t)

const tipoVariazioneOptions = [
  { value: null, label: t('common.all') },
  { value: 'PERCENTUALE', label: 'PERCENTUALE' },
  { value: 'VALORE_FISSO', label: 'VALORE_FISSO' },
  { value: 'PREZZO_FISSO', label: 'PREZZO_FISSO' }
]

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
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText
            v-model="searchText"
            class="app-filter-w-lg"
            :placeholder="t('vendite.promo_articoli.search_placeholder')"
          />
        </template>
        <LookupSelect
          v-model="uomFilter"
          class="app-filter-w-md"
          @change="onUomChange"
          rel="catalogo.unita_misura"
          :placeholder="t('vendite.promo_articoli.filter_uom')"
          showClear
        />
        <Select
          v-model="tipoVariazioneFilter"
          class="app-filter-w-sm"
          :options="tipoVariazioneOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('vendite.promo_articoli.filter_tipo_variazione')"
          @change="onTipoVariazioneChange"
        />
        <Select
          v-model="attivoFilter"
          class="app-filter-w-sm"
          :options="boolOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('common.attivo')"
          @change="onAttivoChange"
        />
      </FiltriLista>
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

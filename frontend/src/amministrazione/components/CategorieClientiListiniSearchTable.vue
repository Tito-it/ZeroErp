<script setup>
// Scopo: Matrice pricing v5 configurabile
//        (`<ListaConfigurabile codice="anagrafiche.categorie_clienti_listini">`):
//        categoria_cliente x utility x emittente x classe_utenza (opz) ->
//        listino con variazione opzionale. Colonne, ordine e visibilita' dal
//        catalogo `ui.lista_colonna`, con ritiro dinamico e personalizzazione
//        per utente. Nessun export: il dominio non ha endpoint.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCategorieClientiListiniStore } from '../stores/categorieClientiListini'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { TAB_ENTITIES } from '../../core/constants'
import { buildBoolOptions } from '../../core/utils/options'
import { useLookup } from '../../core/composables/useLookup'
import { listEmittentiFiscali } from '../api/amministrazione'
import { displayDate } from '../../core/utils/date'
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
const store = useCategorieClientiListiniStore()
const isBlocked = useInjectBlocked()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'amministrazione.matrice_categorie_listini.new_row',
  onNew: () => emit('new'),
  // `valido_al` DESC: regola di dominio sulle liste con date di validita',
  // allineato al preset del seed.
  searchTableOptions: { defaultSortField: 'valido_al', defaultSortOrder: 'desc' },
})

const emittentiLookup = useLookup(listEmittentiFiscali, { immediate: true })

const attivoFilter = ref(true)
const categoriaFilter = ref(null)
const utilityFilter = ref(null)
const emittenteFilter = ref(null)
const listinoFilter = ref(null)

const boolOptions = buildBoolOptions(t)

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

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

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
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="anagrafiche.categorie_clienti_listini"
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
      <template #cell-classe_utenza_codice="{ data }">
        {{ data.classe_utenza_codice || '—' }}
      </template>
      <!-- Cella composita «TIPO: valore»: e' il motivo per cui nel seed la
           colonna e' `ordinabile=f` e non sta in whitelist. -->
      <template #cell-tipo_variazione="{ data }">
        <span v-if="data.tipo_variazione">
          {{ data.tipo_variazione }}: {{ data.valore_variazione }}
        </span>
        <span v-else>—</span>
      </template>
      <!-- `valido_al` NULL = validita' senza scadenza: il trattino lo dice, una
           cella vuota no. Lo slot riceve il valore GREZZO (il formatter di
           serie si salta quando c'e' uno slot), quindi la data va formattata
           qui — `valido_dal`, che non ha slot, la formatta la lista. -->
      <template #cell-valido_al="{ data }">
        {{ displayDate(data.valido_al) || '—' }}
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
    </ListaConfigurabile>
    </template>
  </div>
</template>

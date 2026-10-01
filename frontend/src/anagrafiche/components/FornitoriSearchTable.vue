<script setup>
// Scopo: Lista fornitori (<ListaConfigurabile codice="anagrafiche.fornitori">).
// Scaffolding (useSearchTable + ref lista + export + pageActions + onConfigLoaded)
// centralizzato in useListaConfigurabilePage (estrazione regola del 2,
// 2026-06-02): qui restano filtri, slot e azioni di riga specifici.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFornitoriStore } from '../stores/fornitori'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { exportFornitori } from '../api/anagrafiche'
import { statoFornitoreSeverity } from '../../core/utils/severity'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import SearchHint from '../../core/components/SearchHint.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'

const emit = defineEmits(['new', 'row-click', 'soggetto', 'contatti', 'indirizzi', 'conti-bancari'])
const { t } = useI18n()
const store = useFornitoriStore()
const auth = useAuthStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded,
  pageActions, perimetroBloccato, mostraLista, mostraSearchHint,
} = useListaConfigurabilePage(store, {
  exportFn: exportFornitori,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'anagrafiche.fornitori.nuovo_fornitore',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'ragione_sociale_completa' },
})

// Filtri custom (toolbar caller).
// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_fornitore_id')

// Params export: la lista che stai guardando, dalla sede unica dello store
// (`paramsFiltro`: ricerca, filtri di dominio, ORDINAMENTO). ⚠️ Fino al
// 2026-09-18 questo file si ricostruiva i filtri a mano dai ref della toolbar
// e non mandava l'ordinamento: il file usciva sempre nell'ordine di default
// del backend, qualunque colonna l'operatore avesse cliccato. E la ricerca
// viene dallo store (debounced), non dal ref immediato: e' quella con cui la
// lista a video e' stata davvero interrogata.
function buildExportParams(format) {
  return { formato: format, ...store.paramsFiltro() }
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento Primevue).
function onRowClick(data) { emit('row-click', data) }

// Azioni di riga del fornitore (sub-drawer anagrafici). Conto bancario
// disabilitato se l'oggetto e' BLOCCATO per l'operatore (evita 403).
function buildRowActions(data) {
  const contiBlocked = auth.isObjectBlocked('anagrafiche', 'conto_bancario')
  return [
    {
      key: 'soggetto',
      label: t('anagrafiche.fornitori.gestisci_soggetto'),
      icon: MANAGE_ICONS.SOGGETTO,
      command: () => emit('soggetto', data),
    },
    {
      key: 'contatti',
      label: t('anagrafiche.contatto.gestisci_contatti'),
      icon: MANAGE_ICONS.CONTATTI,
      command: () => emit('contatti', data),
    },
    {
      key: 'indirizzi',
      label: t('anagrafiche.indirizzo_soggetto.gestisci_indirizzi'),
      icon: MANAGE_ICONS.INDIRIZZI,
      command: () => emit('indirizzi', data),
    },
    {
      key: 'conti-bancari',
      label: t('anagrafiche.conti_bancari.gestisci_conti'),
      icon: MANAGE_ICONS.CONTI_BANCARI,
      disabled: contiBlocked,
      command: () => emit('conti-bancari', data),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.FORNITORE)
// La lista parte vuota — salvo che arrivi con search precaricata da URL/context.
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
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('anagrafiche.fornitori.search_placeholder')"
            />
          </template>
          <LookupSelect
            v-model="statoFilter"
            class="app-filter-w-md"
            rel="config.stati_fornitore"
            :placeholder="t('anagrafiche.fornitori.filtro_stato')"
            show-clear
            @change="onStatoChange"
          />
        </FiltriLista>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <SearchHint v-if="mostraSearchHint" />

      <ListaConfigurabile
        ref="listaRef"
        v-show="mostraLista"
        codice="anagrafiche.fornitori"
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
        <!-- Stato fornitore: Tag colorato per severity. -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoFornitoreSeverity(data.stato_codice_interno)" />
        </template>

        <template #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </ListaConfigurabile>
    </template>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />
  </div>
</template>

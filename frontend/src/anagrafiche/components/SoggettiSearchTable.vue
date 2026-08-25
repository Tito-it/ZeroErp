<script setup>
// Scopo: Lista soggetti (<ListaConfigurabile codice="anagrafiche.soggetti">).
// Scaffolding (useSearchTable + ref lista + export + pageActions + onConfigLoaded)
// centralizzato in useListaConfigurabilePage (estrazione regola del 2,
// 2026-06-02): qui restano filtri, slot e azioni di riga specifici.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useSoggettiStore } from '../stores/soggetti'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useLookup } from '../../core/composables/useLookup'
import { lookupTipiSoggettoDettaglio } from '../../core/apiCore'
import { exportSoggetti } from '../api/anagrafiche'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import TagList from '../../core/components/TagList.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'

const emit = defineEmits(['new', 'row-click', 'contatti', 'indirizzi', 'conti-bancari'])
const { t } = useI18n()
// Navigazione verso la lista fatture (azione di riga): e' un cambio di
// pagina, non un sotto-drawer, quindi non passa dal padre come le altre voci.
const router = useRouter()
const store = useSoggettiStore()
const auth = useAuthStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded,
  pageActions, perimetroBloccato, mostraLista, mostraSearchHint,
} = useListaConfigurabilePage(store, {
  exportFn: exportSoggetti,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'anagrafiche.soggetti.nuovo_soggetto',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'ragione_sociale_completa' },
})

// Filtri custom (toolbar caller)
const tipiSoggetto = useLookup(lookupTipiSoggettoDettaglio, { immediate: true })
const tipoFilter = ref(null)

function buildExportParams(format) {
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (tipoFilter.value != null) p.tipo_soggetto_dettaglio_id = tipoFilter.value
  return p
}

function onTipoChange() {
  store.filters.tipo_soggetto_dettaglio_id = tipoFilter.value
  applyFilters()
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento Primevue).
function onRowClick(data) { emit('row-click', data) }

// Azioni di riga del soggetto (sub-drawer anagrafici). Conto bancario
// disabilitato se l'oggetto e' BLOCCATO per l'operatore (evita 403).
function buildRowActions(data) {
  const contiBlocked = auth.isObjectBlocked('anagrafiche', 'conto_bancario')
  return [
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
    // ⭐ Porta alla LISTA FATTURE filtrata sull'IDENTIFICATIVO FISCALE, non su
    // un billing account: un soggetto è una persona giuridica e può avere PIÙ
    // conti, quindi «le sue fatture» è un insieme più largo di «le fatture di
    // un conto». È la ragione per cui il backend ha due filtri distinti.
    // ⚠️ Disabilitata quando l'identificativo manca: un soggetto senza codice
    // fiscale né partita IVA non ha un criterio con cui raccogliere i suoi
    // documenti, e mandare senza filtro consegnerebbe le fatture di TUTTI.
    {
      key: 'fatture',
      label: t('vendite.fatture.vedi_fatture'),
      icon: MANAGE_ICONS.FATTURE,
      disabled: !data.id_fiscale_univoco_cf_piva,
      command: () => router.push({
        path: '/vendite/fatture',
        query: { id_fiscale: data.id_fiscale_univoco_cf_piva },
      }),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.SOGGETTO)
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
        <div class="app-page-filters" :inert="perimetroBloccato">
          <InputText
            v-model="searchText"
            :placeholder="t('anagrafiche.soggetti.search_placeholder')"
          />
          <Select
            v-model="tipoFilter"
            :options="tipiSoggetto.items.value"
            :loading="tipiSoggetto.loading.value"
            option-label="descrizione"
            option-value="id"
            :placeholder="t('anagrafiche.soggetti.filtro_tipo')"
            show-clear
            @change="onTipoChange"
          />
        </div>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <!-- Placeholder: nessuna ricerca effettuata. -->
      <SearchHint v-if="mostraSearchHint" />

      <ListaConfigurabile
        ref="listaRef"
        v-show="mostraLista"
        codice="anagrafiche.soggetti"
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
        <!-- Nessuno slot per l'Id. Fiscale: la colonna del catalogo si chiama
             `id_fiscale` e legge `id_fiscale_univoco_cf_piva` (GENERATED
             ALWAYS). Il formatter di serie legge gia' `data[campo_sorgente]`,
             cioe' lo stesso identico valore. -->

        <!-- Ruoli: TagList aggregato dal repo via jsonb_agg. -->
        <template #cell-ruoli="{ data }">
          <TagList :items="data.ruoli || []" />
        </template>

        <template #actions="{ data, compact }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" :force-compact="compact" />
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

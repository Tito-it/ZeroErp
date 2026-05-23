<script setup>
// Scopo: Lista soggetti con search e filtro tipo.
// Migrazione DEF-8 (2026-05-11) gemello clienti: il DataTable statico
// e' sostituito da <ListaConfigurabile codice="anagrafiche.soggetti">.
// La toolbar e' UNICA, esterna, con PageActionsBar standard:
// refresh + personalizza-colonne + export + nuovo (su touch finiscono
// nel kebab).
//
// Le colonne provengono dal seed BE (`ui.lista_colonna` di
// 'anagrafiche.soggetti'); il caller fornisce slot custom solo per la
// cella `ruoli` (TagList) e per le azioni (3 sub-drawer anagrafici).
//
// Allineamento store <-> config: all'evento @config-loaded sincronizziamo
// `store.filters.limit` con la `pagina_dimensione` risolta dal BE, una
// sola volta dopo il primo load.
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useSoggettiStore } from '../stores/soggetti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useFileDownload } from '../../core/composables/useFileDownload'
import { useLookup } from '../../core/composables/useLookup'
import { lookupTipiSoggettoDettaglio } from '../../core/apiCore'
import { exportSoggetti } from '../api/anagrafiche'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import TagList from '../../core/components/TagList.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'

const emit = defineEmits(['new', 'row-click', 'contatti', 'indirizzi', 'conti-bancari'])
const { t } = useI18n()
const store = useSoggettiStore()
const auth = useAuthStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'ragione_sociale_completa'
})

// Ref al ListaConfigurabile per chiamare openModal() / leggere
// dirty / colonneNuove (stato esposto via defineExpose, auto-unwrappato
// nel parent — niente `.value` extra sui ref esposti).
const listaRef = ref(null)
const dirty = computed(() => listaRef.value?.dirty ?? false)
const colonneNuove = computed(() => listaRef.value?.colonneNuove ?? 0)
const configReady = computed(() => listaRef.value?.config != null)

// Filtri custom (toolbar caller)
const tipiSoggetto = useLookup(lookupTipiSoggettoDettaglio, { immediate: true })
const tipoFilter = ref(null)

// Export DEF-1: scarica CSV o Excel con i filtri attualmente applicati.
const { download: downloadFile, loading: exportLoading } = useFileDownload()
const exportDialogVisible = ref(false)

function buildExportParams(format) {
  // NB: il query param si chiama `formato` (italiano) NON `format`.
  // `format` e' un magic parameter DRF (content-negotiation): se non ha
  // un renderer registrato per il valore passato, DRF risponde 404 prima
  // di entrare nella view.
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (tipoFilter.value != null) p.tipo_soggetto_dettaglio_id = tipoFilter.value
  return p
}

async function onExportConfirm(format) {
  const result = await downloadFile(
    () => exportSoggetti(buildExportParams(format)),
    { successMessage: t('lista_config.export_success') },
  )
  if (result !== null) exportDialogVisible.value = false
}

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: reload,
  },
  {
    key: 'personalizza-colonne',
    kind: 'utility',
    label: colonneNuove.value > 0
      ? `${t('lista_config.personalizza_colonne')} (${colonneNuove.value})`
      : t('lista_config.personalizza_colonne'),
    tooltip: colonneNuove.value > 0
      ? t('lista_config.colonne_nuove_disponibili', { n: colonneNuove.value })
      : t('lista_config.personalizza_colonne'),
    icon: MANAGE_ICONS.PERSONALIZZA,
    disabled: !configReady.value,
    command: () => listaRef.value?.openModal?.(),
  },
  {
    key: 'export',
    kind: 'utility',
    label: t('lista_config.export'),
    tooltip: t('lista_config.export_tooltip'),
    icon: MANAGE_ICONS.DOWNLOAD,
    disabled: exportLoading.value,
    command: () => { exportDialogVisible.value = true },
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('soggetti.nuovo_soggetto'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

function onTipoChange() {
  store.filters.tipo_soggetto_dettaglio_id = tipoFilter.value
  applyFilters()
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento Primevue).
function onRowClick(data) { emit('row-click', data) }

// Scopo: Allinea store.filters.limit alla pagina_dimensione risolta dal
// BE al primo load. Se il valore differisce e l'utente non ha ancora
// fetchato dati specifici, aggiorna lo store; se e' gia' partita una
// fetch precedente con limit diverso, il prossimo onPage la risolve.
const configAligned = ref(false)
function onConfigLoaded(config) {
  if (configAligned.value) return
  configAligned.value = true
  const newLimit = config?.pagina_dimensione
  if (newLimit && newLimit !== store.filters.limit) {
    store.filters.limit = newLimit
    if (store.hasSearched) store.fetchList()
  }
}

// Scopo: azioni di riga del soggetto (sub-drawer anagrafici).
// Conto bancario disabilitato se l'oggetto e' BLOCCATO per l'operatore
// (defense-in-depth UX: evita click che genererebbero 403).
function buildRowActions(data) {
  const contiBlocked = auth.isObjectBlocked('anagrafiche', 'conto_bancario')
  return [
    {
      key: 'contatti',
      label: t('contatto.gestisci_contatti'),
      icon: MANAGE_ICONS.CONTATTI,
      command: () => emit('contatti', data),
    },
    {
      key: 'indirizzi',
      label: t('indirizzo_soggetto.gestisci_indirizzi'),
      icon: MANAGE_ICONS.INDIRIZZI,
      command: () => emit('indirizzi', data),
    },
    {
      key: 'conti-bancari',
      label: t('conti_bancari.gestisci_conti'),
      icon: MANAGE_ICONS.CONTI_BANCARI,
      disabled: contiBlocked,
      command: () => emit('conti-bancari', data),
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
      <!-- Toolbar UNICA esterna (pattern lista standard frontend-standards.md):
           filtri a sinistra, PageActionsBar a destra. Su touch/tablet
           PageActionsBar collassa nel kebab. -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText
            v-model="searchText"
            :placeholder="t('soggetti.search_placeholder')"
          />
          <Select
            v-model="tipoFilter"
            :options="tipiSoggetto.items.value"
            :loading="tipiSoggetto.loading.value"
            option-label="descrizione"
            option-value="id"
            :placeholder="t('soggetti.filtro_tipo')"
            show-clear
            @change="onTipoChange"
          />
        </div>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <Tag
              v-if="dirty"
              :value="t('lista_config.stato_temporanea')"
              severity="warn"
              v-tooltip.bottom="t('lista_config.stato_temporanea_tooltip')"
            />
            <Tag
              v-else-if="configReady"
              :value="t('lista_config.stato_salvata')"
              severity="success"
            />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <!-- Placeholder: nessuna ricerca effettuata. Il <ListaConfigurabile>
           resta montato anche con dati vuoti per preservare lo stato
           config; lo SearchHint copre solo visualmente lo stato iniziale. -->
      <SearchHint v-if="!store.hasSearched && !store.loading" />

      <ListaConfigurabile
        ref="listaRef"
        v-show="store.hasSearched || store.loading"
        codice="anagrafiche.soggetti"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="paginatorProps.first / paginatorProps.rows + 1"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        @page="onPage"
        @sort="onSort"
        @row-click="onRowClick"
        @config-loaded="onConfigLoaded"
      >
        <!-- CF / P.IVA: legge il campo `id_fiscale_univoco_cf_piva`,
             colonna GENERATED ALWAYS sulla tabella `anagrafiche.soggetti`
             che fa il COALESCE CF/P.IVA (pattern allineato a clienti).
             Lo slot bypassa il default formatter perche' il catalogo
             attuale ha `campo_sorgente='codice_fiscale'`: il brief DB
             `brief-db-def8-soggetti-fix-id-fiscale.md` aggiornera' il
             seed a `campo_sorgente='id_fiscale_univoco_cf_piva'`; dopo
             quel fix lo slot continuera' a funzionare in modo
             equivalente, ma puo' essere rimosso lasciando il default. -->
        <template #cell-codice_fiscale="{ data }">
          {{ data.id_fiscale_univoco_cf_piva }}
        </template>

        <!-- Ruoli: TagList aggregato dal repo via jsonb_agg. -->
        <template #cell-ruoli="{ data }">
          <TagList :items="data.ruoli || []" />
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

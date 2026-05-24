<script setup>
// Scopo: Lista clienti con search, filtro utility e stato.
// Migrazione Blocco E5 (2026-05-07) + refactor toolbar 2026-05-08:
// il DataTable statico e' sostituito da <ListaConfigurabile codice="
// anagrafiche.clienti">. La toolbar e' UNICA, esterna, con
// PageActionsBar standard: refresh + nuovo + personalizza-colonne (via
// `listaRef.openModal()` esposto). Tag stato e ReadonlyBadge in
// #suffix. Su touch/tablet tutto finisce nel kebab.
//
// Le colonne provengono dal seed BE (`ui.lista_colonna` di
// 'anagrafiche.clienti'); il caller fornisce slot custom solo per le
// celle con rendering complesso (codice fiscale fallback PIVA,
// sosp_riatt composta, tag stato).
//
// Allineamento store <-> config:
//   - all'evento @config-loaded sincronizziamo `store.filters.limit`
//     con la `pagina_dimensione` risolta dal BE, una sola volta dopo
//     il primo load (le successive modifiche utente al paginator si
//     applicano via onPage di useSearchTable).
import { computed, ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClientiStore } from '../stores/clienti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useFileDownload } from '../../core/composables/useFileDownload'
import { exportClienti } from '../api/anagrafiche'
import { MANAGE_ICONS, TIPO_RUOLO, TAB_ENTITIES } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { statoClienteSeverity } from '../../core/utils/severity'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'

const emit = defineEmits(['new', 'row-click', 'soggetto', 'contatti', 'indirizzi', 'conti-bancari', 'contratti'])
const { t } = useI18n()
const store = useClientiStore()
const auth = useAuthStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'ragione_sociale_completa'
})

// Ref al ListaConfigurabile per chiamare openModal() / leggere
// dirty / colonneNuove (stato esposto via defineExpose).
//
// Vue 3 `defineExpose` con `<script setup>` auto-unwrappa i ref:
// dal parent `listaRef.value.dirty` restituisce direttamente il valore
// booleano, NON il ref. Niente `.value` extra qui — sarebbe `.value` su
// un primitivo/oggetto normale e verrebbe sempre `undefined` (causando
// computed bloccati sul fallback di default).
const listaRef = ref(null)
const dirty = computed(() => listaRef.value?.dirty ?? false)
const colonneNuove = computed(() => listaRef.value?.colonneNuove ?? 0)
const configReady = computed(() => listaRef.value?.config != null)

// Filtri custom (toolbar caller)
const utilityFilter = ref(null)
const statoFilter = ref(null)

// Export DEF-1: scarica CSV o Excel con i filtri attualmente applicati.
// Il dialog `ExportDialog` chiede il formato all'utente; il
// `useFileDownload` poi triggera il download del Blob (su Chrome/Edge
// HTTPS apre il dialog "Salva con nome" nativo OS, altrove fallback al
// download standard). Errori (es. 422 oltre 10.000 righe) sono
// notificati dall'interceptor axios via useApiHandler.
const { download: downloadFile, loading: exportLoading } = useFileDownload()
const exportDialogVisible = ref(false)

function buildExportParams(format) {
  // NB: il query param si chiama `formato` (italiano) NON `format`.
  // `format` e' un magic parameter DRF (content-negotiation): se non ha
  // un renderer registrato per il valore passato, DRF risponde 404
  // PRIMA di entrare nella view. Convenzione di progetto: usare nomi
  // italiani per query param custom evita collisioni con DRF default.
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (utilityFilter.value != null) p.utility_id = utilityFilter.value
  if (statoFilter.value != null) p.stato_cliente_id = statoFilter.value
  return p
}

async function onExportConfirm(format) {
  const result = await downloadFile(
    () => exportClienti(buildExportParams(format)),
    { successMessage: t('lista_config.export_success') },
  )
  // Chiudi il dialog solo a download avviato con successo. Su errore
  // (es. 422 cap superato), useApiHandler ha mostrato il toast: il
  // dialog resta aperto cosi' l'utente puo' raffinare i filtri e
  // riprovare senza ricliccare "Esporta".
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
    tooltip: t('clienti.nuovo_cliente'),
    icon: MANAGE_ICONS.ADD,
    hideWhenReadonly: true,
    command: () => emit('new'),
  },
])

function onUtilityChange() {
  store.filters.utility_id = utilityFilter.value
  applyFilters()
}

function onStatoChange() {
  store.filters.stato_cliente_id = statoFilter.value
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

// Scopo: azioni di riga del cliente (sub-drawer anagrafici + contratti).
// Ogni sub-drawer con model_permission proprio disabilita la sua voce se
// l'oggetto e' BLOCCATO per l'operatore (defense-in-depth UX: evita click
// che genererebbero 403).
function buildRowActions(data) {
  const contiBlocked = auth.isObjectBlocked('anagrafiche', 'conto_bancario')
  return [
    {
      key: 'soggetto',
      label: t('clienti.gestisci_soggetto'),
      icon: MANAGE_ICONS.SOGGETTO,
      command: () => emit('soggetto', data),
    },
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
    {
      key: 'contratti',
      label: t('contratti.gestisci_contratti'),
      icon: MANAGE_ICONS.CONTRATTI,
      command: () => emit('contratti', data),
    },
  ]
}

// Scopo: Mostra data sospensione o riattivazione (l'ultima in ordine cronologico).
function dataSospRiatt(row) {
  const sosp = row.data_sospensione
  const riatt = row.data_riattivazione
  if (!sosp && !riatt) return null
  if (sosp && !riatt) return { label: 'clienti.col_sospeso_il', date: sosp }
  if (!sosp && riatt) return { label: 'clienti.col_riattivato_il', date: riatt }
  return sosp > riatt
    ? { label: 'clienti.col_sospeso_il', date: sosp }
    : { label: 'clienti.col_riattivato_il', date: riatt }
}

useTabFreshness(store, TAB_ENTITIES.CLIENTE)
// La lista parte vuota — salvo che arrivi con search precaricata da URL/context.
onMounted(() => {
  if (searchText.value) {
    store.fetchList()
  }
})
</script>

<template>
  <div class="app-tab-content">
    <!-- Livello oggetto BLOCCATO: sostituisce toolbar + lista con pannello dedicato -->
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- Toolbar UNICA esterna (pattern lista standard frontend-standards.md):
           filtri a sinistra, PageActionsBar a destra con refresh + personalizza
           + nuovo. Su touch/tablet PageActionsBar collassa nel kebab. -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText
            v-model="searchText"
            :placeholder="t('clienti.search_placeholder')"
            style="width: 320px;"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('clienti.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_cliente"
            :placeholder="t('clienti.filtro_stato')"
            show-clear
            @change="onStatoChange"
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
        codice="anagrafiche.clienti"
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
        <!-- Cell custom: codice fiscale o, in fallback, partita IVA. Il seed
             BE puo' nominare la colonna come 'codice_fiscale' (campo_sorgente
             aggiornato a `id_fiscale_univoco_cf_piva` post-Blocco F.2). -->
        <template #cell-codice_fiscale="{ data }">
          {{ data.id_fiscale_univoco_cf_piva || data.codice_fiscale || data.partita_iva }}
        </template>

        <!-- Date semplici: il default formatter del componente
             (displayDate via formato='date_short') si applica
             automaticamente se il seed BE imposta `formato`. Slot espliciti
             qui per robustezza nel caso il seed ometta il `formato`. -->
        <template #cell-data_attivazione="{ value }">{{ displayDate(value) }}</template>
        <template #cell-data_chiusura="{ value }">{{ displayDate(value) }}</template>
        <template #cell-data_sospensione="{ value }">{{ displayDate(value) }}</template>
        <template #cell-data_riattivazione="{ value }">{{ displayDate(value) }}</template>

        <!-- Sospensione/Riattivazione: colonna composta che mostra l'ultima
             tra le due date con etichetta semantica. Renderizzata solo se
             il seed dichiara la colonna 'sosp_riatt' (post-Blocco F.2). -->
        <template #cell-sosp_riatt="{ data }">
          <span v-if="data.data_sospensione || data.data_riattivazione">
            <small class="text-color-secondary">{{ t(dataSospRiatt(data).label) }}</small><br>
            {{ displayDate(dataSospRiatt(data).date) }}
          </span>
        </template>

        <!-- Stato cliente: tag colorato per severity. -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoClienteSeverity(data.stato_codice)" />
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

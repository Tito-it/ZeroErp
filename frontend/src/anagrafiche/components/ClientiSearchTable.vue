<script setup>
// Scopo: Lista clienti (<ListaConfigurabile codice="anagrafiche.clienti">).
// Scaffolding (useSearchTable + ref lista + export + pageActions + onConfigLoaded)
// centralizzato in useListaConfigurabilePage (estrazione regola del 2,
// 2026-06-02): qui restano filtri, slot e azioni di riga specifici.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useClientiStore } from '../stores/clienti'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { exportClienti } from '../api/anagrafiche'
import { MANAGE_ICONS, TIPO_RUOLO, TAB_ENTITIES } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { statoClienteSeverity } from '../../core/utils/severity'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
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
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'

const emit = defineEmits(['new', 'row-click', 'soggetto', 'contatti', 'indirizzi', 'conti-bancari', 'contratti'])
const { t } = useI18n()
// Navigazione verso la lista fatture (azione di riga): e' un cambio di
// pagina, non un sotto-drawer, quindi non passa dal padre come le altre voci.
const router = useRouter()
const store = useClientiStore()
const auth = useAuthStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded,
  pageActions, perimetroBloccato, mostraLista, mostraSearchHint,
} = useListaConfigurabilePage(store, {
  exportFn: exportClienti,
  getExportParams: (fmt) => buildExportParams(fmt),
  newTooltipKey: 'anagrafiche.clienti.nuovo_cliente',
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'ragione_sociale_completa' },
})

// Filtri custom (toolbar caller)
// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_cliente_id')

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

// Scopo: azioni di riga del cliente (sub-drawer anagrafici + contratti).
// Ogni sub-drawer con model_permission proprio disabilita la sua voce se
// l'oggetto e' BLOCCATO per l'operatore (evita click che genererebbero 403).
function buildRowActions(data) {
  const contiBlocked = auth.isObjectBlocked('anagrafiche', 'conto_bancario')
  return [
    {
      key: 'soggetto',
      label: t('anagrafiche.clienti.gestisci_soggetto'),
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
    {
      key: 'contratti',
      label: t('vendite.contratti.gestisci_contratti'),
      icon: MANAGE_ICONS.CONTRATTI,
      command: () => emit('contratti', data),
    },
    // ⭐ Porta alla LISTA FATTURE già filtrata su questo conto. Non apre un
    // sotto-drawer: è una navigazione, e la lista dichiara a video da dove
    // arriva e come togliere il filtro.
    // ⛔ `billing_account_id` e NON `id`: su questa vista sono due colonne
    // diverse e non coincidono mai (misurato: 0 righe su 21). Usare `id`
    // avrebbe dato un filtro valido e SEMPRE VUOTO — «questo cliente non ha
    // fatture» su ogni cliente, senza nessun errore.
    {
      key: 'fatture',
      label: t('vendite.fatture.vedi_fatture'),
      icon: MANAGE_ICONS.FATTURE,
      command: () => router.push({
        path: '/vendite/fatture',
        query: { ba: data.billing_account_id, eti: data.ragione_sociale_completa },
      }),
    },
  ]
}

// Scopo: Mostra data sospensione o riattivazione (l'ultima in ordine cronologico).
function dataSospRiatt(row) {
  const sosp = row.data_sospensione
  const riatt = row.data_riattivazione
  if (!sosp && !riatt) return null
  if (sosp && !riatt) return { label: 'anagrafiche.clienti.col_sospeso_il', date: sosp }
  if (!sosp && riatt) return { label: 'anagrafiche.clienti.col_riattivato_il', date: riatt }
  return sosp > riatt
    ? { label: 'anagrafiche.clienti.col_sospeso_il', date: sosp }
    : { label: 'anagrafiche.clienti.col_riattivato_il', date: riatt }
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
      <div class="app-page-toolbar">
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('anagrafiche.clienti.search_placeholder')"
            />
          </template>
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            class="app-filter-w-md"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('anagrafiche.clienti.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <LookupSelect
            v-model="statoFilter"
            class="app-filter-w-md"
            rel="config.stati_cliente"
            :placeholder="t('anagrafiche.clienti.filtro_stato')"
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

      <!-- Placeholder: nessuna ricerca effettuata. -->
      <SearchHint v-if="mostraSearchHint" />

      <ListaConfigurabile
        ref="listaRef"
        v-show="mostraLista"
        codice="anagrafiche.clienti"
        :azioni-inline="6"
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
             `id_fiscale` e legge `id_fiscale_univoco_cf_piva`, che il formatter
             di serie risolve da solo. Il fallback `|| codice_fiscale ||
             partita_iva` era codice morto: la colonna generata e' NULL solo
             quando lo sono entrambe le sorgenti. -->

        <!-- Date semplici (slot espliciti per robustezza se il seed omette `formato`). -->
        <template #cell-data_attivazione="{ value }">{{ displayDate(value) }}</template>
        <template #cell-data_chiusura="{ value }">{{ displayDate(value) }}</template>
        <template #cell-data_sospensione="{ value }">{{ displayDate(value) }}</template>
        <template #cell-data_riattivazione="{ value }">{{ displayDate(value) }}</template>

        <!-- Sospensione/Riattivazione: colonna composta che mostra l'ultima delle due date. -->
        <template #cell-sosp_riatt="{ data }">
          <span v-if="data.data_sospensione || data.data_riattivazione">
            <small class="app-text-muted">{{ t(dataSospRiatt(data).label) }}</small><br>
            {{ displayDate(dataSospRiatt(data).date) }}
          </span>
        </template>

        <!-- Stato cliente: tag colorato per severity. -->
        <template #cell-stato="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoClienteSeverity(data.stato_codice_interno)" />
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

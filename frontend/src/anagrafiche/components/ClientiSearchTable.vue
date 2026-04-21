<script setup>
// Scopo: DataTable paginata clienti con search, filtro utility e stato.
// Riusabile da: ClientiView, futuro ricerca clienti in altri domini.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClientiStore } from '../stores/clienti'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { MANAGE_ICONS, TIPO_RUOLO } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { statoClienteSeverity } from '../../core/utils/severity'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import NewButton from '../../core/components/NewButton.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import SearchHint from '../../core/components/SearchHint.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'

const emit = defineEmits(['new', 'row-click', 'contatti', 'indirizzi', 'conti-bancari', 'contratti'])
const { t } = useI18n()
const store = useClientiStore()
const auth = useAuthStore()
const isBlocked = useInjectBlocked()
const { searchText, onPage, onSort, applyFilters, reload, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'ragione_sociale_completa'
})

// Filtri
const utilityFilter = ref(null)
const statoFilter = ref(null)

function onUtilityChange() {
  store.filters.utility_id = utilityFilter.value
  applyFilters()
}

function onStatoChange() {
  store.filters.stato_cliente_id = statoFilter.value
  applyFilters()
}

function onRowClick(event) { emit('row-click', event.data) }

// Scopo: azioni di riga del cliente (sub-drawer anagrafici + contratti).
// Ogni sub-drawer con model_permission proprio disabilita la sua voce se
// l'oggetto e' BLOCCATO per l'operatore (defense-in-depth UX: evita click
// che genererebbero 403).
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

useTabFreshness(store, 'cliente')
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
      <div class="app-page-actions">
        <ReadonlyBadge />
        <ReloadButton @click="reload" />
        <NewButton :tooltip="t('clienti.nuovo_cliente')" @click="emit('new')" />
      </div>
    </div>

    <!-- Placeholder: nessuna ricerca effettuata -->
    <SearchHint v-if="!store.hasSearched && !store.loading" />

    <DataTable
      v-show="store.hasSearched || store.loading"
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy
      removable-sort
      striped-rows
      scrollable
      scrollHeight="flex"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      selection-mode="single"
      data-key="id"
    >
      <Column field="soggetto_codice" :header="t('clienti.col_cd_soggetto')" sortable style="width: 140px;" />
      <Column field="ba_codice" :header="t('clienti.col_ba_codice')" sortable style="width: 140px;" />
      <Column field="ragione_sociale_completa" :header="t('clienti.col_ragione_sociale')" sortable style="width: 180px;" />
      <Column field="codice_fiscale" :header="t('clienti.col_id_fiscale')" sortable style="width: 160px;">
        <template #body="{ data }">{{ data.codice_fiscale || data.partita_iva }}</template>
      </Column>
      <Column field="utility_descrizione" :header="t('clienti.col_utility')" sortable style="width: 130px;" />
      <Column field="data_attivazione" :header="t('clienti.col_data_attivazione')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_attivazione) }}</template>
      </Column>
      <Column field="data_chiusura" :header="t('clienti.col_data_chiusura')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_chiusura) }}</template>
      </Column>
      <Column :header="t('clienti.col_sosp_riatt')" style="width: 130px;">
        <template #body="{ data }">
          <span v-if="data.data_sospensione || data.data_riattivazione">
            <small class="text-color-secondary">{{ t(dataSospRiatt(data).label) }}</small><br>
            {{ displayDate(dataSospRiatt(data).date) }}
          </span>
        </template>
      </Column>
      <Column field="stato_descrizione" :header="t('clienti.col_stato')" sortable style="width: 110px;">
        <template #body="{ data }">
          <Tag :value="data.stato_descrizione" :severity="statoClienteSeverity(data.stato_codice)" />
        </template>
      </Column>
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>
    </template>
  </div>
</template>

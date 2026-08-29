<script setup>
// Scopo: LA LISTA DEI DOCUMENTI FISCALI — la settima del ciclo attivo, sullo
//        stampo delle sei sorelle (`<ListaConfigurabile codice="vendite.fatture">`,
//        scaffolding in `useListaConfigurabilePage`).
//
// ⭐ Perché esiste. Fino al 2026-08-24 la fattura era l'unico documento del
//    ciclo attivo SENZA la sua lista: si raggiungeva solo passando da un lotto,
//    da un cruscotto o da un collegamento. Il caso che l'ha resa urgente —
//    rilievo di Tid, nato sul campo — è una commessa di competenza giugno
//    fatturata ad agosto: il documento porta la data di agosto, e chi lo cerca
//    lo cerca per QUELLA, non per la competenza della commessa.
//
// ⚠️ SOLA LETTURA: nessun «Nuovo». La fattura si produce dalla pipeline di
//    fatturazione, non da un form — per questo `useListaConfigurabilePage` è
//    chiamato senza `onNew`, e dal 2026-07-31 il BB in quel caso il pulsante
//    non lo mette affatto.
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import LineagePraticaCell from '../_shared/lineage/LineagePraticaCell.vue'
import LineageFaseTag from '../_shared/lineage/LineageFaseTag.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { DATE_FORMAT, TAB_ENTITIES, TIPO_RUOLO } from '../../core/constants'
import { naturaDocSeverity, statoDocFiscaleSeverity } from '../../core/utils/severity'
import { exportFatture } from '../api/fatture'
import { useFattureStore } from '../stores/fatture'

const emit = defineEmits(['row-click'])
const { t } = useI18n()
const store = useFattureStore()
const isBlocked = useInjectBlocked()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions,
  perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportFatture,
  getExportParams: (fmt) => buildExportParams(fmt),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// --- Filtri (toolbar caller), legati allo store dal BB ---
const { bindSelect, bindDate } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_codice_interno')
const { value: naturaFilter, onChange: onNaturaChange } = bindSelect('natura_doc_codice')
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
const { value: dataDaFilter, onChange: onDataDaChange } = bindDate('data_da')
const { value: dataAlFilter, onChange: onDataAlChange } = bindDate('data_a')

// ⭐ La natura è un vocabolario CHIUSO e cortissimo (tre valori): un Select
// statico, non un lookup — un round-trip per tre voci è lavoro sprecato, e il
// vocabolario è lo stesso che il BE filtra su `natura_doc_codice`.
const opzioniNatura = [
  { value: 'FATTURA', label: t('vendite.fatture.natura_fattura') },
  { value: 'NOTA_CREDITO', label: t('vendite.fatture.natura_nota_credito') },
  { value: 'NOTA_DEBITO', label: t('vendite.fatture.natura_nota_debito') },
]

// Params export: i filtri vivono in `store.filters`, `search` dal ref immediato.
// ⚠️ Il file È la lista: ogni filtro a video deve arrivare anche qui, o si
// consegna a qualcuno un elenco più largo di quello che stava guardando.
function buildExportParams(format) {
  const p = { formato: format }
  if (searchText.value?.trim()) p.search = searchText.value.trim()
  if (store.filters.stato_codice_interno != null) p.stato_codice_interno = store.filters.stato_codice_interno
  if (store.filters.natura_doc_codice != null) p.natura_doc_codice = store.filters.natura_doc_codice
  if (store.filters.utility_id != null) p.utility_id = store.filters.utility_id
  if (store.filters.billing_account_id != null) p.billing_account_id = store.filters.billing_account_id
  if (store.filters.data_da) p.data_da = store.filters.data_da
  if (store.filters.data_a) p.data_a = store.filters.data_a
  if (store.filters.order_by) {
    p.order_by = store.filters.order_by
    p.order_dir = store.filters.order_dir || 'desc'
  }
  return p
}

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

// ------------------------------------------------- arrivo da un COLLEGAMENTO
// ⭐ Le liste SOGGETTI e CLIENTI mandano qui con una voce del kebab: la prima
//    per identificativo fiscale, la seconda per id del billing account.
//    ⚠️ Sono due criteri DIVERSI e non intercambiabili: un soggetto può avere
//    più billing account, quindi «le fatture del soggetto» è un insieme più
//    largo di «le fatture del conto».
//
// ⛔ È il PRIMO filtro da URL dell'applicazione — i quattro `route.query` che
//    esistevano aprono un drawer (`?open=`) o scelgono una scheda. Da qui il
//    banner: una lista che mostra 8 righe su 18 senza dire perché è la stessa
//    trappola che questo dominio ha già pagato più volte — un elenco filtrato e
//    uno completo si leggono uguali.
const route = useRoute()
const router = useRouter()
const collegamento = ref(null)

const etichettaCollegamento = computed(() => {
  if (!collegamento.value) return ''
  return collegamento.value.idFiscale
    ? t('vendite.fatture.collegamento_soggetto', { valore: collegamento.value.idFiscale })
    : t('vendite.fatture.collegamento_cliente', { valore: collegamento.value.etichetta })
})

// Scopo: torna alla lista di sempre — toglie il criterio, rimette il pavimento
//        temporale standard e ripulisce l'URL, così un refresh non lo riapplica.
function rimuoviCollegamento() {
  collegamento.value = null
  router.replace({ query: {} })
  store.rimuoviCollegamento()
}

useTabFreshness(TAB_ENTITIES.FATTURA, () => store.fetchList())
onMounted(() => {
  const q = route.query
  const idFiscale = typeof q.id_fiscale === 'string' ? q.id_fiscale.trim() : ''
  // ⚠️ `Number.isFinite` e non un cast nudo: `?ba=abc` diventerebbe `NaN` e
  //    finirebbe nella query come filtro illeggibile invece di essere ignorato.
  const ba = Number(q.ba)
  if (idFiscale) {
    collegamento.value = { idFiscale }
    store.applicaCollegamento({ idFiscale })
    return
  }
  if (Number.isFinite(ba) && ba > 0) {
    collegamento.value = {
      billingAccountId: ba,
      // L'etichetta viaggia nell'URL perché chi manda la conosce già: farla
      // risolvere qui costerebbe una chiamata per mostrare un nome che il
      // chiamante aveva in mano.
      etichetta: (typeof q.eti === 'string' && q.eti) || String(ba),
    }
    store.applicaCollegamento({ billingAccountId: ba })
    return
  }
  store.fetchList()
})
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <!-- ⛔ IL BANNER NON È DECORAZIONE. Arrivando da un collegamento la lista
           mostra un sottoinsieme, e senza dirlo si legge come l'elenco intero:
           «questo cliente ha 8 fatture» invece di «ne sto mostrando 8 delle
           18 che ci sono». È lo stesso difetto — l'elenco filtrato che sembra
           completo — che questo dominio ha già pagato sulle segnalazioni e
           sulle righe di routine del giornale.
           ⭐ E dichiara anche ciò che il collegamento TOGLIE: il pavimento
           temporale, senza il quale un soggetto con documenti vecchi
           riceverebbe «Nessuna fattura». -->
      <Message
        v-if="collegamento"
        severity="info"
        class="app-mb-1"
        :closable="false"
      >
        <div class="app-page-filters">
          <span>{{ etichettaCollegamento }}</span>
          <Button
            text
            size="small"
            :label="t('vendite.fatture.collegamento_rimuovi')"
            icon="pi pi-times"
            @click="rimuoviCollegamento"
          />
        </div>
      </Message>

      <!-- Toolbar UNICA esterna (pattern lista standard). -->
      <div class="app-page-toolbar">
        <div class="app-page-filters" :inert="perimetroBloccato">
          <InputText
            v-model="searchText"
            :placeholder="t('vendite.fatture.search_placeholder')"
            style="width: 260px;"
          />
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_fiscale"
            value-field="codice_interno"
            :placeholder="t('vendite.fatture.filtro_stato')"
            show-clear
            style="width: 170px;"
            @change="onStatoChange"
          />
          <Select
            v-model="naturaFilter"
            :options="opzioniNatura"
            option-label="label"
            option-value="value"
            :placeholder="t('vendite.fatture.filtro_natura')"
            show-clear
            style="width: 170px;"
            @update:model-value="onNaturaChange"
          />
          <UtilityPerRuoloSelect
            v-model="utilityFilter"
            :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
            :placeholder="t('vendite.fatture.filtro_utility')"
            show-clear
            apply-default
            @change="onUtilityChange"
          />
          <!-- ⚠️ È la data del DOCUMENTO, non la competenza della commessa:
               è la ragione per cui questa lista esiste. -->
          <DatePicker v-model="dataDaFilter" :placeholder="t('common.data_da')"
            :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
            @date-select="onDataDaChange" @clear-click="onDataDaChange" />
          <DatePicker v-model="dataAlFilter" :placeholder="t('common.data_a')"
            :date-format="DATE_FORMAT" show-icon show-button-bar style="width: 150px;"
            @date-select="onDataAlChange" @clear-click="onDataAlChange" />
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
        codice="vendite.fatture"
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
        <!-- ⚠️ I nomi degli slot sono i `codice` di QUESTA lista a catalogo, e
             NON coincidono con quelli delle sorelle: qui il DB ha chiamato le
             colonne `natura_doc_descrizione` / `stato_descrizione` /
             `pratica_numero`, sui contratti si chiamano `natura` / `stato` /
             `pratica`. Uno slot col nome sbagliato non dà nessun errore: la
             cella ripiega sul valore grezzo e i Tag colorati spariscono in
             silenzio. Il nome si legge dal seed, mai dalla lista sorella.

             Numero: NULL finché il documento non è numerato. Mai una cella
             vuota — su un documento fiscale un vuoto si legge come dato perso
             invece che come stato del processo. -->
        <template #cell-numero="{ data }">{{ data.numero || '—' }}</template>

        <!-- ⚠️ La nota di credito non è un'anomalia: severity neutra, mai
             `danger`. Il totale negativo si mostra com'è, perché è il documento
             a essere di segno opposto. -->
        <template #cell-natura_doc_descrizione="{ data }">
          <Tag
            v-if="data.natura_doc_codice_interno"
            :value="data.natura_doc_descrizione || data.natura_doc_codice_interno"
            :severity="naturaDocSeverity(data.natura_doc_codice_interno)"
          />
          <span v-else>—</span>
        </template>

        <template #cell-stato_descrizione="{ data }">
          <Tag
            :value="data.stato_descrizione"
            :severity="statoDocFiscaleSeverity(data.stato_codice_interno)"
          />
        </template>

        <!-- Colonne lineage, come sulle sorelle. -->
        <template #cell-pratica_numero="{ data }">
          <LineagePraticaCell
            :pratica-id="data.pratica_id"
            :pratica-numero="data.pratica_numero"
            :n-pratiche="data.n_pratiche"
          />
        </template>
        <template #cell-fase="{ data }">
          <LineageFaseTag :fase="data.fase" />
        </template>

        <template #empty>
          <div class="app-empty-state">
            <i class="pi pi-file" />
            <p>{{ t('vendite.fatture.nessuna_fattura') }}</p>
          </div>
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

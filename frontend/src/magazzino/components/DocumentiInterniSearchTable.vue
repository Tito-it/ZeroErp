<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA LISTA del documento interno di magazzino — inventari o rettifiche,
//        UN componente con la famiglia in prop (Q-1): lista configurabile
//        (`magazzino.inventari` 70 / `magazzino.rettifiche` 73), filtri
//        (magazzino, stato, date, ricerca), «Nuovo», export, azioni di riga.
//
// ⭐ Tutto cio' che distingue le due famiglie sta in `FAMIGLIE[famiglia]`
//    (`vocabolari.js`): codice lista, radice i18n, evento cross-tab, il
//    parametro del deep-link verso il registro. Qui non c'e' nessun
//    `if (famiglia === …)`.
//
// ⚠️ Le azioni di riga: «Elimina» solo su una BOZZA — il DB e' la porta
//    (`E_MAG_DOCUMENTO_NON_ELIMINABILE`, 409) e qui non si PROPONE cio' che
//    verrebbe rifiutato; «Movimenti» solo su un POSTED, perche' prima di
//    allora il registro non ha niente di questo documento. Sono azioni non
//    applicabili, non azioni spente: si nascondono (`visible`), come da
//    standard delle azioni di riga — il motivo non e' uno stato che cambia
//    sotto le mani, e' la natura della riga. Le TRANSIZIONI di stato non stanno
//    in lista: vivono nel drawer, dove arrivano le capability (R-1).
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useInjectBlocked, useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { documentoInternoSeverity } from '../../core/utils/severity'
import { exportDocumenti } from '../api/magazzino'
import { useEtichetteMagazzino } from '../etichette'
import { useDocumentiInterniStore } from '../stores/documentiInterni'
import { FAMIGLIE, STATO_DOCUMENTO } from '../vocabolari'
import FiltroPeriodo from '../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'

const props = defineProps({
  famiglia: {
    type: String,
    required: true,
    validator: (v) => v in FAMIGLIE,
  },
})
const emit = defineEmits(['new', 'row-click'])

const { t } = useI18n()
const router = useRouter()
// ⚠️ La famiglia si legge UNA volta al setup: la vista e' montata per rotta
//    (`:key="$route.path"`), e le due porte sono due istanze diverse.
const f = FAMIGLIE[props.famiglia]
const store = useDocumentiInterniStore(f.codice)
const isBlocked = useInjectBlocked()
const isReadonly = useInjectReadonly()
const { execute } = useApiHandler()
const { confirmAction } = useConfirmAction()
const { statoDocumento, opzioniStatoDocumento } = useEtichetteMagazzino()
const opzioniStato = opzioniStatoDocumento()

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded,
  pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: (params) => exportDocumenti(f.codice, params),
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
  newTooltipKey: `${f.i18n}.nuovo`,
  newLabelKey: `${f.i18n}.nuovo`,
  onNew: () => emit('new'),
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// --- Filtri ---
const { bindSelect, bindPeriodo } = useStoreFilterBindings(store, applyFilters)
const { value: magazzinoFilter, onChange: onMagazzinoChange } = bindSelect('magazzino_id')
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato')
// Il periodo e' UN filtro con due estremi: un binding, un componente.
const periodo = bindPeriodo()

function onRowClick(data) { emit('row-click', data) }

// Scopo: elimina una BOZZA dopo conferma. Il rifiuto — se non e' piu' in
//        bozza — arriva dal database con la sua frase. ⛔ Nessun refetch qui:
//        il verbo dello store emette l'evento e `useTabFreshness` ricarica.
function onElimina(riga) {
  confirmAction({
    header: t('confirm.delete_title'),
    message: t(`${f.i18n}.conferma_elimina`, { id: riga.id }),
    danger: true,
    onAccept: () => execute(
      () => store.elimina(riga.id),
      { successMessage: t(`${f.i18n}.eliminato`) },
    ),
  })
}

// Scopo: apre il registro gia' filtrato sui movimenti di QUESTO documento
//        (deep-link `?inventario_id=` / `?rettifica_id=`).
function apriMovimenti(riga) {
  router.push({ name: 'magazzino-movimenti', query: { [f.filtroMovimenti]: riga.id } })
}

function buildRowActions(riga) {
  return [
    {
      key: 'movimenti',
      label: t('magazzino.documenti_interni.movimenti'),
      icon: NAV_ICONS.MOVIMENTI,
      visible: riga.stato === STATO_DOCUMENTO.POSTED,
      command: () => apriMovimenti(riga),
    },
    {
      key: 'elimina',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      // ⛔ In sola lettura si NASCONDE (permesso, non stato): `RowActionsMenu`
      //    non conosce `hideWhenReadonly`, il filtro va fatto qui.
      visible: !isReadonly.value && riga.stato === STATO_DOCUMENTO.DRAFT,
      command: () => onElimina(riga),
    },
  ]
}

// Il numero di pulsanti inline della colonna azioni: e' l'unica larghezza che
// il catalogo non conosce, e la dichiara chi scrive `buildRowActions`.
const AZIONI_INLINE = 2

useTabFreshness(store, f.tabEntity)

// Lista con floor data standard: parte piena al mount.
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
              :placeholder="t(`${f.i18n}.search_placeholder`)"
            />
          </template>
          <LookupSelect
            v-model="magazzinoFilter"
            class="app-filter-w-md"
            rel="magazzino.magazzini"
            :placeholder="t('magazzino.documenti_interni.filtro_magazzino')"
            show-clear
            show-code
            @change="onMagazzinoChange"
          />
          <Select
            v-model="statoFilter"
            class="app-filter-w-md"
            :options="opzioniStato"
            option-label="label"
            option-value="value"
            :placeholder="t('magazzino.documenti_interni.filtro_stato')"
            show-clear
            @update:model-value="onStatoChange"
          />
          <FiltroPeriodo :periodo="periodo" />
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
        :codice="f.listaCodice"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        :azioni-inline="AZIONI_INLINE"
        @page="onPage"
        @sort="onSort"
        @row-click="onRowClick"
        @config-loaded="onConfigLoaded"
      >
        <!-- Lo stato e' un codice GREZZO (nessuna tabella di stato a DB):
             l'etichetta e' i18n fail-visible, il colore la mappa in severity.js. -->
        <template #cell-stato="{ data }">
          <Tag :value="statoDocumento(data.stato)" :severity="documentoInternoSeverity(data.stato)" />
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

<script setup>
// Scopo: Coda di lavoro resi (righe reso CONFERMATE). Due varianti via prop
//        `coda`: 'accreditare' (righe a credito, predisposizione slice nota
//        di credito) e 'riconsegnare' (righe per ri-consegna con copertura
//        pendente, colonne resa/ri-consegnata/residua + stato derivato).
//        Fetch dalle viste dedicate BE (scope emittente automatico), colonne
//        fisse (niente ListaConfigurabile: liste di RIGHE, non di documenti).
//        Stato pagina/fetch via BB `usePagedDashFetch` (adottato 2026-07-14,
//        ok Tid): guard anti-race, `loaded` per empty-state onesto,
//        applyPageEvent per il paginator lazy; l'adapter converte
//        {page, page_size} nei limit/offset degli endpoint coda.
//        Click riga -> apre il reso nel drawer.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

import { usePagedDashFetch } from '../../../core/composables/usePagedDashFetch'
import { MANAGE_ICONS, PAGINATION } from '../../../core/constants'
import { displayDate } from '../../../core/utils/date'
import { formatNumber } from '../../../core/utils/format'
import { statoRiconsegnaSeverity } from '../../../core/utils/severity'
import { listDaAccreditare, listDaRiconsegnare } from '../api/resiApi'

const { t } = useI18n()

const props = defineProps({
  coda: {
    type: String,
    required: true,
    validator: (v) => ['accreditare', 'riconsegnare'].includes(v),
  },
})
const emit = defineEmits(['apri-reso'])

const isRiconsegna = props.coda === 'riconsegnare'
const fetchCoda = isRiconsegna ? listDaRiconsegnare : listDaAccreditare

// Sezione paginata standard (BB): l'adapter mappa la paginazione page-based
// del BB sui limit/offset degli endpoint coda (envelope {results, count}).
const { items, count, page, pageSize, loading, loaded, fetch, applyPageEvent } =
  usePagedDashFetch(
    ({ page: p, page_size: size }) =>
      fetchCoda({ limit: size, offset: (p - 1) * size }),
  )

function onPage(event) {
  applyPageEvent(event)
  fetch()
}

onMounted(fetch)
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters" />
      <Button :icon="MANAGE_ICONS.RELOAD" text rounded size="small"
        class="app-reload-btn" :disabled="loading"
        v-tooltip.bottom="t('common.reload_list')" @click="fetch" />
    </div>

    <DataTable :value="items" lazy paginator paginator-position="top"
      :rows="pageSize" :total-records="count" :first="(page - 1) * pageSize"
      :rows-per-page-options="PAGINATION.ROWS_OPTIONS"
      :loading="loading" striped-rows size="small" class="app-datatable"
      data-key="resi_riga_id" @page="onPage"
      @row-click="(e) => emit('apri-reso', e.data.reso_id)"
      :row-hover="true">
      <Column field="reso_numero" :header="t('vendite.resi.col_numero')" style="width: 110px;">
        <template #body="{ data }">{{ data.reso_numero || '—' }}</template>
      </Column>
      <Column field="data" :header="t('vendite.resi.col_data')" style="width: 100px;">
        <template #body="{ data }">{{ displayDate(data.data) }}</template>
      </Column>
      <Column field="destinatario_denominazione" :header="t('vendite.resi.col_destinatario')" />
      <Column field="descrizione" :header="t('vendite.resi.riga_articolo')" />
      <Column field="ddt_numero" :header="t('vendite.resi.col_ddt_origine')" style="width: 110px;" />

      <!-- Coda accrediti: quantita' resa. -->
      <Column v-if="!isRiconsegna" field="qta_operativa" :header="t('vendite.resi.riga_quantita')" style="width: 100px;">
        <template #body="{ data }">{{ formatNumber(data.qta_operativa ?? data.quantita) }}</template>
      </Column>
      <Column v-if="!isRiconsegna" field="motivo" :header="t('vendite.resi.riga_motivo')" />

      <!-- Coda ri-consegne: copertura resa/ri-consegnata/residua + stato derivato. -->
      <Column v-if="isRiconsegna" field="qta_resa" :header="t('vendite.resi.riconsegna_col_resa')" style="width: 100px;">
        <template #body="{ data }">{{ formatNumber(data.qta_resa) }}</template>
      </Column>
      <Column v-if="isRiconsegna" field="qta_riconsegnata" :header="t('vendite.resi.riconsegna_col_riconsegnata')" style="width: 120px;">
        <template #body="{ data }">{{ formatNumber(data.qta_riconsegnata) }}</template>
      </Column>
      <Column v-if="isRiconsegna" field="qta_residua" :header="t('vendite.resi.riconsegna_col_residua')" style="width: 100px;">
        <template #body="{ data }">{{ formatNumber(data.qta_residua) }}</template>
      </Column>
      <Column v-if="isRiconsegna" field="stato_riconsegna" :header="t('vendite.resi.riga_stato_riconsegna')" style="width: 130px;">
        <template #body="{ data }">
          <Tag :value="t(`vendite.resi.riconsegna_stato.${data.stato_riconsegna}`)"
            :severity="statoRiconsegnaSeverity(data.stato_riconsegna)" />
        </template>
      </Column>

      <template #empty>
        <div v-if="loaded" class="app-empty-state">
          {{ t(isRiconsegna ? 'vendite.resi.riconsegna_nessuna_riga' : 'common.no_results') }}
        </div>
      </template>
    </DataTable>
  </div>
</template>

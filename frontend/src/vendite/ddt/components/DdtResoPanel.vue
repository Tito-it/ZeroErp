<script setup>
// Scopo: Pannello "Crea reso" dentro il drawer DDT (solo stato CONSEGNATO —
// non si rende cio' che non e' stato consegnato; il pulsante manuale «Reso»
// e' stato rimosso dalla matrice: questo pannello E' il percorso). Macchina
// selezione/quantità via BB `useRigheSelezioneQta` (regola del 2 — condivisa
// con evasione ordini e ri-spedizione reso); qui in piu': tipo reso + motivo
// per riga (mappe extra seedate in onLoaded). Quantità in unità OPERATIVA;
// payload sempre ESPLICITO (mai null: la creazione parziale è la norma).
// Il reso nasce DRAFT: nessun router-push, si rifinisce/conferma dal tab Resi.
// L'over-return resta rifiutato dal guard DB (E_RESO_QTA_SUPERA_CONSEGNATO).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'

import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useGlobalLookup } from '../../../core/composables/useGlobalLookup'
import { useNotify } from '../../../core/composables/useNotify'
import { lookupCodici } from '../../../core/apiCore'
import { formatNumber } from '../../../core/utils/format'
import { useRigheSelezioneQta } from '../../_shared/righe/useRigheSelezioneQta'
import { getRigheDdtPerReso } from '../../resi/api/resiApi'
import { useResiStore } from '../../resi/stores/resi'
import { TIPO_RESO } from '../../resi/constants'

const { t } = useI18n()
const resiStore = useResiStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

const props = defineProps({
  ddtId: { type: Number, required: true },
  // In readonly puro il pannello e' consuntivo (righe visibili, no azione).
  readonly: { type: Boolean, default: false },
})
// `reso-creato` notifica il drawer padre (aggiorna i residui rendibili).
const emit = defineEmits(['reso-creato'])

// Input extra per riga (keyed per ddt_riga_id): tipo reso + motivo libero.
const tipoMap = ref({})
const motivoMap = ref({})

// Tipi reso dal lookup generico (cache modulo-level condivisa, stessa chiave
// del LookupSelect rel="config.tipi_reso": transform envelope di default).
const { items: tipiReso, load: loadTipiReso } = useGlobalLookup(
  'config.tipi_reso',
  () => lookupCodici('config.tipi_reso'),
)
// Default: A_CREDITO se presente, altrimenti il primo tipo attivo del lookup
// (fail-soft: un rename del codice_interno non deve lasciare le righe senza
// tipo e far fallire la creazione in modo muto).
const tipoDefaultId = computed(
  () => tipiReso.value.find(x => x.codice_interno === TIPO_RESO.A_CREDITO)?.id
    ?? tipiReso.value[0]?.id
    ?? null,
)

// Scopo: residuo rendibile OPERATIVO della riga DDT (0 se esaurito).
function residuoDi(r) {
  return Number(r.qta_resa_residua_operativa) || 0
}

// Macchina selezione/quantità (BB). Le due fetch (lookup tipi + righe) sono
// indipendenti: in parallelo (latenza = max, non somma).
const {
  righe, loadingRighe, selected, qtaMap, righeSelezionabili,
  loadRighe, buildPayloadRighe,
  isSelectable, isSelected, toggleRow, toggleAll, allSelected, anySelected,
} = useRigheSelezioneQta({
  fetchRighe: async () => {
    if (!props.ddtId) return []
    const [, res] = await Promise.all([
      loadTipiReso(),
      getRigheDdtPerReso(props.ddtId),
    ])
    return res.data.data || []
  },
  residuoDi,
  rowKey: 'ddt_riga_id',
  readonly: () => props.readonly,
  onLoaded: (rows) => {
    const tipo = {}
    const motivo = {}
    for (const r of rows) {
      tipo[r.ddt_riga_id] = tipoDefaultId.value
      motivo[r.ddt_riga_id] = ''
    }
    tipoMap.value = tipo
    motivoMap.value = motivo
  },
})

watch(() => props.ddtId, loadRighe, { immediate: true })
defineExpose({ loadRighe })

// Scopo: crea il reso in bozza con le righe selezionate. Il payload viaggia
// in unita' OPERATIVA (il trigger DB deriva la base). A valle: toast + emit
// al padre + reload residui.
function onCrea() {
  if (!selected.value.length) return
  const payloadRighe = buildPayloadRighe(
    (r, qta) => ({
      ddt_riga_id: r.ddt_riga_id,
      tipo_reso_id: tipoMap.value[r.ddt_riga_id],
      qta_operativa: String(qta),
      motivo: motivoMap.value[r.ddt_riga_id]?.trim() || null,
    }),
    { filterRow: (r) => tipoMap.value[r.ddt_riga_id] != null },
  )

  if (!payloadRighe.length) {
    notify.warn(t('vendite.resi.crea_qta_nulla'))
    return
  }

  confirmAction({
    message: t('vendite.resi.crea_conferma', { righe: payloadRighe.length }),
    onAccept: async () => {
      const result = await execute(
        () => resiStore.create({ ddt_id: props.ddtId, righe: payloadRighe }),
      )
      if (result === null) return
      // Il reso nasce in DRAFT: numero assegnato solo alla conferma.
      notify.success(t('vendite.resi.reso_creato'))
      await loadRighe()
      emit('reso-creato', { resoId: result?.id ?? null })
    },
  })
}
</script>

<template>
  <div class="form-grid">
    <h4 style="margin: 0;">{{ t('vendite.resi.crea_titolo') }}</h4>
    <p style="margin: 0; font-size: 0.85rem; color: var(--text-color-secondary);">
      {{ t('vendite.resi.crea_intro') }}
    </p>

    <DataTable v-if="righe.length" :value="righe"
      data-key="ddt_riga_id" striped-rows size="small" class="app-datatable"
      :loading="loadingRighe" scrollable scrollHeight="280px">
      <!-- Checkbox custom (no selectionMode: PrimeVue 4 renderebbe spuntabili
           anche le righe con residuo esaurito): disabled per riga da
           isSelectable, colonna nascosta quando non resta nulla da rendere. -->
      <Column v-if="!readonly && righeSelezionabili.length" headerStyle="width: 3rem">
        <template #header>
          <Checkbox :model-value="allSelected" binary
            :indeterminate="anySelected" @update:model-value="toggleAll" />
        </template>
        <template #body="{ data }">
          <Checkbox :model-value="isSelected(data)" binary
            :disabled="!isSelectable(data)" @update:model-value="toggleRow(data)" />
        </template>
      </Column>
      <Column :header="t('vendite.resi.riga_articolo')">
        <template #body="{ data }">
          {{ data.articolo_codice }} — {{ data.descrizione }}
        </template>
      </Column>
      <Column :header="t('vendite.resi.crea_col_consegnata')" style="width: 110px;">
        <template #body="{ data }">
          {{ formatNumber(data.qta_operativa) }} {{ data.uom_codice }}
        </template>
      </Column>
      <Column :header="t('vendite.resi.crea_col_gia_resa')" style="width: 100px;">
        <template #body="{ data }">{{ formatNumber(data.qta_gia_resa) }}</template>
      </Column>
      <Column :header="t('vendite.resi.crea_col_residuo')" style="width: 100px;">
        <template #body="{ data }">{{ formatNumber(data.qta_resa_residua_operativa) }}</template>
      </Column>
      <Column :header="t('vendite.resi.crea_col_qta')" style="width: 150px;">
        <template #body="{ data }">
          <InputNumber v-if="!readonly && residuoDi(data) > 0"
            v-model="qtaMap[data.ddt_riga_id]" :min="0" :max="residuoDi(data)"
            :min-fraction-digits="0" :max-fraction-digits="6"
            input-style="width: 6.5rem;" />
          <span v-else>{{ formatNumber(qtaMap[data.ddt_riga_id]) }}</span>
        </template>
      </Column>
      <Column :header="t('vendite.resi.crea_col_tipo')" style="width: 190px;">
        <template #body="{ data }">
          <Select v-if="!readonly && residuoDi(data) > 0"
            v-model="tipoMap[data.ddt_riga_id]" :options="tipiReso"
            option-label="descrizione" option-value="id" size="small" />
        </template>
      </Column>
      <Column :header="t('vendite.resi.crea_col_motivo')" style="width: 180px;">
        <template #body="{ data }">
          <InputText v-if="!readonly && residuoDi(data) > 0"
            v-model="motivoMap[data.ddt_riga_id]" size="small" style="width: 100%;" />
        </template>
      </Column>
    </DataTable>
    <div v-else-if="!loadingRighe" style="color: var(--text-color-secondary); font-style: italic;">
      {{ t('vendite.resi.crea_nessuna_riga') }}
    </div>

    <Button v-if="!readonly && righeSelezionabili.length" icon="pi pi-replay"
      :label="t('vendite.resi.crea_bottone')"
      severity="warn" size="small" :loading="loading"
      :disabled="selected.length === 0" @click="onCrea"
      style="align-self: flex-start;" />
  </div>
</template>

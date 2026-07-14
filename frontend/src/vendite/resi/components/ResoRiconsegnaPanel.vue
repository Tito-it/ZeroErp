<script setup>
// Scopo: Pannello "Ri-spedizione" dentro il drawer RESO (solo CONFERMATO).
// Macchina selezione/quantità via BB `useRigheSelezioneQta` (regola del 2 —
// condivisa con evasione ordini e crea-reso DDT). Righe reso per RI-CONSEGNA
// con copertura pendente; quantità in unità BASE (contratto
// fn_genera_ddt_riconsegna: [{resi_riga_id, qta}]). Selezione completa e
// intatta ⇒ righe null (il BE ri-spedisce tutta la copertura residua,
// race-proof). L'over-ri-spedizione resta rifiutata dal guard DB del ponte
// (E_RESO_RICONSEGNA_SUPERA_RESO).
import { watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'

import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useNotify } from '../../../core/composables/useNotify'
import { formatNumber } from '../../../core/utils/format'
import { useRigheSelezioneQta } from '../../_shared/righe/useRigheSelezioneQta'
import { useResiStore } from '../stores/resi'

const { t } = useI18n()
const store = useResiStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

const props = defineProps({
  resoId: { type: Number, required: true },
  // In readonly puro il pannello e' consuntivo: righe visibili, niente azione.
  readonly: { type: Boolean, default: false },
})
// `generato` notifica il drawer padre che un DDT di ri-consegna e' nato.
const emit = defineEmits(['generato'])

// Macchina selezione/quantità (BB): righe = solo RESO_PER_RICONSEGNA;
// residuo = copertura residua in unità BASE.
const {
  righe, loadingRighe, selected, qtaMap, righeSelezionabili,
  coversAllResiduo, loadRighe, buildPayloadRighe,
} = useRigheSelezioneQta({
  fetchRighe: async () => {
    if (!props.resoId) return []
    const rows = await store.loadRighe(props.resoId)
    return (rows || []).filter(r => r.riapre_residuo)
  },
  residuoDi: (r) => Number(r.qta_residua) || 0,
  readonly: () => props.readonly,
})

watch(() => props.resoId, loadRighe, { immediate: true })
defineExpose({ loadRighe })

const generaLabel = computed(() =>
  coversAllResiduo.value
    ? t('vendite.resi.riconsegna_genera_tutto')
    : t('vendite.resi.riconsegna_genera_selezione'),
)

// Scopo: genera il DDT di ri-consegna dalle righe selezionate. null = tutta
// la copertura residua; altrimenti array esplicito {resi_riga_id, qta} in
// unita' BASE. A valle: toast + emit al padre + reload righe.
function onGenera() {
  if (!selected.value.length) return
  const usaTutto = coversAllResiduo.value
  const payloadRighe = usaTutto
    ? null
    : buildPayloadRighe((r, qta) => ({ resi_riga_id: r.id, qta: String(qta) }))

  if (!usaTutto && !payloadRighe.length) {
    notify.warn(t('vendite.resi.riconsegna_qta_nulla'))
    return
  }

  confirmAction({
    message: t('vendite.resi.riconsegna_conferma', {
      righe: usaTutto ? righeSelezionabili.value.length : payloadRighe.length,
    }),
    onAccept: async () => {
      const result = await execute(
        () => store.generaRiconsegna(props.resoId, { righe: payloadRighe }),
      )
      if (result === null) return
      // Il DDT di ri-consegna nasce in DRAFT: si rifinisce dal tab DDT.
      notify.success(t('vendite.resi.riconsegna_generato'))
      await loadRighe()
      emit('generato', { ddtId: result?.ddt_id ?? null })
    },
  })
}
</script>

<template>
  <div class="form-grid">
    <h4 style="margin: 0;">{{ t('vendite.resi.riconsegna_titolo') }}</h4>
    <p style="margin: 0; font-size: 0.85rem; color: var(--text-color-secondary);">
      {{ t('vendite.resi.riconsegna_intro') }}
    </p>

    <DataTable v-if="righe.length" :value="righe" v-model:selection="selected"
      data-key="id" striped-rows size="small" class="app-datatable"
      :loading="loadingRighe" scrollable scrollHeight="240px">
      <Column v-if="!readonly" selectionMode="multiple" headerStyle="width: 3rem" />
      <Column :header="t('vendite.resi.riga_articolo')">
        <template #body="{ data }">
          {{ data.articolo_codice }} — {{ data.descrizione }}
        </template>
      </Column>
      <Column :header="t('vendite.resi.riconsegna_col_resa')" style="width: 100px;">
        <template #body="{ data }">{{ formatNumber(data.quantita) }}</template>
      </Column>
      <Column :header="t('vendite.resi.riconsegna_col_riconsegnata')" style="width: 120px;">
        <template #body="{ data }">{{ formatNumber(data.qta_riconsegnata) }}</template>
      </Column>
      <Column :header="t('vendite.resi.riconsegna_col_residua')" style="width: 100px;">
        <template #body="{ data }">{{ formatNumber(data.qta_residua) }}</template>
      </Column>
      <Column :header="t('vendite.resi.riconsegna_col_qta')" style="width: 170px;">
        <template #body="{ data }">
          <InputNumber v-if="!readonly && (Number(data.qta_residua) || 0) > 0"
            v-model="qtaMap[data.id]" :min="0" :max="Number(data.qta_residua) || 0"
            :min-fraction-digits="0" :max-fraction-digits="6"
            input-style="width: 7rem;" />
          <span v-else>{{ formatNumber(qtaMap[data.id]) }}</span>
        </template>
      </Column>
    </DataTable>
    <div v-else-if="!loadingRighe" style="color: var(--text-color-secondary); font-style: italic;">
      {{ t('vendite.resi.riconsegna_nessuna_riga') }}
    </div>

    <Button v-if="!readonly && righeSelezionabili.length" icon="pi pi-send"
      :label="generaLabel"
      severity="info" size="small" :loading="loading"
      :disabled="selected.length === 0" @click="onGenera"
      style="align-self: flex-start;" />
  </div>
</template>

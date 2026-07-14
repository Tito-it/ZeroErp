<script setup>
// Scopo: Pannello "Genera DDT" (evasione) dentro il drawer ORDINE. Macchina
// selezione/quantità via BB `useRigheSelezioneQta` (estratto 2026-07-14,
// regola del 2 alla 3ª copia, ok Tid — condiviso con crea-reso DDT e
// ri-spedizione reso). Tabella righe ordine con residuo per riga
// (`qta_residua_operativa` dal fulfillment multi-DDT aggregato, unità
// OPERATIVE), selezione multipla + quantità da evadere (default = RESIDUO) e
// azione unica "Genera DDT". Selezione completa e intatta ⇒ righe null (il BE
// evade il residuo effettivo: race-proof su evasioni concorrenti).
// L'over-shipping resta rifiutato dal guard DB (E_QTA_SUPERA_RESIDUO).
// Nessun router-push: il DDT nasce DRAFT e si apre dal suo tab.
import { watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useNotify } from '../../../core/composables/useNotify'
import { useTabEvents } from '../../../core/composables/useTabEvents'
import { useRigheSelezioneQta } from '../../_shared/righe/useRigheSelezioneQta'
import { useOrdiniStore } from '../stores/ordini'
import { generaDdtFromOrdine } from '../api/ordiniApi'
import { TAB_ENTITIES } from '../../../core/constants'
import { formatNumber } from '../../../core/utils/format'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'

const { t } = useI18n()
const store = useOrdiniStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()
const { emitDataChanged } = useTabEvents()

const props = defineProps({
  ordineId: { type: Number, required: true },
  // In readonly puro (LETTURA/split/forzato) il pannello e' consuntivo: mostra
  // le righe ma niente selezione/azione.
  readonly: { type: Boolean, default: false },
})
// `evaso` notifica il drawer padre che un DDT e' stato generato: ricarica il
// detail (lo stato ordine e' proiettato dal BE) e propaga il DDT id.
const emit = defineEmits(['evaso'])

// Scopo: residuo operativo della riga (0 se campo assente/riga gia' evasa).
function residuoDi(r) {
  return Number(r.qta_residua_operativa) || 0
}

// Macchina selezione/quantità (BB): le righe gia' completamente evase restano
// visibili come consuntivo (ordinata/evasa), le evadibili sono preselezionate
// con qta = residuo.
const {
  righe, loadingRighe, selected, qtaMap,
  righeSelezionabili: righeEvadibili,
  coversAllResiduo: evadeTuttoResiduo,
  loadRighe, buildPayloadRighe,
} = useRigheSelezioneQta({
  fetchRighe: async () => {
    if (!props.ordineId) return []
    return (await store.loadRighe(props.ordineId)) || []
  },
  residuoDi,
  readonly: () => props.readonly,
})

watch(() => props.ordineId, loadRighe, { immediate: true })

// Etichetta azione: "tutto il residuo" quando la selezione e' completa e
// intatta; altrimenti "selezione".
const generaLabel = computed(() =>
  evadeTuttoResiduo.value
    ? t('vendite.ordini.evasione_genera_tutto')
    : t('vendite.ordini.evasione_genera_selezione'),
)

// Scopo: genera il DDT dalle righe selezionate. Se evade tutto il residuo invia
// null (il BE risolve il residuo dal fulfillment); altrimenti invia l'array
// esplicito {ordine_riga_id, qta_da_evadere}. A valle: toast + emit al padre +
// notifica il tab DDT (refresh) + reload residui.
function onGenera() {
  if (!selected.value.length) return
  const usaResiduo = evadeTuttoResiduo.value
  const payloadRighe = usaResiduo
    ? null
    : buildPayloadRighe((r, qta) => ({ ordine_riga_id: r.id, qta_da_evadere: qta }))

  if (!usaResiduo && !payloadRighe.length) {
    notify.warn(t('vendite.ordini.evasione_qta_nulla'))
    return
  }

  confirmAction({
    message: t('vendite.ordini.evasione_conferma', {
      righe: usaResiduo ? righeEvadibili.value.length : payloadRighe.length,
    }),
    onAccept: async () => {
      const result = await execute(
        () => generaDdtFromOrdine(props.ordineId, payloadRighe),
      )
      if (result === null) return
      const ddtId = result?.ddt_id ?? null
      // Il DDT nasce in DRAFT: il numero e' assegnato solo all'emissione.
      notify.success(t('vendite.ordini.ddt_generato'))
      if (ddtId) emitDataChanged(TAB_ENTITIES.DDT, ddtId)
      await loadRighe()
      emit('evaso', { ddtId })
    },
  })
}
</script>

<template>
  <div class="form-grid">
    <div class="evasione-header">
      <h4 style="margin: 0;">{{ t('vendite.ordini.evasione_titolo') }}</h4>
    </div>
    <p style="margin: 0; font-size: 0.85rem; color: var(--text-color-secondary);">
      {{ t('vendite.ordini.evasione_intro') }}
    </p>

    <DataTable v-if="righe.length" :value="righe" v-model:selection="selected"
      data-key="id" striped-rows size="small" class="app-datatable"
      :loading="loadingRighe" scrollable scrollHeight="240px">
      <Column v-if="!readonly" selectionMode="multiple" headerStyle="width: 3rem" />
      <Column :header="t('vendite.ordini.riga_articolo')">
        <template #body="{ data }">
          {{ data.articolo_codice }} — {{ data.descrizione }}
        </template>
      </Column>
      <Column :header="t('vendite.ordini.evasione_col_qta_ordinata')" style="width: 120px;">
        <template #body="{ data }">
          {{ formatNumber(data.qta_operativa) }} {{ data.uom_codice }}
        </template>
      </Column>
      <Column :header="t('vendite.ordini.evasione_col_qta_evasa')" style="width: 110px;">
        <template #body="{ data }">
          {{ formatNumber(data.qta_evasa_operativa) }}
        </template>
      </Column>
      <Column :header="t('vendite.ordini.evasione_col_qta_residua')" style="width: 110px;">
        <template #body="{ data }">
          {{ formatNumber(data.qta_residua_operativa) }}
        </template>
      </Column>
      <Column :header="t('vendite.ordini.evasione_col_qta_da_evadere')" style="width: 160px;">
        <template #body="{ data }">
          <InputNumber v-if="!readonly && residuoDi(data) > 0"
            v-model="qtaMap[data.id]" :min="0" :max="residuoDi(data)"
            :min-fraction-digits="0" :max-fraction-digits="6"
            input-style="width: 7rem;" />
          <span v-else>{{ formatNumber(qtaMap[data.id]) }}</span>
        </template>
      </Column>
    </DataTable>
    <div v-else-if="!loadingRighe" style="color: var(--text-color-secondary); font-style: italic;">
      {{ t('vendite.ordini.evasione_nessuna_riga') }}
    </div>

    <Button v-if="!readonly && righeEvadibili.length" icon="pi pi-send"
      :label="generaLabel"
      severity="info" size="small" :loading="loading"
      :disabled="selected.length === 0" @click="onGenera"
      style="align-self: flex-start;" />
  </div>
</template>

<style scoped>
.evasione-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
</style>

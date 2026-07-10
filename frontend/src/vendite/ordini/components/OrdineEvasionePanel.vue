<script setup>
// Scopo: Pannello "Genera DDT" (evasione) dentro il drawer ORDINE. Gemello di
// "genera ordine da preventivo" (PreventiviSmistamentoPanel): tabella righe
// ordine con selezione multipla + quantita' da evadere per riga + azione unica
// "Genera DDT". L'evasione instrada verso il DDT (DRAFT); lo stato ordine viene
// proiettato dal BE (CONFERMATO / PARZIALMENTE_EVASO / EVASO). Nessun
// router-push: il DDT nasce DRAFT e si apre dal suo tab (emitDataChanged).
//
// Residuo per riga: il BE espone `qta_evasa_operativa` e
// `qta_residua_operativa` su GET /righe/ (fulfillment multi-DDT aggregato,
// unita' operative). La tabella mostra ordinata/evasa/residuo e il default di
// "qta da evadere" e' il RESIDUO (mai l'ordinato: su un ordine gia'
// parzialmente evaso l'ordinato supererebbe il residuo). Quando la selezione
// copre tutte le righe evadibili con quantita' intatte si invia `null` (il BE
// evade il residuo effettivo: race-proof su evasioni concorrenti); altrimenti
// l'array esplicito. L'over-shipping resta comunque rifiutato dal guard DB
// (E_QTA_SUPERA_RESIDUO).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { useNotify } from '../../../core/composables/useNotify'
import { useTabEvents } from '../../../core/composables/useTabEvents'
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

const righe = ref([])
const loadingRighe = ref(false)
const selected = ref([])
// Quantita' da evadere per riga (keyed per riga id), default = RESIDUO.
const qtaMap = ref({})

// Scopo: residuo operativo della riga (0 se campo assente/riga gia' evasa).
function residuoDi(r) {
  return Number(r.qta_residua_operativa) || 0
}

// Righe con residuo > 0: le uniche selezionabili/evadibili. Le righe gia'
// completamente evase restano visibili come consuntivo (ordinata/evasa).
const righeEvadibili = computed(() => righe.value.filter(r => residuoDi(r) > 0))

// Scopo: carica le righe dell'ordine e preseleziona le evadibili (evadi-tutto
// il residuo di default). Ogni riga parte con qta_da_evadere = residuo.
async function loadRighe() {
  if (!props.ordineId) return
  loadingRighe.value = true
  try {
    const rows = await store.loadRighe(props.ordineId)
    righe.value = rows || []
    const map = {}
    for (const r of righe.value) map[r.id] = residuoDi(r)
    qtaMap.value = map
    selected.value = props.readonly ? [] : righe.value.filter(r => residuoDi(r) > 0)
  } finally {
    loadingRighe.value = false
  }
}

watch(() => props.ordineId, loadRighe, { immediate: true })

// Tutte le righe EVADIBILI selezionate E nessuna quantita' ritoccata rispetto
// al residuo → si delega al BE l'evasione del residuo (null, race-proof).
const evadeTuttoResiduo = computed(() => {
  const evadibili = righeEvadibili.value
  if (evadibili.length === 0) return false
  const selIds = new Set(selected.value.map(r => r.id))
  if (selIds.size !== evadibili.length) return false
  return evadibili.every(
    r => selIds.has(r.id) && Number(qtaMap.value[r.id]) === residuoDi(r),
  )
})

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
// notifica il tab DDT (refresh) + reload righe.
function onGenera() {
  const sel = selected.value
  if (!sel.length) return
  const usaResiduo = evadeTuttoResiduo.value
  const payloadRighe = usaResiduo
    ? null
    : sel
        .map(r => ({ ordine_riga_id: r.id, qta_da_evadere: Number(qtaMap.value[r.id]) || 0 }))
        .filter(r => r.qta_da_evadere > 0)

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

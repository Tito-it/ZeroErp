<script setup>
// Scopo: Dialog "DDT ri-spedizione" del drawer RESO (solo CONFERMATO), aperta
// dal pulsante in barra azioni (2026-07-25, decisione Tid — stessa forma di
// «Genera reso» del DDT e «Genera DDT» dell'ordine: le azioni di processo
// stanno in alto, non in coda al contenuto).
//
// Macchina selezione/quantità via BB `useRigheSelezioneQta` (regola del 2 —
// condivisa con evasione ordini e crea-reso DDT). Righe reso per RI-CONSEGNA
// con copertura pendente; quantità in unità BASE (contratto
// fn_genera_ddt_riconsegna: [{resi_riga_id, qta}]). Selezione completa e
// intatta ⇒ righe null (il BE ri-spedisce tutta la copertura residua,
// race-proof). L'over-ri-spedizione resta rifiutata dal guard DB del ponte
// (E_RESO_RICONSEGNA_SUPERA_RESO).
//
// PARZIALE = NORMA, NON ECCEZIONE: qui `preselezione` resta 'tutto' (a
// differenza del crea-reso). Ri-spedire tutto il residuo è l'esito atteso —
// la merce da ri-consegnare è già determinata dal reso, non è una scelta
// dell'operatore — e la selezione intatta abilita il payload `null`
// race-proof. Una quantità minore genera un DDT parziale e LASCIA il resto
// pendente: la riga resta in lista con `qta_residua` ridotta e si genera un
// altro DDT quando serve (fn_genera_ddt_riconsegna salta le righe a residuo
// esaurito ed è ri-eseguibile).
import { watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Checkbox from 'primevue/checkbox'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'

import AppDialog from '../../../../core/components/AppDialog.vue'
import { useApiHandler } from '../../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../../core/composables/useConfirmAction'
import { useNotify } from '../../../../core/composables/useNotify'
import { formatNumber } from '../../../../core/utils/format'
import { useRigheSelezioneQta } from '../../../_shared/righe/useRigheSelezioneQta'
import { useResiStore } from '../../stores/resi'

const { t } = useI18n()
const store = useResiStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()
const notify = useNotify()

const props = defineProps({
  visible: { type: Boolean, required: true },
  resoId: { type: Number, required: true },
  // In readonly puro la dialog e' consuntiva: righe visibili, niente azione.
  readonly: { type: Boolean, default: false },
})
// `generato` notifica il drawer padre che un DDT di ri-consegna e' nato.
const emit = defineEmits(['update:visible', 'generato'])

// Macchina selezione/quantità (BB): righe = solo RESO_PER_RICONSEGNA;
// residuo = copertura residua in unità BASE.
const {
  righe, loadingRighe, selected, qtaMap, righeSelezionabili,
  coversAllResiduo, loadRighe, buildPayloadRighe,
  isSelectable, isSelected, toggleRow, toggleAll, allSelected, anySelected,
} = useRigheSelezioneQta({
  fetchRighe: async () => {
    if (!props.resoId) return []
    const rows = await store.loadRighe(props.resoId)
    return (rows || []).filter(r => r.riapre_residuo)
  },
  residuoDi: (r) => Number(r.qta_residua) || 0,
  readonly: () => props.readonly,
})

// Fetch lazy: all'apertura (e a ogni riapertura, cosi' la copertura residua
// resta fresca dopo una ri-spedizione parziale appena generata).
watch(
  () => [props.visible, props.resoId],
  ([visible]) => { if (visible && props.resoId) loadRighe() },
  { immediate: true },
)

// L'etichetta dice quale delle due semantiche parte: tutta la copertura
// residua (payload null, race-proof) o la sola selezione esplicita.
const generaLabel = computed(() =>
  coversAllResiduo.value
    ? t('vendite.resi.riconsegna_genera_tutto')
    : t('vendite.resi.riconsegna_genera_selezione'),
)

// Footer di sola chiusura quando non c'e' nulla da ri-spedire: readonly puro
// (consuntivo) o copertura gia' completa.
const soloChiusura = computed(
  () => props.readonly || righeSelezionabili.value.length === 0,
)

function close() {
  emit('update:visible', false)
}

// Scopo: genera il DDT di ri-consegna dalle righe selezionate. null = tutta
// la copertura residua; altrimenti array esplicito {resi_riga_id, qta} in
// unita' BASE. A valle: toast + emit al padre + chiusura.
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
      emit('generato', { ddtId: result?.ddt_id ?? null })
      close()
    },
  })
}
</script>

<template>
  <!-- `readonly` esplicito = quello PURO del chiamante: la dialog e' lanciata da
       un drawer locked-by-stato (reso CONFERMATO) e senza override il FormFooter
       erediterebbe readonly=true nascondendo il pulsante di generazione — pur
       essendo la ri-spedizione un'azione legittima proprio in quello stato. -->
  <AppDialog
    :visible="visible"
    width="xl"
    :header="t('vendite.resi.riconsegna_titolo')"
    :readonly="readonly"
    :loading="loading"
    :close-only="soloChiusura"
    :save-disabled="selected.length === 0"
    :save-label="generaLabel"
    @update:visible="emit('update:visible', $event)"
    @save="onGenera"
    @cancel="close"
  >
    <div class="form-grid">
      <p style="margin: 0; font-size: 0.85rem; color: var(--text-color-secondary);">
        {{ t('vendite.resi.riconsegna_intro') }}
      </p>

      <DataTable v-if="righe.length" :value="righe"
        data-key="id" striped-rows size="small" class="app-datatable"
        :loading="loadingRighe" scrollable scrollHeight="360px">
        <!-- Checkbox custom (no selectionMode: PrimeVue 4 renderebbe spuntabili
             anche le righe esaurite): disabled per riga da isSelectable, colonna
             nascosta quando non resta nulla da selezionare (solo consuntivo). -->
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

      <!-- Nota esplicita sul parziale: una quantita' inferiore al residuo NON
           perde il resto — genera un DDT per quello che spedisci e lascia la
           riga in coda col residuo aggiornato. Senza dirlo, l'operatore non
           puo' sapere se sta rinunciando alla differenza. -->
      <p v-if="righeSelezionabili.length" class="app-riconsegna-nota">
        {{ t('vendite.resi.riconsegna_nota_parziale') }}
      </p>
    </div>
  </AppDialog>
</template>

<style scoped>
.app-riconsegna-nota {
  margin: 0;
  font-size: 0.8rem;
  color: var(--app-text-muted);
  font-style: italic;
}
</style>

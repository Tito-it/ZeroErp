<script setup>
// Scopo: Drawer crea/modifica preventivo vendita.
// CREATE: form testata semplice per creazione rapida.
// EDIT: testata + righe + totali + integrazione (con azioni stato).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreventiviStore } from '../stores/preventivi'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { statoPreventiveSeverity } from '../../../core/utils/severity'
import { displayDate, toDateString } from '../../../core/utils/date'
import { DRAWER_WIDTH, STATO_PREVENTIVO } from '../../../core/constants'
import DrawerTitle from '../../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../../core/components/DrawerFooter.vue'
import PreventiviForm from './PreventiviForm.vue'
import PreventiviRigheTable from './PreventiviRigheTable.vue'
import PreventiviIntegrazione from './PreventiviIntegrazione.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Divider from 'primevue/divider'

const { t } = useI18n()
const store = usePreventiviStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  preventivoId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)
const righeRef = ref(null)
const integrazioneRef = ref(null)

// Stato corrente del preventivo (codice_interno)
const statoCodice = computed(() => detail.value?.stato_codice_interno || '')

// Il preventivo e' modificabile solo in BOZZA (DRAFT)
const isModificabile = computed(() => statoCodice.value === STATO_PREVENTIVO.BOZZA)

// Il preventivo e' in stato ACCETTATO — abilita integrazione
const isAccettato = computed(() => statoCodice.value === STATO_PREVENTIVO.ACCETTATO)

function defaultForm() {
  return {
    utility_id: null,
    billing_account_id: null,
    istanza_utility_id: null,
    valuta_id: null,
    termine_pagamento_id: null,
    validita_dal: null,
    validita_al: null,
    competenza_mese: null,
    fatturazione_immediata: false,
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
}

async function loadDetail() {
  if (!props.preventivoId) return
  const data = await store.fetchDetail(props.preventivoId)
  if (!data) return
  detail.value = data
  form.value = {
    utility_id: data.utility_id,
    billing_account_id: data.billing_account_id,
    istanza_utility_id: data.istanza_utility_id,
    valuta_id: data.valuta_id,
    termine_pagamento_id: data.termine_pagamento_id,
    validita_dal: data.validita_dal ? new Date(data.validita_dal + 'T00:00:00') : null,
    validita_al: data.validita_al ? new Date(data.validita_al + 'T00:00:00') : null,
    competenza_mese: data.competenza_mese ? new Date(data.competenza_mese + 'T00:00:00') : null,
    fatturazione_immediata: data.fatturazione_immediata || false,
  }
}

watch(() => props.visible, (v) => {
  if (!v) return
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
  }
})

const canSave = computed(() => form.value.utility_id != null)

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {}
    if (f.billing_account_id != null) payload.billing_account_id = f.billing_account_id
    if (f.validita_dal != null) payload.validita_dal = toDateString(f.validita_dal)
    if (f.validita_al != null) payload.validita_al = toDateString(f.validita_al)
    if (f.competenza_mese != null) payload.competenza_mese = toDateString(f.competenza_mese)
    payload.fatturazione_immediata = f.fatturazione_immediata
    const result = await execute(
      () => store.update(props.preventivoId, payload),
      { successMessage: t('preventivi.preventivo_salvato') }
    )
    if (result) {
      await loadDetail()
      emit('saved', result)
    }
  } else {
    const payload = {
      utility_id: f.utility_id,
      billing_account_id: f.billing_account_id || null,
      istanza_utility_id: f.istanza_utility_id || null,
      valuta_id: f.valuta_id || null,
      termine_pagamento_id: f.termine_pagamento_id || null,
      validita_dal: f.validita_dal ? toDateString(f.validita_dal) : null,
      validita_al: f.validita_al ? toDateString(f.validita_al) : null,
      competenza_mese: f.competenza_mese ? toDateString(f.competenza_mese) : null,
      fatturazione_immediata: f.fatturazione_immediata,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('preventivi.preventivo_creato') }
    )
    if (result) emit('saved', result)
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}

// --- Azioni stato ---

function transizioni() {
  const stato = statoCodice.value
  const list = []
  if (stato === STATO_PREVENTIVO.BOZZA) {
    list.push({ codice: 'EMESSO', label: t('preventivi.azione_emetti'), severity: 'info', icon: 'pi pi-send' })
    list.push({ codice: 'ANNULLATO', label: t('preventivi.azione_annulla'), severity: 'danger', icon: 'pi pi-times' })
  } else if (stato === STATO_PREVENTIVO.EMESSO) {
    list.push({ codice: 'ACCETTATO', label: t('preventivi.azione_accetta'), severity: 'success', icon: 'pi pi-check' })
    list.push({ codice: 'RIFIUTATO', label: t('preventivi.azione_rifiuta'), severity: 'danger', icon: 'pi pi-ban' })
    list.push({ codice: 'ANNULLATO', label: t('preventivi.azione_annulla'), severity: 'danger', icon: 'pi pi-times' })
  } else if (stato === STATO_PREVENTIVO.ACCETTATO) {
    list.push({ codice: 'ANNULLATO', label: t('preventivi.azione_annulla'), severity: 'danger', icon: 'pi pi-times' })
  }
  return list
}

function onCambiaStato(nuovoStato) {
  const isIrreversibile = ['RIFIUTATO', 'ANNULLATO', 'SCADUTO'].includes(nuovoStato)
  if (isIrreversibile) {
    confirmAction({
      message: t('preventivi.conferma_cambio_stato', { stato: nuovoStato }),
      accept: () => eseguiCambioStato(nuovoStato)
    })
  } else {
    eseguiCambioStato(nuovoStato)
  }
}

async function eseguiCambioStato(nuovoStato) {
  const result = await execute(
    () => store.cambiaStato(props.preventivoId, nuovoStato),
    { successMessage: t('preventivi.stato_cambiato') }
  )
  if (result !== null) {
    await loadDetail()
    emit('saved', result)
  }
}

// Scopo: Crea nuova revisione del preventivo.
function onNuovaRevisione() {
  confirmAction({
    message: t('preventivi.conferma_revisione'),
    accept: async () => {
      const result = await execute(
        () => store.nuovaRevisione(props.preventivoId),
        { successMessage: t('preventivi.revisione_creata') }
      )
      if (result !== null) emit('saved', result)
    }
  })
}

function formatCurrency(value) {
  if (value == null) return '-'
  return Number(value).toLocaleString('it-IT', { style: 'currency', currency: 'EUR' })
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE }" :dismissable="true">
    <template #header>
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('preventivi.preventivo')" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- Header info (solo edit) -->
      <div v-if="isEdit && detail" style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.5rem;">
        <Tag :value="`${detail.numero} rev.${detail.rev}`" severity="secondary" />
        <Tag :value="detail.stato_descrizione" :severity="statoPreventiveSeverity(detail.stato_codice_interno)" />
        <span v-if="detail.data" style="font-size: 0.85rem; color: var(--text-color-secondary);">
          {{ displayDate(detail.data) }}
        </span>
        <span v-if="detail.cliente_denominazione" style="font-size: 0.85rem;">
          {{ detail.cliente_denominazione }}
        </span>
      </div>

      <!-- Azioni stato (solo edit, non readonly) -->
      <div v-if="isEdit && detail && !isReadonly" style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.5rem;">
        <Button v-for="tr in transizioni()" :key="tr.codice"
          :icon="tr.icon" :label="tr.label" :severity="tr.severity"
          size="small" @click="onCambiaStato(tr.codice)" />
        <Button v-if="statoCodice === STATO_PREVENTIVO.EMESSO || statoCodice === STATO_PREVENTIVO.ACCETTATO"
          icon="pi pi-copy" :label="t('preventivi.azione_revisione')" severity="secondary"
          size="small" @click="onNuovaRevisione" />
      </div>

      <Divider v-if="isEdit && detail" />

      <!-- Form testata -->
      <PreventiviForm :form="form" :is-edit="isEdit" :is-modificabile="isModificabile && !isReadonly" />

      <!-- Righe (solo edit) -->
      <template v-if="isEdit && detail">
        <Divider />
        <PreventiviRigheTable ref="righeRef"
          :preventivo-id="preventivoId"
          :is-modificabile="isModificabile && !isReadonly" />

        <!-- Totali -->
        <div style="display: flex; justify-content: flex-end; gap: 1.5rem; padding: 0.75rem 0; font-size: 0.9rem;">
          <div><strong>{{ t('preventivi.totale_imponibile') }}:</strong> {{ formatCurrency(detail.totale_imponibile) }}</div>
          <div><strong>{{ t('preventivi.totale_iva') }}:</strong> {{ formatCurrency(detail.totale_iva) }}</div>
          <div><strong>{{ t('preventivi.totale_documento') }}:</strong> {{ formatCurrency(detail.totale_documento) }}</div>
        </div>
      </template>

      <!-- Integrazione (solo stato ACCETTATO) -->
      <template v-if="isEdit && detail && isAccettato">
        <Divider />
        <PreventiviIntegrazione ref="integrazioneRef" :preventivo-id="preventivoId" />
      </template>

      <DrawerFooter v-if="isModificabile" :loading="loading" :disabled="!canSave"
        @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>

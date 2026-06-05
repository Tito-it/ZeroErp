<script setup>
// Scopo: Form singola riga ordine — articolo (autocomplete), UoM, quantita',
// prezzo, sconto, IVA. Pricing stile preventivo gestito lato BE: se il prezzo
// resta vuoto e l'articolo NON e' composito, gestisci_riga lo risolve via
// PricingService. Per articolo composito il prezzo padre e' SUM(componenti)
// (trigger DB): il campo prezzo e' nascosto. In CREATE, su articolo composito,
// si apre la ComponentiDialog pre-save per editare i prezzi componente (come
// preventivi/contratti): gli override viaggiano in `componenti_overrides`. In
// EDIT i prezzi componente si modificano via OrdiniRigaComponentiPanel.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotify } from '../../../core/composables/useNotify'
import { extractApiError } from '../../../core/utils/apiError'
import { useOrdiniStore } from '../stores/ordini'
import { previewRigaComponenti } from '../api/ordiniApi'
import { useRigaArticoloComposito } from '../../_shared/righe/useRigaArticoloComposito'
import ArticoloLookup from '../../../core/components/ArticoloLookup.vue'
import IvaSelect from '../../../core/components/IvaSelect.vue'
import OrdiniRigaComponentiPanel from './OrdiniRigaComponentiPanel.vue'
import ComponentiCreateActionsPanel from '../../_shared/componenti/ComponentiCreateActionsPanel.vue'
import ComponentiDialog from '../../_shared/componenti/ComponentiDialog.vue'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const { t } = useI18n()
const store = useOrdiniStore()
const notify = useNotify()
const loading = ref(false)

const props = defineProps({
  ordineId: { type: Number, required: true },
  riga: { type: Object, default: null },
})
const emit = defineEmits(['saved', 'cancel', 'componenti-changed'])

const form = ref({
  articolo_id: null,
  descrizione: '',
  qta_operativa: 1,
  prezzo_unitario: null,
  sconto_perc: 0,
  iva_id: null,
  uom_operativa_id: null,
})

// Articolo selezionato (per restore autocomplete).
const articoloObj = ref(null)

// Cuore riga articolo/composito condiviso con PreventiviRigaForm (B11, regola
// del 2): flag composito + wiring UoM + ComponentiDialog + submitRiga. Resolver
// listino e gate L2 (preventivi) restano fuori: l'ordine non li ha.
const {
  isEdit, isCasoA, isPadreComposito,
  uomOptions, uomLoading, uomLabel, caricaUomConPickBase, resetUomOptions,
  componentiDialogVisible, componentiPayload, showComponentiDialog,
  apriComponentiDialog, onComponentiConfirm,
  submitRiga,
} = useRigaArticoloComposito({
  store,
  parentId: () => props.ordineId,
  riga: () => props.riga,
  articoloObj,
  form,
})

watch(() => props.riga, (riga) => {
  if (riga) {
    form.value = {
      articolo_id: riga.articolo_id,
      descrizione: riga.descrizione || '',
      qta_operativa: Number(riga.qta_operativa) || 1,
      prezzo_unitario: riga.prezzo_unitario != null ? Number(riga.prezzo_unitario) : null,
      sconto_perc: Number(riga.sconto_perc) || 0,
      iva_id: riga.iva_id || null,
      uom_operativa_id: riga.uom_operativa_id || null,
    }
    articoloObj.value = riga.articolo_id
      ? { id: riga.articolo_id, codice: riga.articolo_codice, descrizione: riga.articolo_descrizione }
      : null
  } else {
    form.value = {
      articolo_id: null, descrizione: '', qta_operativa: 1, prezzo_unitario: null,
      sconto_perc: 0, iva_id: null, uom_operativa_id: null,
    }
    articoloObj.value = null
    resetUomOptions()
  }
}, { immediate: true })

function onArticoloSelect(item) {
  form.value.articolo_id = item.id
  form.value.descrizione = item.descrizione || ''
  // Auto-fill IVA dall'articolo (sovrascrivibile prima del save).
  if (item.iva_id != null) {
    form.value.iva_id = item.iva_id
  }
  form.value.uom_operativa_id = null
  form.value.prezzo_unitario = null
  articoloObj.value = item
  // Create: autopick base; in edit l'articolo e' disabled e questo non scatta.
  caricaUomConPickBase(item.id)
}

// Validazione FE. Il BE richiede: articolo, UoM operativa, qta_operativa <> 0,
// IVA. Il prezzo NON e' richiesto: se vuoto e articolo non composito, il BE lo
// risolve via PricingService; per articolo composito e' SUM(componenti).
const canSave = computed(() => {
  const f = form.value
  if (!f.articolo_id) return false
  if (!f.uom_operativa_id) return false
  if (f.qta_operativa == null || Number(f.qta_operativa) === 0) return false
  if (!f.iva_id) return false
  // CREATE su articolo composito: blocca il save finche' la ComponentiDialog
  // non e' stata confermata almeno una volta (componentiPayload valorizzato).
  if (showComponentiDialog.value && componentiPayload.value == null) return false
  return true
})

function buildRigaPayload() {
  const f = form.value
  if (isEdit.value) {
    const base = {
      qta_operativa: f.qta_operativa,
      sconto_perc: f.sconto_perc,
      descrizione: f.descrizione || null,
    }
    // Per riga CASO A il prezzo padre e' SUM(componenti) via trigger DB:
    // l'edit del prezzo avviene per componente nel pannello sotto.
    if (!isCasoA.value) {
      base.prezzo_unitario = f.prezzo_unitario
    }
    return base
  }
  const payload = {
    articolo_id: f.articolo_id,
    descrizione: f.descrizione || null,
    qta_operativa: f.qta_operativa,
    sconto_perc: f.sconto_perc,
    iva_id: f.iva_id,
    uom_operativa_id: f.uom_operativa_id,
  }
  // Articolo composito CREATE: il prezzo padre e' SUM(componenti) — non inviarlo
  // (il BE inizializza i componenti). Per articoli semplici: solo se valorizzato
  // (vuoto → il BE risolve via PricingService).
  if (!isPadreComposito.value && f.prezzo_unitario != null) {
    payload.prezzo_unitario = f.prezzo_unitario
  }
  // Override prezzi componente dal dialog pre-save (se confermato).
  if (showComponentiDialog.value && componentiPayload.value?.overrides) {
    payload.componenti_overrides = componentiPayload.value.overrides
  }
  return payload
}

async function handleSave() {
  const successMessage = isEdit.value
    ? t('vendite.ordini.riga_salvata')
    : t('vendite.ordini.riga_aggiunta')
  loading.value = true
  try {
    const result = await submitRiga(buildRigaPayload())
    notify.success(successMessage)
    emit('saved', result)
  } catch (err) {
    notify.error(extractApiError(err, t('vendite.ordini.errore_generico')))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="form-grid">
    <div class="form-field">
      <label>{{ t('vendite.ordini.riga_articolo') }} <span v-if="!isEdit">*</span></label>
      <ArticoloLookup :model-value="articoloObj" :disabled="isEdit"
        :filtri="{ soloComponenti: 'escludi' }"
        :placeholder="t('vendite.ordini.riga_cerca_articolo')" @select="onArticoloSelect" />
    </div>

    <div class="form-field">
      <label>{{ t('vendite.ordini.riga_descrizione') }}</label>
      <InputText v-model="form.descrizione" />
    </div>

    <div class="form-grid-3col">
      <div class="form-field">
        <label>{{ t('vendite.ordini.riga_quantita') }} *</label>
        <InputNumber v-model="form.qta_operativa" :min-fraction-digits="2" :max-fraction-digits="6" />
      </div>
      <div class="form-field">
        <label style="display: flex; align-items: center; gap: 0.5rem;">
          {{ t('vendite.ordini.riga_prezzo') }}
          <Tag v-if="isPadreComposito"
            severity="secondary"
            :value="t('vendite.ordini.componenti_padre_calcolato')"
            v-tooltip.top="t('vendite.ordini.componenti_section_hint')" />
        </label>
        <InputNumber v-model="form.prezzo_unitario" mode="currency" currency="EUR" locale="it-IT"
          :min-fraction-digits="6" :max-fraction-digits="6"
          :disabled="isPadreComposito" />
        <small v-if="!isPadreComposito" class="text-color-secondary">
          {{ t('vendite.ordini.riga_prezzo_auto_hint') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.ordini.riga_sconto') }}</label>
        <InputNumber v-model="form.sconto_perc" suffix="%" :min="0" :max="100"
          :min-fraction-digits="2" :max-fraction-digits="2" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.ordini.riga_iva') }} *</label>
        <IvaSelect v-model="form.iva_id"
          :placeholder="t('vendite.ordini.riga_iva')" :disabled="isEdit" />
      </div>
      <div class="form-field" v-if="!isEdit">
        <label>{{ t('vendite.ordini.riga_uom') }} *</label>
        <Select v-model="form.uom_operativa_id"
          :options="uomOptions" :option-label="uomLabel" option-value="uom_id"
          :loading="uomLoading"
          :disabled="!form.articolo_id || uomLoading"
          :placeholder="form.articolo_id
            ? t('vendite.ordini.riga_uom')
            : t('vendite.ordini.riga_uom_articolo_first')" />
      </div>
    </div>

    <!-- Componenti BoM CREATE (articolo composito): dialog pre-save per editare
         i prezzi componente. BB condiviso con preventivi/contratti. Gli override
         confermati viaggiano in `componenti_overrides` nel payload. -->
    <ComponentiCreateActionsPanel
      v-if="!isEdit && articoloObj?.is_composito"
      section-title-key="vendite.ordini.componenti_section_title"
      :disabled="!form.articolo_id || !form.uom_operativa_id
        || ((form.qta_operativa || 0) <= 0)"
      :componenti-payload="componentiPayload"
      @apri-dialog="apriComponentiDialog"
    />

    <ComponentiDialog
      v-if="showComponentiDialog"
      v-model:visible="componentiDialogVisible"
      :articolo="articoloObj"
      :documento-id="ordineId"
      :uom-operativa-id="form.uom_operativa_id"
      :quantita="form.qta_operativa"
      :api-preview="previewRigaComponenti"
      :initial-payload="componentiPayload"
      @confirm="onComponentiConfirm"
    />

    <!-- Componenti BoM CASO A (solo EDIT): pannello componenti persistiti,
         modifica prezzo per singolo componente via PATCH. In CREATE i componenti
         sono inizializzati dal BE al save della riga composita. -->
    <div v-if="isCasoA" class="app-drawer-section" style="margin-top: 1rem;">
      <h4 style="margin: 0 0 0.5rem 0; font-size: 1rem;">
        {{ t('vendite.ordini.componenti_section_title') }}
      </h4>
      <OrdiniRigaComponentiPanel
        :ordine-id="ordineId"
        :riga-id="props.riga.id"
        :readonly="false"
        @changed="emit('componenti-changed')" />
    </div>

    <!-- Bottoni Salva/Annulla della riga: sempre visibili in edit-riga. I bottoni
         del FormFooter testata si nascondono via `formRigaAperto` lato OrdiniDrawer. -->
    <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem;">
      <Button :label="t('common.cancel')" severity="secondary" @click="emit('cancel')" />
      <Button :label="t('common.save')" :loading="loading" :disabled="!canSave" @click="handleSave" />
    </div>
  </div>
</template>

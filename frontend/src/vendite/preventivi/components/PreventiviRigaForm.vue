<script setup>
// Scopo: Form singola riga preventivo — articolo (autocomplete), UoM, quantita', prezzo, sconto, IVA.
// Il prezzo viene proposto dal listino ma e' sempre sovrascrivibile dall'operatore.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { usePreventiviStore } from '../stores/preventivi'
import ArticoloLookup from '../../../core/components/ArticoloLookup.vue'
import LookupSelect from '../../../core/components/LookupSelect.vue'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'

const { t } = useI18n()
const store = usePreventiviStore()
const { execute, loading } = useApiHandler()

const props = defineProps({
  preventivoId: { type: Number, required: true },
  riga: { type: Object, default: null }
})
const emit = defineEmits(['saved', 'cancel'])

const isEdit = computed(() => props.riga != null)

const form = ref({
  articolo_id: null,
  descrizione: '',
  quantita: 1,
  prezzo_unitario: null,
  sconto_percentuale: 0,
  iva_id: null,
  uom_operativa_id: null,
  ordine: null,
})

// Articolo selezionato (per restore autocomplete)
const articoloObj = ref(null)

watch(() => props.riga, (riga) => {
  if (riga) {
    form.value = {
      articolo_id: riga.articolo_id,
      descrizione: riga.descrizione || '',
      quantita: Number(riga.quantita) || 1,
      prezzo_unitario: Number(riga.prezzo_unitario) || null,
      sconto_percentuale: Number(riga.sconto_percentuale) || 0,
      iva_id: riga.iva_id || null,
      uom_operativa_id: riga.uom_operativa_id || null,
      ordine: riga.ordine || null,
    }
    articoloObj.value = riga.articolo_id ? { id: riga.articolo_id, codice: riga.articolo_codice, descrizione: riga.articolo_descrizione } : null
  } else {
    form.value = { articolo_id: null, descrizione: '', quantita: 1, prezzo_unitario: null, sconto_percentuale: 0, iva_id: null, uom_operativa_id: null, ordine: null }
    articoloObj.value = null
  }
}, { immediate: true })

function onArticoloSelect(item) {
  form.value.articolo_id = item.id
  form.value.descrizione = item.descrizione || ''
  articoloObj.value = item
}

const canSave = computed(() => form.value.articolo_id && form.value.quantita > 0)

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {
      quantita: f.quantita,
      prezzo_unitario: f.prezzo_unitario,
      sconto_percentuale: f.sconto_percentuale,
    }
    const result = await execute(
      () => store.aggiornaRiga(props.preventivoId, props.riga.id, payload),
      { successMessage: t('preventivi.riga_salvata') }
    )
    if (result !== null) emit('saved', result)
  } else {
    const payload = {
      articolo_id: f.articolo_id,
      descrizione: f.descrizione || null,
      quantita: f.quantita,
      prezzo_unitario: f.prezzo_unitario,
      sconto_percentuale: f.sconto_percentuale,
      iva_id: f.iva_id,
      uom_operativa_id: f.uom_operativa_id,
      ordine: f.ordine,
    }
    const result = await execute(
      () => store.addRiga(props.preventivoId, payload),
      { successMessage: t('preventivi.riga_aggiunta') }
    )
    if (result !== null) emit('saved', result)
  }
}
</script>

<template>
  <div class="form-grid">
    <div class="form-field">
      <label>{{ t('preventivi.riga_articolo') }}</label>
      <ArticoloLookup :model-value="articoloObj" :disabled="isEdit"
        :placeholder="t('preventivi.riga_cerca_articolo')" @select="onArticoloSelect" />
    </div>

    <div class="form-field">
      <label>{{ t('preventivi.riga_descrizione') }}</label>
      <InputText v-model="form.descrizione" />
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.riga_quantita') }}</label>
        <InputNumber v-model="form.quantita" :min-fraction-digits="2" :max-fraction-digits="6" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.riga_prezzo') }}</label>
        <InputNumber v-model="form.prezzo_unitario" mode="currency" currency="EUR" locale="it-IT" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('preventivi.riga_sconto') }}</label>
        <InputNumber v-model="form.sconto_percentuale" suffix="%" :min="0" :max="100"
          :min-fraction-digits="2" :max-fraction-digits="2" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.riga_iva') }}</label>
        <LookupSelect v-model="form.iva_id" rel="config.iva"
          :placeholder="t('preventivi.riga_iva')" :disabled="isEdit" />
      </div>
    </div>

    <div class="form-grid-2col" v-if="!isEdit">
      <div class="form-field">
        <label>{{ t('preventivi.riga_uom') }}</label>
        <LookupSelect v-model="form.uom_operativa_id" rel="catalogo.unita_misura"
          :placeholder="t('preventivi.riga_uom')" />
      </div>
      <div class="form-field">
        <label>{{ t('preventivi.riga_ordine') }}</label>
        <InputNumber v-model="form.ordine" :use-grouping="false" />
      </div>
    </div>

    <div style="display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem;">
      <Button :label="t('common.cancel')" severity="secondary" @click="emit('cancel')" />
      <Button :label="t('common.save')" :loading="loading" :disabled="!canSave" @click="handleSave" />
    </div>
  </div>
</template>

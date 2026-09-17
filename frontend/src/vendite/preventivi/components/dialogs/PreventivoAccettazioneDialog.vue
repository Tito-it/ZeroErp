<script setup>
// Scopo: Dialog di accettazione preventivo — raccoglie i dati di processo
//        richiesti dall'accettazione (EMESSO → ACCETTATO): modalita' di
//        fatturazione (toggle immediata) + mese di competenza. Componente
//        CONDIVISO: usato sia dal programma standalone (PreventiviDrawer) sia
//        dal percorso pratica (FlussoDrawer, completamento APPROVAZIONE_CLIENTE),
//        così le scelte operatore sono identiche ovunque (uniformita').
//        Emette `confirm` con il payload gia' BE-ready
//        ({fatturazione_immediata, competenza_mese: 'YYYY-MM-DD'|null});
//        il parent decide come applicarlo (cambio stato preventivo o
//        completamento flusso con `meta`).
// Regola di priorita' (mirror BE preventivi_service.cambia_stato):
//        immediata=true ⇒ competenza forzata al primo del mese corrente.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppDialog from '../../../../core/components/AppDialog.vue'
import ToggleSwitch from 'primevue/toggleswitch'
import DatePicker from 'primevue/datepicker'
import { toDateString } from '../../../../core/utils/date'
import { DATE_FORMAT } from '../../../../core/constants'

const props = defineProps({
  // Campi che il BACKEND indica come da correggere (envelope `error.fields`).
  // Arrivano dal padre: questo componente non chiama le API da solo.
  campiErrati: { type: Array, default: () => [] },
  visible: Boolean,
  readonly: Boolean,
})
const emit = defineEmits(['update:visible', 'confirm'])
const { t } = useI18n()

// Helper: primo giorno del mese corrente (snapshot tx-time, allineato BE).
function _firstOfCurrentMonth() {
  const now = new Date()
  return new Date(now.getFullYear(), now.getMonth(), 1)
}

const form = ref({
  fatturazione_immediata: false,
  competenza_mese: _firstOfCurrentMonth(),
})

// immediata=true ⇒ datepicker disabilitato (il BE forza il mese corrente).
const competenzaDisabled = computed(() => form.value.fatturazione_immediata === true)

// Sync UX↔BE: attivando "immediata" il mese torna al corrente (= valore forzato BE).
watch(() => form.value.fatturazione_immediata, (immediata) => {
  if (immediata) form.value.competenza_mese = _firstOfCurrentMonth()
})

// Reset del form a ogni apertura (niente stato residuo fra accettazioni).
watch(() => props.visible, (v) => {
  if (v) {
    form.value = {
      fatturazione_immediata: false,
      competenza_mese: _firstOfCurrentMonth(),
    }
  }
})

function onSave() {
  const f = form.value
  emit('confirm', {
    fatturazione_immediata: f.fatturazione_immediata,
    competenza_mese: f.competenza_mese ? toDateString(f.competenza_mese) : null,
  })
  emit('update:visible', false)
}
</script>

<template>
  <AppDialog
    :visible="props.visible"
    :closable="false"
    :header="t('vendite.preventivi.accetta_titolo')"
    width="sm"
    :readonly="props.readonly"
    :save-label="t('vendite.preventivi.accetta_conferma')"
    :save-disabled="!form.fatturazione_immediata && !form.competenza_mese"
    @update:visible="(val) => emit('update:visible', val)"
    @save="onSave"
  >
    <p style="margin: 0 0 1rem 0; color: var(--app-text-muted);">
      {{ t('vendite.preventivi.accetta_descrizione') }}
    </p>
    <div class="form-grid">
      <div class="form-field" style="display: flex; align-items: center; gap: 0.75rem;">
        <ToggleSwitch v-model="form.fatturazione_immediata"
        :invalid="campiErrati.includes('fatturazione_immediata')" inputId="accept-immediata" />
        <label for="accept-immediata">{{ t('vendite.preventivi.accetta_fatturazione_immediata') }}</label>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.preventivi.accetta_competenza') }}</label>
        <DatePicker v-model="form.competenza_mese" :date-format="DATE_FORMAT"
          show-icon view="month" :disabled="competenzaDisabled" />
        <small v-if="competenzaDisabled" style="color: var(--app-text-muted);">
          {{ t('vendite.preventivi.accetta_competenza_hint_immediata') }}
        </small>
        <small v-else-if="!form.competenza_mese" class="app-field-error">
          {{ t('vendite.preventivi.accetta_competenza_required') }}
        </small>
      </div>
    </div>
  </AppDialog>
</template>

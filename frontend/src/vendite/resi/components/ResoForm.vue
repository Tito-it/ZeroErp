<script setup>
// Scopo: Form testata reso — quasi tutta DISPLAY-ONLY: il reso eredita
// cliente/destinatario/utility/valuta/emittente dal DDT sorgente (trigger DB
// normalize) e i campi sono immutabili (non_editable_fields BE). Si scelgono
// in bozza la data documento e il MAGAZZINO DI RIENTRO (3-bis D-3b-a: lo
// propone il DB dalla bolla d'origine; obbligatorio alla conferma di un reso
// che fa rientrare merce, motivo `magazzino_mancante` della capability).
// Spegnimento per campo, come gli altri documenti: la capability dice quali.
// Usato dentro ResoDrawer.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { DATE_FORMAT } from '../../../core/constants'
import EmittenteFiscaleField from '../../../core/components/EmittenteFiscaleField.vue'
import MagazzinoDocumentoSelect from '../../../magazzino/components/MagazzinoDocumentoSelect.vue'
import DatePicker from 'primevue/datepicker'
import InputText from 'primevue/inputtext'

const { t } = useI18n()

const form = defineModel('form', { type: Object, required: true })

const props = defineProps({
  // Campi che il BACKEND indica come da correggere (envelope `error.fields`).
  // Arrivano dal padre: questo componente non chiama le API da solo.
  campiErrati: { type: Array, default: () => [] },
  isModificabile: { type: Boolean, default: true },
  nonEditableFields: { type: Array, default: () => [] },
  // Detail testata (vw_resi_lista) per i display denormalizzati.
  record: { type: Object, default: null },
})

const lockedFields = computed(() => new Set(props.nonEditableFields))
function isLocked(field) {
  return !props.isModificabile || lockedFields.value.has(field)
}

</script>

<template>
  <div class="form-grid">
    <div class="form-grid-2col">
      <!-- Emittente ereditato dal DDT sorgente: sempre display denormalizzato. -->
      <div class="form-field">
        <label>{{ t('vendite.resi.field_emittente_fiscale') }}</label>
        <EmittenteFiscaleField
          v-model="form.emittente_fiscale_id"
          :record="record"
          :is-edit="true"
          disabled />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.resi.field_data') }}</label>
        <DatePicker v-model="form.data"
        :invalid="campiErrati.includes('data')" :date-format="DATE_FORMAT"
          show-icon show-button-bar :disabled="isLocked('data')" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>
          {{ t('vendite.resi.field_magazzino') }}
          <span
            v-if="!isLocked('magazzino_id')"
            v-tooltip.bottom="t('vendite.resi.field_magazzino_richiesto_conferma')"
          >*</span>
        </label>
        <MagazzinoDocumentoSelect
          v-model="form.magazzino_id"
          :emittente-id="form.emittente_fiscale_id"
          :record="record"
          :invalid="campiErrati.includes('magazzino_id')"
          :disabled="isLocked('magazzino_id')"
          :placeholder="t('vendite.resi.field_magazzino')" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.resi.field_billing_account') }}</label>
        <InputText :model-value="record?.ba_codice || '—'" disabled />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.resi.field_destinatario') }}</label>
        <InputText :model-value="record?.destinatario_denominazione || '—'" disabled />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('vendite.resi.field_ddt_origine') }}</label>
        <InputText :model-value="record?.ddt_origine_numero || '—'" disabled />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.resi.field_valuta') }}</label>
        <InputText :model-value="record?.valuta_codice || '—'" disabled />
      </div>
    </div>
  </div>
</template>

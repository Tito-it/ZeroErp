<script setup>
// Scopo: Drawer crea/modifica riga matrice config.tipi_ruolo_tipi_indirizzo.
// FK immutabili in edit: tipo_ruolo_id, tipo_indirizzo_id.
// Campi modificabili in edit: attivo, obbligatorio, fallback_tipo_indirizzo_id.
// Sola lettura: prop `readonly` cumulativa con useInjectReadonly.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTipiRuoloTipiIndirizzoStore } from '../stores/tipiRuoloTipiIndirizzo'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { displayDate } from '../../core/utils/date'
import Select from 'primevue/select'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'
import InputText from 'primevue/inputtext'



const { t } = useI18n()
const store = useTipiRuoloTipiIndirizzoStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  recordId: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const isReadOnlyEffective = computed(() => props.readonly || isReadonly.value)

// Fase 4 — Campi non editabili e fallback options letti dal BE detail.
// `nonEditableFields`: lista delle dimensioni immutabili (in edit: ['tipo_ruolo_id', 'tipo_indirizzo_id']).
// `fallbackOptions`: lista candidati pre-filtrati (no self-ref + no cicli);
// in create resta vuota e si usa il LookupSelect generico (l'admin deve
// poter scegliere un qualsiasi tipo_indirizzo perche' la riga non esiste
// ancora e il guard ciclo non e' computabile fino a save).
const nonEditableFields = ref([])
const fallbackOptions = ref([])
const detail = ref(null)

function isFieldImmutable(field) {
  return nonEditableFields.value.includes(field)
}

const form = ref({
  tipo_ruolo_id: null,
  tipo_indirizzo_id: null,
  obbligatorio: false,
  fallback_tipo_indirizzo_id: null,
  attivo: true
})
// Modifiche non salvate: fotografia all'apertura (anche in creazione), e
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

function resetForm() {
  form.value = {
    tipo_ruolo_id: null,
    tipo_indirizzo_id: null,
    obbligatorio: false,
    fallback_tipo_indirizzo_id: null,
    attivo: true
  }
  nonEditableFields.value = []
  fallbackOptions.value = []
  detail.value = null
  fissa()
}

async function loadDetail() {
  if (!props.recordId) return
  const data = await store.fetchDetail(props.recordId)
  // Race cancellation: chiudi+riapri in create prima del completion ->
  // mutazione post-await sovrascrive form vuoto. Pattern Fase 3.
  if (!props.visible || !isEdit.value) return
  if (!data) return
  detail.value = data
  form.value = {
    tipo_ruolo_id: data.tipo_ruolo_id,
    tipo_indirizzo_id: data.tipo_indirizzo_id,
    obbligatorio: data.obbligatorio ?? false,
    fallback_tipo_indirizzo_id: data.fallback_tipo_indirizzo_id,
    attivo: data.attivo ?? true
  }
  nonEditableFields.value = Array.isArray(data.non_editable_fields)
    ? data.non_editable_fields
    : []
  fallbackOptions.value = Array.isArray(data.fallback_options)
    ? data.fallback_options
    : []
  fissa()
}

watch(() => props.visible, (v) => {
  if (!v) return
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
  }
})

const canSave = computed(() => {
  if (isReadOnlyEffective.value) return false
  // Fase 4 — Guard UX: blocca self-ref fallback prima del submit (in create
  // la lista candidati non e' filtrata BE-side perche' la riga non esiste
  // ancora). In edit il filtraggio e' gestito da `fallbackOptions` data-driven.
  // Il BE comunque rifiuta col CHECK constraint, ma evitiamo un round-trip
  // di errore.
  if (
    form.value.fallback_tipo_indirizzo_id != null &&
    form.value.fallback_tipo_indirizzo_id === form.value.tipo_indirizzo_id
  ) {
    return false
  }
  if (isEdit.value) return true
  return form.value.tipo_ruolo_id && form.value.tipo_indirizzo_id
})

async function handleSave() {
  if (isReadOnlyEffective.value) return
  if (isEdit.value) {
    const payload = {
      attivo: form.value.attivo,
      obbligatorio: form.value.obbligatorio,
      fallback_tipo_indirizzo_id: form.value.fallback_tipo_indirizzo_id || null
    }
    const result = await execute(
      () => store.update(props.recordId, payload),
      { successMessage: t('amministrazione.matrice_indirizzi_ruoli.saved') }
    )
    if (result !== null) { fissa(); emit('saved', result); close() }
  } else {
    const payload = {
      tipo_ruolo_id: form.value.tipo_ruolo_id,
      tipo_indirizzo_id: form.value.tipo_indirizzo_id,
      obbligatorio: form.value.obbligatorio,
      attivo: form.value.attivo
    }
    if (form.value.fallback_tipo_indirizzo_id) {
      payload.fallback_tipo_indirizzo_id = form.value.fallback_tipo_indirizzo_id
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('amministrazione.matrice_indirizzi_ruoli.created') }
    )
    if (result !== null) { fissa(); emit('saved', result); close() }
  }
}

// Uscita dopo il salvataggio, diretta. Quella per volonta' dell'utente passa
// dalla conferma di AppDrawer (`conferma-uscita`).
function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('amministrazione.matrice_indirizzi_ruoli.drawer_title')"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.SIMPLE"
    :readonly="isReadOnlyEffective"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('amministrazione.matrice_indirizzi_ruoli.field_tipo_ruolo') }}</label>
        <LookupSelect v-model="form.tipo_ruolo_id" rel="config.tipi_ruoli"
          :placeholder="t('amministrazione.matrice_indirizzi_ruoli.field_tipo_ruolo_placeholder')"
          :disabled="isFieldImmutable('tipo_ruolo_id') || isReadOnlyEffective" />
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.matrice_indirizzi_ruoli.field_tipo_indirizzo') }}</label>
        <LookupSelect v-model="form.tipo_indirizzo_id" rel="config.tipi_indirizzi"
          :placeholder="t('amministrazione.matrice_indirizzi_ruoli.field_tipo_indirizzo_placeholder')"
          :disabled="isFieldImmutable('tipo_indirizzo_id') || isReadOnlyEffective" />
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.matrice_indirizzi_ruoli.field_obbligatorio') }}</label>
        <ToggleSwitch v-model="form.obbligatorio" :disabled="isReadOnlyEffective"
          :invalid="campiErrati.includes('obbligatorio')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.matrice_indirizzi_ruoli.field_fallback') }}</label>
        <!-- Fase 4: in edit usa fallback_options pre-filtrate dal BE
             (no self-ref + no cicli). In create il record non esiste ancora,
             il guard ciclo non e' computabile: fallback al LookupSelect generico
             sui tipi_indirizzi (BE rifiuta self-ref via FK constraint). -->
        <Select v-if="isEdit" v-model="form.fallback_tipo_indirizzo_id"
          :options="fallbackOptions"
          option-label="descrizione"
          option-value="tipo_indirizzo_id"
          :placeholder="t('amministrazione.matrice_indirizzi_ruoli.field_fallback_placeholder')"
          :disabled="isReadOnlyEffective" show-clear filter
          :invalid="campiErrati.includes('fallback_tipo_indirizzo_id')"
        />
        <LookupSelect v-else v-model="form.fallback_tipo_indirizzo_id" rel="config.tipi_indirizzi"
          :placeholder="t('amministrazione.matrice_indirizzi_ruoli.field_fallback_placeholder')"
          :disabled="isReadOnlyEffective" show-clear />
      </div>
      <div v-if="isEdit" class="form-field">
        <label>{{ t('indirizzi.campo_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective"
          :invalid="campiErrati.includes('attivo')"
        />
      </div>
      <Message v-if="isEdit" severity="info" :closable="false">
        {{ t('amministrazione.matrice_indirizzi_ruoli.fk_immutable_hint') }}
      </Message>
      <template v-if="isEdit && detail">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('amministrazione.matrice_indirizzi_ruoli.col_valido_dal') }}</label>
            <InputText :model-value="displayDate(detail.valido_dal)" disabled />
          </div>
          <div class="form-field">
            <label>{{ t('amministrazione.matrice_indirizzi_ruoli.col_valido_al') }}</label>
            <InputText :model-value="displayDate(detail.valido_al)" disabled />
          </div>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('common.data_insert') }}</label>
            <InputText :model-value="displayDate(detail.data_insert)" disabled />
          </div>
          <div class="form-field">
            <label>{{ t('common.data_update') }}</label>
            <InputText :model-value="displayDate(detail.data_update)" disabled />
          </div>
        </div>
      </template>
    </div>
  </AppDrawer>
</template>

<script setup>
// Scopo: Drawer crea/modifica anagrafiche.categorie_clienti.
//        - In create: tutti i campi editabili (codice obbligatorio).
//        - In edit:   codice immutabile (lock_columns DB).
//        - Sola lettura: prop `readonly` cumulativa con useInjectReadonly.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCategorieClientiStore } from '../stores/categorieClienti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import AppDrawer from '../../core/components/AppDrawer.vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'



const { t } = useI18n()
const store = useCategorieClientiStore()
// `campiErrati`: i campi che il BACKEND indica come da correggere (envelope
// `error.fields`). ⭐ PILOTA del §12 del piano-be-classe-codici-errore: e' il
// primo drawer che li usa. Non sostituisce la validazione client (`canSave`) —
// copre le regole che il frontend NON conosce, quelle che stanno nel service.
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

const form = ref({
  codice: '',
  descrizione: '',
  ordinamento: 0,
  partecipa_promo: false,
  attivo: true
})
// Modifiche non salvate: fotografia all'apertura (anche in creazione), e
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

function resetForm() {
  form.value = {
    codice: '',
    descrizione: '',
    ordinamento: 0,
    partecipa_promo: false,
    attivo: true
  }
  fissa()
}

async function loadDetail() {
  if (!props.recordId) return
  const data = await store.fetchDetail(props.recordId)
  if (!data) return
  form.value = {
    codice: data.codice ?? '',
    descrizione: data.descrizione ?? '',
    ordinamento: data.ordinamento ?? 0,
    partecipa_promo: data.partecipa_promo ?? false,
    attivo: data.attivo ?? true
  }
  fissa()
}

watch(
  [() => props.visible, () => props.recordId],
  ([visible]) => {
    if (!visible) return
    if (isEdit.value) {
      loadDetail()
    } else {
      resetForm()
    }
  }
)

const canSave = computed(() => {
  if (isReadOnlyEffective.value) return false
  // descrizione sempre obbligatoria; codice solo in create.
  if (!form.value.descrizione || form.value.descrizione.trim() === '') return false
  if (!isEdit.value) {
    if (!form.value.codice || form.value.codice.trim() === '') return false
  }
  return true
})

async function handleSave() {
  const payload = {
    descrizione: form.value.descrizione.trim(),
    ordinamento: form.value.ordinamento ?? 0,
    partecipa_promo: form.value.partecipa_promo,
    attivo: form.value.attivo
  }
  if (!isEdit.value) {
    payload.codice = form.value.codice.trim()  // il maiuscolo lo mette il DB (CODICE_MAIUSCOLO)
  }
  const result = await execute(
    () => isEdit.value
      ? store.update(props.recordId, payload)
      : store.create(payload),
    {
      successMessage: isEdit.value
        ? t('amministrazione.categorie_clienti.saved')
        : t('amministrazione.categorie_clienti.created')
    }
  )
  if (result !== null) { fissa(); emit('saved', result) }
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('amministrazione.categorie_clienti.drawer_title')"
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
        <label>{{ t('amministrazione.categorie_clienti.field_codice') }} <span v-if="!isEdit">*</span></label>
        <InputText
          v-model="form.codice"
          class="app-codice-input"
          :disabled="isEdit || isReadOnlyEffective"
          :placeholder="t('amministrazione.categorie_clienti.field_codice_placeholder')"
          maxlength="32"
          :invalid="campiErrati.includes('codice')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.categorie_clienti.field_descrizione') }} *</label>
        <InputText
          v-model="form.descrizione"
          :disabled="isReadOnlyEffective"
          :placeholder="t('amministrazione.categorie_clienti.field_descrizione_placeholder')"
          maxlength="255"
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.categorie_clienti.field_ordinamento') }}</label>
        <InputNumber
          v-model="form.ordinamento"
          :disabled="isReadOnlyEffective"
          :min="0"
          showButtons
          :invalid="campiErrati.includes('ordinamento')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('amministrazione.categorie_clienti.field_partecipa_promo') }}</label>
        <ToggleSwitch v-model="form.partecipa_promo" :disabled="isReadOnlyEffective"
          :invalid="campiErrati.includes('partecipa_promo')" />
        <small class="app-text-muted">
          {{ t('amministrazione.categorie_clienti.field_partecipa_promo_hint') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('common.attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective"
          :invalid="campiErrati.includes('attivo')" />
      </div>

      <Message v-if="isEdit" severity="info" :closable="false">
        {{ t('amministrazione.categorie_clienti.codice_immutable_hint') }}
      </Message>
    </div>
  </AppDrawer>
</template>

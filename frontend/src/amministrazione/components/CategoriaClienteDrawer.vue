<script setup>
// Scopo: Drawer crea/modifica anagrafiche.categorie_clienti.
//        - In create: tutti i campi editabili (codice obbligatorio).
//        - In edit:   codice immutabile (lock_columns DB).
//        - Sola lettura: prop `readonly` cumulativa con useInjectReadonly.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCategorieClientiStore } from '../stores/categorieClienti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useCategorieClientiStore()
const { execute, loading } = useApiHandler()
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

function resetForm() {
  form.value = {
    codice: '',
    descrizione: '',
    ordinamento: 0,
    partecipa_promo: false,
    attivo: true
  }
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
    payload.codice = form.value.codice.trim().toUpperCase()
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
  if (result !== null) emit('saved', result)
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    position="right"
    :style="{ width: DRAWER_WIDTH.SIMPLE }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('amministrazione.categorie_clienti.drawer_title')"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadOnlyEffective }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('amministrazione.categorie_clienti.field_codice') }} <span v-if="!isEdit">*</span></label>
          <InputText
            v-model="form.codice"
            :disabled="isEdit || isReadOnlyEffective"
            :placeholder="t('amministrazione.categorie_clienti.field_codice_placeholder')"
            maxlength="32"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.categorie_clienti.field_descrizione') }} *</label>
          <InputText
            v-model="form.descrizione"
            :disabled="isReadOnlyEffective"
            :placeholder="t('amministrazione.categorie_clienti.field_descrizione_placeholder')"
            maxlength="255"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.categorie_clienti.field_ordinamento') }}</label>
          <InputNumber
            v-model="form.ordinamento"
            :disabled="isReadOnlyEffective"
            :min="0"
            showButtons
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.categorie_clienti.field_partecipa_promo') }}</label>
          <ToggleSwitch v-model="form.partecipa_promo" :disabled="isReadOnlyEffective" />
          <small class="text-color-secondary">
            {{ t('amministrazione.categorie_clienti.field_partecipa_promo_hint') }}
          </small>
        </div>
        <div class="form-field">
          <label>{{ t('common.attivo') }}</label>
          <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective" />
        </div>

        <Message v-if="isEdit" severity="info" :closable="false">
          {{ t('amministrazione.categorie_clienti.codice_immutable_hint') }}
        </Message>
      </div>

      <DrawerFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="close"
      />
    </div>
  </Drawer>
</template>

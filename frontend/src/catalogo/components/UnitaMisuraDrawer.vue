<script setup>
// Scopo: Drawer crea/modifica unita' di misura.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUnitaMisuraStore } from '../stores/unitaMisura'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import { CATALOGO_LOOKUP_RELS } from '../constants'

const { t } = useI18n()
const store = useUnitaMisuraStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  uomId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({ codice: '', descrizione: '', descrizione_fattura: '', tipo_uom_id: null, attivo: true })
// Modifiche non salvate: fotografia all'apertura (anche in creazione) e
// conferma se si chiude con modifiche (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

function resetForm() {
  form.value = { codice: '', descrizione: '', descrizione_fattura: '', tipo_uom_id: null, attivo: true }
  fissa()
}

async function loadDetail() {
  if (!props.uomId) return
  const data = await store.fetchDetail(props.uomId)
  if (!data) return
  form.value = {
    codice: data.codice || '',
    descrizione: data.descrizione || '',
    descrizione_fattura: data.descrizione_fattura || '',
    tipo_uom_id: data.tipo_uom_id ?? null,
    attivo: data.attivo ?? true
  }
  fissa()
}

watch(
  [() => props.visible, () => props.mode, () => props.uomId],
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
  if (isReadonly.value) return false
  return Boolean(
    form.value.codice?.trim() &&
    form.value.descrizione?.trim() &&
    form.value.tipo_uom_id != null
  )
})

async function handleSave() {
  if (isEdit.value) {
    const payload = {
      descrizione: form.value.descrizione?.trim(),
      descrizione_fattura: form.value.descrizione_fattura?.trim() || null,
      tipo_uom_id: form.value.tipo_uom_id,
      attivo: form.value.attivo,
    }
    const result = await execute(() => store.update(props.uomId, payload), { successMessage: t('catalogo.uom_salvata') })
    if (result !== null) { fissa(); emit('saved', result) }
  } else {
    const payload = {
      codice: form.value.codice?.trim(),
      descrizione: form.value.descrizione?.trim(),
      descrizione_fattura: form.value.descrizione_fattura?.trim() || null,
      tipo_uom_id: form.value.tipo_uom_id
    }
    const result = await execute(() => store.create(payload), { successMessage: t('catalogo.uom_creata') })
    if (result !== null) { fissa(); emit('saved', result) }
  }
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('catalogo.unita_misura')"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.SIMPLE"
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
        <label>{{ t('catalogo.field_codice') }}</label>
        <InputText v-model="form.codice" class="app-codice-input" :disabled="isEdit || isReadonly"
          :invalid="campiErrati.includes('codice')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_descrizione') }}</label>
        <InputText v-model="form.descrizione" :disabled="isReadonly"
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_desc_fattura') }}</label>
        <InputText v-model="form.descrizione_fattura" :disabled="isReadonly" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.uom_tipo') }}</label>
        <LookupSelect
          v-model="form.tipo_uom_id"
          :rel="CATALOGO_LOOKUP_RELS.UOM_TIPI"
          :placeholder="t('catalogo.uom_tipo')"
          show-code
          :disabled="isReadonly"
        />
      </div>
      <div v-if="isEdit" class="form-field">
        <label>{{ t('indirizzi.campo_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" :disabled="isReadonly"
          :invalid="campiErrati.includes('attivo')"
        />
      </div>
    </div>
  </AppDrawer>
</template>

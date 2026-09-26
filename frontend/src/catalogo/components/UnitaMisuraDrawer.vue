<script setup>
// Scopo: Drawer crea/modifica unita' di misura.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUnitaMisuraStore } from '../stores/unitaMisura'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerFormPreserve, gestoreVisibile } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
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

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
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

function close() {
  chiudiConConferma(() => {
    emit('update:visible', false)
    emit('cancelled')
  })
}
const suVisibile = gestoreVisibile(emit, close)
</script>

<template>
  <Drawer :visible="visible" @update:visible="suVisibile"
    position="right" :style="{ width: DRAWER_WIDTH.SIMPLE }" :dismissable="true"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :modificato="modificato" :action="isEdit ? t('common.edit') : t('common.new')" :title="t('catalogo.unita_misura')" />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('catalogo.field_codice') }}</label>
          <InputText v-model="form.codice" :disabled="isEdit || isReadonly"
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

      <FormFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>

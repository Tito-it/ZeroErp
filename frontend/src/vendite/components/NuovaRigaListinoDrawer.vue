<script setup>
// Scopo: Sub-drawer per aggiungere una riga prezzo a una versione listino.
// Articolo e BA affiancati, UoM dipendente dall'articolo selezionato,
// prezzo obbligatorio. Al save chiude e notifica il padre per reload lista.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { createRiga } from '../api/listini'
import { listArticoloUom } from '../../catalogo/api/catalogo'
import { DRAWER_WIDTH } from '../../core/constants'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'

const { t } = useI18n()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  listinoId: { type: [Number, null], required: true },
  versioneId: { type: [Number, null], required: true },
  listinoUtilityId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const form = ref({})
const uomOptions = ref([])
const uomLoading = ref(false)

function defaultForm() {
  return { articolo_obj: null, uom_id: null, prezzo: null, ba_obj: null }
}

watch(() => props.visible, (v) => {
  if (v) {
    form.value = defaultForm()
    uomOptions.value = []
  }
})

const canSave = computed(() =>
  !!form.value.articolo_obj?.id &&
  !!form.value.uom_id &&
  form.value.prezzo != null
)

// Scopo: Carica UoM operative dell'articolo selezionato e pre-seleziona la base.
async function onArticoloSelect(articolo) {
  form.value.uom_id = null
  uomOptions.value = []
  if (!articolo?.id) return
  uomLoading.value = true
  try {
    const res = await listArticoloUom(articolo.id)
    const list = res.data.data.results || res.data.data || []
    uomOptions.value = list
    const base = list.find(u => u.is_base)
    if (base) {
      form.value.uom_id = base.uom_id
    } else if (list.length === 1) {
      form.value.uom_id = list[0].uom_id
    }
  } catch {
    uomOptions.value = []
  } finally {
    uomLoading.value = false
  }
}

async function handleSave() {
  if (!props.listinoId || !props.versioneId) return
  const payload = {
    articolo_id: form.value.articolo_obj?.id,
    uom_id: form.value.uom_id,
    prezzo: form.value.prezzo,
  }
  if (form.value.ba_obj?.id) {
    payload.billing_account_id = form.value.ba_obj.id
  }
  const result = await execute(
    () => createRiga(props.listinoId, props.versioneId, payload),
    { successMessage: t('listini.riga_creata') }
  )
  if (result !== null) {
    emit('saved')
    close()
  }
}

function close() {
  emit('update:visible', false)
}

// Scopo: Etichetta UoM nel dropdown: "codice — descrizione (BASE)" se base.
function uomLabel(uom) {
  const base = uom.is_base ? ` ${t('listini.uom_base_suffix')}` : ''
  return `${uom.uom_codice} — ${uom.uom_descrizione}${base}`
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.STANDARD }">
    <template #header>
      <DrawerTitle :action="t('common.new')" :title="t('listini.aggiungi_prezzo_hint')" icon="pi pi-plus" />
    </template>

    <div class="app-drawer-content">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('listini.field_articolo') }} *</label>
          <ArticoloLookup v-model="form.articolo_obj" @select="onArticoloSelect" />
        </div>
        <div class="form-field">
          <label>{{ t('listini.field_ba') }}</label>
          <BillingAccountLookup v-model="form.ba_obj"
            :utilityId="listinoUtilityId"
            :placeholder="t('listini.select_ba')" />
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('listini.field_uom') }} *</label>
          <Select v-model="form.uom_id"
            :options="uomOptions"
            option-value="uom_id"
            :option-label="uomLabel"
            :placeholder="form.articolo_obj?.id ? t('catalogo.select_uom') : t('listini.uom_select_articolo_first')"
            :disabled="!form.articolo_obj?.id || uomLoading"
            :loading="uomLoading"
            :empty-message="t('listini.uom_no_operative')" />
        </div>
        <div class="form-field">
          <label>{{ t('listini.field_prezzo') }} *</label>
          <InputNumber v-model="form.prezzo" :minFractionDigits="2" :maxFractionDigits="10" />
        </div>
      </div>

      <DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>

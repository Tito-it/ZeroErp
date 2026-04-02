<script setup>
// Scopo: Drawer crea/modifica articolo con tab UoM operative, BoM e note in edit.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useArticoliStore } from '../stores/articoli'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import ArticoloUomTab from './ArticoloUomTab.vue'
import ArticoloBomTab from './ArticoloBomTab.vue'
import ArticoloNoteTab from './ArticoloNoteTab.vue'
import Drawer from 'primevue/drawer'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'

const { t } = useI18n()
const store = useArticoliStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  articoloId: { type: [String, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)

function defaultForm() {
  return {
    codice: '', descrizione: '', descrizione_breve: '',
    uom_id: null, tipo_voce_id: null, gruppo_voce_id: null,
    spesa_id: null, iva_id: null,
    conto_contabile_vendita_id: null, conto_contabile_acquisto_id: null,
    is_composito: false, is_solo_componente: false,
    requires_serial: false, voce_utility: false
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
}

async function loadDetail() {
  if (!props.articoloId) return
  const data = await store.fetchDetail(props.articoloId)
  if (!data) return
  detail.value = data
  form.value = {
    codice: data.codice || '',
    descrizione: data.descrizione || '',
    descrizione_breve: data.descrizione_breve || '',
    uom_id: data.uom_id,
    tipo_voce_id: data.tipo_voce_id,
    gruppo_voce_id: data.gruppo_voce_id,
    spesa_id: data.spesa_id,
    iva_id: data.iva_id,
    conto_contabile_vendita_id: data.conto_contabile_vendita_id,
    conto_contabile_acquisto_id: data.conto_contabile_acquisto_id,
    is_composito: data.is_composito || false,
    is_solo_componente: data.is_solo_componente || false,
    requires_serial: data.requires_serial || false,
    voce_utility: data.voce_utility || false
  }
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
  return form.value.codice?.trim() && form.value.descrizione?.trim() && form.value.uom_id != null
})

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    const payload = {
      descrizione: f.descrizione?.trim() || '',
      descrizione_breve: f.descrizione_breve?.trim() || null,
      uom_id: f.uom_id,
      tipo_voce_id: f.tipo_voce_id,
      gruppo_voce_id: f.gruppo_voce_id,
      spesa_id: f.spesa_id,
      iva_id: f.iva_id,
      conto_contabile_vendita_id: f.conto_contabile_vendita_id,
      conto_contabile_acquisto_id: f.conto_contabile_acquisto_id,
      is_composito: f.is_composito,
      is_solo_componente: f.is_solo_componente,
      requires_serial: f.requires_serial,
      voce_utility: f.voce_utility,
    }
    const result = await execute(
      () => store.update(props.articoloId, payload),
      { successMessage: t('catalogo.articolo_salvato') }
    )
    if (result) emit('saved', result)
  } else {
    const payload = {
      codice: f.codice?.trim(),
      descrizione: f.descrizione?.trim(),
      descrizione_breve: f.descrizione_breve?.trim() || null,
      uom_id: f.uom_id,
      tipo_voce_id: f.tipo_voce_id,
      gruppo_voce_id: f.gruppo_voce_id,
      spesa_id: f.spesa_id,
      iva_id: f.iva_id,
      conto_contabile_vendita_id: f.conto_contabile_vendita_id,
      conto_contabile_acquisto_id: f.conto_contabile_acquisto_id,
      is_composito: f.is_composito,
      is_solo_componente: f.is_solo_componente,
      requires_serial: f.requires_serial,
      voce_utility: f.voce_utility,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('catalogo.articolo_creato') }
    )
    if (result) emit('saved', result)
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.COMPLEX }" :dismissable="true">
    <template #header>
      <DrawerTitle :action="isEdit ? t('common.edit') : t('common.new')" :title="t('catalogo.articolo')" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('catalogo.field_codice') }}</label>
          <InputText v-model="form.codice" :disabled="isEdit" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_uom') }}</label>
          <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura" :placeholder="t('catalogo.select_uom')" />
        </div>
      </div>

      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('catalogo.field_descrizione') }}</label>
          <InputText v-model="form.descrizione" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_descrizione_breve') }}</label>
          <InputText v-model="form.descrizione_breve" />
        </div>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('catalogo.field_tipologia') }}</label>
          <LookupSelect v-model="form.tipo_voce_id" rel="vendite.articoli_tipologie" :placeholder="t('catalogo.select_tipologia')" show-clear />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_gruppo') }}</label>
          <LookupSelect v-model="form.gruppo_voce_id" rel="vendite.articoli_gruppi" :placeholder="t('catalogo.select_gruppo')" show-clear />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_spesa') }}</label>
          <LookupSelect v-model="form.spesa_id" rel="vendite.articoli_spesa" :placeholder="t('catalogo.select_spesa')" show-clear />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_iva') }}</label>
          <LookupSelect v-model="form.iva_id" rel="config.iva" :placeholder="t('catalogo.select_iva')" show-clear />
        </div>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('catalogo.field_composito') }}</label>
          <ToggleSwitch v-model="form.is_composito" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_solo_componente') }}</label>
          <ToggleSwitch v-model="form.is_solo_componente" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_voce_utility') }}</label>
          <ToggleSwitch v-model="form.voce_utility" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_requires_serial') }}</label>
          <ToggleSwitch v-model="form.requires_serial" />
        </div>
      </div>

      <!-- Tab solo in edit -->
      <TabView v-if="isEdit && detail" lazy class="mt-1">
        <TabPanel :header="t('catalogo.tab_uom')">
          <ArticoloUomTab :articolo-id="props.articoloId" />
        </TabPanel>
        <TabPanel v-if="form.is_composito" :header="t('catalogo.tab_bom')">
          <ArticoloBomTab :articolo-id="props.articoloId" />
        </TabPanel>
        <TabPanel :header="t('catalogo.tab_note')">
          <ArticoloNoteTab :articolo-id="props.articoloId" />
        </TabPanel>
      </TabView>

      <DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>

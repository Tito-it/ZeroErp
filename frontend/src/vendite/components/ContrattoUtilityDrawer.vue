<script setup>
// Scopo: Sub-drawer gestione riga utility 1:1 del contratto
//        (tipo_utenza, classe_utenza, param_1_num, param_2_txt).
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContrattiStore } from '../stores/contratti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'

const { t } = useI18n()
const store = useContrattiStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  contrattoId: { type: Number, required: true },
  utilityIniziale: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'changed'])

const form = ref({})
const utilityId = ref(null)

function populate(u) {
  if (!u) {
    form.value = {
      tipo_utenza_id: null,
      classe_utenza_id: null,
      param_1_num: null,
      param_2_txt: '',
    }
    utilityId.value = null
  } else {
    form.value = {
      tipo_utenza_id: u.tipo_utenza_id,
      classe_utenza_id: u.classe_utenza_id,
      param_1_num: u.param_1_num != null ? Number(u.param_1_num) : null,
      param_2_txt: u.param_2_txt || '',
    }
    utilityId.value = u.id
  }
}

watch(() => props.visible, (v) => {
  if (v) populate(props.utilityIniziale)
})

const canSave = computed(() => {
  if (isReadonly.value) return false
  // Tipo/classe utenza obbligatori per utility con dimensione (GAS, EE, ecc).
  // Il FE non conosce la dimensione — lascia al DB trigger la verifica.
  return true
})

async function handleSave() {
  const f = form.value
  const payload = {
    tipo_utenza_id: f.tipo_utenza_id || null,
    classe_utenza_id: f.classe_utenza_id || null,
    param_1_num: f.param_1_num != null ? String(f.param_1_num) : null,
    param_2_txt: f.param_2_txt || null,
  }
  if (utilityId.value == null) {
    const result = await execute(
      () => store.addUtility(props.contrattoId, payload),
      { successMessage: t('vendite.contratti.utility_creata') }
    )
    if (result !== null) emit('changed')
  } else {
    const result = await execute(
      () => store.updateUtility(props.contrattoId, utilityId.value, payload),
      { successMessage: t('vendite.contratti.utility_salvata') }
    )
    if (result !== null) emit('changed')
  }
}

const onClose = useDrawerClose(emit)
</script>

<template>
  <Drawer
    :visible="props.visible"
    @update:visible="val => emit('update:visible', val)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle :title="t('vendite.contratti.gestisci_utility')" :icon="MANAGE_ICONS.UTILITY" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_tipo_utenza') }}</label>
          <LookupSelect v-model="form.tipo_utenza_id" rel="config.tipi_utenze" class="w-full"
            :placeholder="t('vendite.contratti.select_tipo_utenza')" show-clear />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_classe_utenza') }}</label>
          <LookupSelect v-model="form.classe_utenza_id" rel="config.classi_utenze" class="w-full"
            :placeholder="t('vendite.contratti.select_classe_utenza')" show-clear />
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_param_1_num') }}</label>
          <InputNumber v-model="form.param_1_num" class="w-full"
            :min-fraction-digits="0" :max-fraction-digits="4"
            :invalid="campiErrati.includes('param_1_num')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('vendite.contratti.field_param_2_txt') }}</label>
          <InputText v-model="form.param_2_txt" class="w-full"
            :invalid="campiErrati.includes('param_2_txt')"
          />
        </div>
      </div>
      <FormFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="onClose" />
    </div>
  </Drawer>
</template>

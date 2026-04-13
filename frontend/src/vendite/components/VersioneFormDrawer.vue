<script setup>
// Scopo: Drawer compatto per creare una nuova versione di un listino.
// Apertura: dal pulsante "+ Nuova versione" nell'expansion riga listino.
// Campi: codice_versione (obbl.), valido_dal (obbl.), valido_al.
// Lo stato iniziale e' BOZZA (gestito dal backend).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useListiniStore } from '../stores/listini'
import { createVersione } from '../api/listini'
import { toDateString } from '../../core/utils/date'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Message from 'primevue/message'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()
const listiniStore = useListiniStore()

const props = defineProps({
  visible: { type: Boolean, default: false },
  listino: { type: Object, default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const form = ref({})

function defaultForm() {
  return {
    codice_versione: '',
    valido_dal: new Date(),
    valido_al: null,
  }
}

watch(() => props.visible, (v) => {
  if (v) form.value = defaultForm()
})

const canSave = computed(() =>
  !!form.value.codice_versione?.trim() &&
  !!form.value.valido_dal
)

const bozzeEsistenti = computed(() => {
  if (!props.listino?.id) return []
  const versioni = listiniStore.versioniByListino[props.listino.id] || []
  return versioni.filter(v => v.stato === 'BOZZA')
})

async function handleSave() {
  if (!props.listino?.id) return
  const f = form.value
  const payload = {
    codice_versione: f.codice_versione.trim(),
    valido_dal: toDateString(f.valido_dal),
    valido_al: toDateString(f.valido_al),
  }
  // execute() restituisce gia' body.data unwrappato (vedi useApiHandler).
  const result = await execute(
    () => createVersione(props.listino.id, payload),
    { successMessage: t('listini.versione_creata') }
  )
  if (result !== null) {
    emit('saved', { listinoId: props.listino.id, versione: result })
    close()
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.STANDARD }">
    <template #header>
      <DrawerTitle :action="t('common.new')" :title="t('listini.nuova_versione')" icon="pi pi-history" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listino" class="app-drawer-section">
        <h4>{{ t('listini.listino') }}: {{ listino.codice }} — {{ listino.descrizione }}</h4>
      </div>

      <Message v-if="bozzeEsistenti.length > 0" severity="warn" :closable="false" class="mb-1">
        {{ t('listini.warning_bozza_esistente', { codice: bozzeEsistenti.map(b => b.codice_versione).join(', ') }) }}
      </Message>

      <div class="form-field">
        <label>{{ t('listini.field_codice_versione') }} *</label>
        <InputText v-model="form.codice_versione" />
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('listini.field_valido_dal') }} *</label>
          <DatePicker v-model="form.valido_dal" :dateFormat="DATE_FORMAT" showIcon />
        </div>
        <div class="form-field">
          <label>{{ t('listini.field_valido_al') }}</label>
          <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar />
        </div>
      </div>

      <DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>

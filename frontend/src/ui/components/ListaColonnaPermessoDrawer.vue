<script setup>
// Scopo: Drawer crea/modifica permesso colonna (`ui.lista_colonna_permesso`).
//        Pattern UPSERT: il backend fa ON CONFLICT (colonna_id, profilo_accesso_id),
//        quindi crea ed edit usano lo stesso endpoint. In edit la coppia
//        (colonna, profilo) e' immutabile (cambiarla = creare un altro
//        permesso): mostriamo i campi readonly.
//        Catalogo colonne caricato lazy on-mount (solo create) per popolare
//        il Select. In edit i campi colonna e profilo sono read-only.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import LookupSelect from '../../core/components/LookupSelect.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import { DRAWER_WIDTH, LIVELLO_ACCESSO } from '../../core/constants'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useUiPresetAdminStore } from '../stores/uiPresetAdmin'
import { useUiPermessoAdminStore } from '../stores/uiPermessoAdmin'

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
  recordData: { type: Object, default: null },
  listaId: { type: Number, default: null },
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const { t } = useI18n()
const presetStore = useUiPresetAdminStore()
const permessoStore = useUiPermessoAdminStore()
const { execute, loading } = useApiHandler()
const injectedReadonly = useInjectReadonly()
const isReadonlyEffective = computed(
  () => props.readonly || injectedReadonly.value,
)
const isEdit = computed(() => props.mode === 'edit')

// Livelli allineati a config.livello_accesso (single source: LIVELLO_ACCESSO).
const livelliOptions = computed(() => [
  { label: t('common.livello_tutto'), value: LIVELLO_ACCESSO.TUTTO },
  { label: t('common.livello_lettura'), value: LIVELLO_ACCESSO.LETTURA },
  { label: t('common.livello_bloccato'), value: LIVELLO_ACCESSO.BLOCCATO },
])

const catalogo = ref([])
const loadingCatalogo = ref(false)

function catalogoLabel(id) {
  const c = catalogo.value.find((x) => x.id === id)
  return c ? `${c.etichetta} (${c.codice})` : ''
}

function defaultForm() {
  return {
    colonna_id: null,
    profilo_accesso_id: null,
    livello_accesso: LIVELLO_ACCESSO.BLOCCATO,
  }
}

const form = ref(defaultForm())

watch(
  () => [props.visible, props.recordData],
  async ([visible, data]) => {
    if (!visible) return
    if (isEdit.value && data) {
      form.value = {
        colonna_id: data.colonna_id,
        profilo_accesso_id: data.profilo_accesso_id,
        livello_accesso: data.livello_accesso,
      }
    } else {
      form.value = defaultForm()
      // Carica catalogo solo per il create (per il Select colonna).
      if (props.listaId != null) {
        loadingCatalogo.value = true
        try {
          catalogo.value = await presetStore.listCatalogo(props.listaId)
        } finally {
          loadingCatalogo.value = false
        }
      }
    }
  },
  { immediate: true },
)

const canSave = computed(() => {
  if (!form.value.colonna_id) return false
  if (!form.value.profilo_accesso_id) return false
  if (!form.value.livello_accesso) return false
  return true
})

async function onSave() {
  if (!canSave.value) return
  const payload = {
    colonna_id: form.value.colonna_id,
    profilo_accesso_id: form.value.profilo_accesso_id,
    livello_accesso: form.value.livello_accesso,
  }
  const result = await execute(
    () => permessoStore.upsert(payload),
    { successMessage: t('notifications.save_success') },
  )
  if (result !== null) {
    emit('saved', result)
  }
}

function onCancel() {
  emit('cancelled')
  emit('update:visible', false)
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="(v) => emit('update:visible', v)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :modal="true"
    :dismissable-mask="false"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('ui_admin.permesso')"
        icon="pi pi-shield"
      />
    </template>

    <div
      class="app-drawer-content"
      :class="{ 'app-readonly': isReadonlyEffective }"
    >
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('ui_admin.permesso_colonna') }}</label>
          <template v-if="isEdit">
            <InputText
              :model-value="recordData?.colonna_codice ? `${recordData.colonna_etichetta} (${recordData.colonna_codice})` : ''"
              readonly
            />
          </template>
          <template v-else>
            <Select
              v-model="form.colonna_id"
              :options="catalogo"
              option-value="id"
              :placeholder="t('ui_admin.permesso_seleziona_colonna')"
              :loading="loadingCatalogo"
              :filter="catalogo.length > 5"
            >
              <template #value="{ value }">
                <span v-if="value">
                  {{ catalogoLabel(value) }}
                </span>
                <span v-else class="muted">
                  {{ t('ui_admin.permesso_seleziona_colonna') }}
                </span>
              </template>
              <template #option="{ option }">
                <span>{{ option.etichetta }} <small class="muted">({{ option.codice }})</small></span>
              </template>
            </Select>
          </template>
        </div>

        <div class="form-field">
          <label>{{ t('ui_admin.permesso_profilo') }}</label>
          <template v-if="isEdit">
            <InputText
              :model-value="recordData?.profilo_accesso_codice ?? ''"
              readonly
            />
          </template>
          <template v-else>
            <LookupSelect
              v-model="form.profilo_accesso_id"
              rel="config.profili_accesso"
              show-code
              :placeholder="t('ui_admin.permesso_seleziona_profilo')"
            />
          </template>
        </div>

        <div class="form-field">
          <label>{{ t('ui_admin.permesso_livello_accesso') }}</label>
          <Select
            v-model="form.livello_accesso"
            :options="livelliOptions"
            option-label="label"
            option-value="value"
          />
        </div>
      </div>
    </div>

    <FormFooter
      v-if="!isReadonlyEffective"
      :loading="loading"
      :disabled="!canSave"
      @save="onSave"
      @cancel="onCancel"
    />
  </Drawer>
</template>

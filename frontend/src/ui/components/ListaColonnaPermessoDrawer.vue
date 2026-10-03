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
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import LookupSelect from '../../core/components/LookupSelect.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import { DRAWER_WIDTH, LIVELLO_ACCESSO, MANAGE_ICONS } from '../../core/constants'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
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
const { execute, loading, campiErrati } = useApiHandler()
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
// Modifiche non salvate: fotografia a form popolato, conferma alla chiusura
// (BB useDrawerFormPreserve). Prima del watch immediate (TDZ).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

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
      fissa()
    } else {
      form.value = defaultForm()
      // Il catalogo sotto non scrive nel form: la fotografia si fissa qui.
      fissa()
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

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('ui.admin.permesso')"
    :icon="MANAGE_ICONS.PERMISSIONS"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
    :readonly="isReadonlyEffective"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="isReadonlyEffective ? 'chiudi' : 'form'"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="onSave"
  >
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('ui.admin.permesso_colonna') }}</label>
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
            :placeholder="t('ui.admin.permesso_seleziona_colonna')"
            :invalid="campiErrati.includes('colonna_id')"
            :loading="loadingCatalogo"
            :filter="catalogo.length > 5"
          >
            <template #value="{ value }">
              <span v-if="value">
                {{ catalogoLabel(value) }}
              </span>
              <span v-else class="muted">
                {{ t('ui.admin.permesso_seleziona_colonna') }}
              </span>
            </template>
            <template #option="{ option }">
              <span>{{ option.etichetta }} <small class="muted">({{ option.codice }})</small></span>
            </template>
          </Select>
        </template>
      </div>

      <div class="form-field">
        <label>{{ t('ui.admin.permesso_profilo') }}</label>
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
            :placeholder="t('ui.admin.permesso_seleziona_profilo')"
          />
        </template>
      </div>

      <div class="form-field">
        <label>{{ t('ui.admin.permesso_livello_accesso') }}</label>
        <Select
          v-model="form.livello_accesso"
          :options="livelliOptions"
          option-label="label"
          option-value="value"
          :invalid="campiErrati.includes('livello_accesso')"
        />
      </div>
    </div>
  </AppDrawer>
</template>

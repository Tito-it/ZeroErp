<script setup>
// Scopo: Drawer crea/modifica `ui.lista_definizione` (Blocco F Fase 2 —
//        DEF-5b). Form 6 campi (codice/descrizione/schema_dati/vista_sql/
//        note/attivo). Workflow draft supportato nativamente dal trigger
//        DB: creare con `attivo=false` (o vista_sql vuoto) per registrare
//        prima che il team DB faccia atterrare la view via Liquibase.
//
//        Pattern standard:
//          - DrawerTitle + FormFooter
//          - Pre-popolazione da props.recordData in edit
//          - useApiHandler per call store
//          - Niente readonly: pagina tecnica SUPER_ADMIN-only
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Checkbox from 'primevue/checkbox'
import Message from 'primevue/message'
import AppDrawer from '../../core/components/AppDrawer.vue'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useUiDefinizioneAdminStore } from '../stores/uiDefinizioneAdmin'

const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' }, // 'create' | 'edit'
  recordId: { type: Number, default: null },
  recordData: { type: Object, default: null },
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const { t } = useI18n()
const definizioneStore = useUiDefinizioneAdminStore()
const { execute, loading, campiErrati } = useApiHandler()

const isEdit = computed(() => props.mode === 'edit')

function defaultForm() {
  return {
    codice: '',
    descrizione: '',
    schema_dati: '',
    vista_sql: '',
    note: '',
    attivo: true,
  }
}

const form = ref(defaultForm())
// Modifiche non salvate: fotografia a form popolato, conferma alla chiusura
// (BB useDrawerFormPreserve). Prima del watch immediate (TDZ).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

watch(
  () => [props.visible, props.recordData],
  ([visible, data]) => {
    if (!visible) return
    if (isEdit.value && data) {
      form.value = {
        codice: data.codice ?? '',
        descrizione: data.descrizione ?? '',
        schema_dati: data.schema_dati ?? '',
        vista_sql: data.vista_sql ?? '',
        note: data.note ?? '',
        attivo: !!data.attivo,
      }
    } else {
      form.value = defaultForm()
    }
    fissa()
  },
  { immediate: true },
)

const canSave = computed(() => {
  if (!form.value.codice?.trim()) return false
  if (!form.value.descrizione?.trim()) return false
  if (!form.value.schema_dati?.trim()) return false
  return true
})

function buildPayload() {
  // Empty string -> null per stringhe opzionali (pattern null_vs_empty
  // BE-aware): lasciamo che il BE normalizzi, ma evitiamo invio di
  // stringhe vuote che lui poi tradurrebbe.
  const payload = {
    codice: form.value.codice.trim(),
    descrizione: form.value.descrizione.trim(),
    schema_dati: form.value.schema_dati.trim(),
    attivo: form.value.attivo,
  }
  payload.vista_sql = form.value.vista_sql?.trim() || null
  payload.note = form.value.note?.trim() || null
  return payload
}

async function onSave() {
  if (!canSave.value) return
  const payload = buildPayload()
  let result
  if (isEdit.value) {
    result = await execute(
      () => definizioneStore.update(props.recordId, payload),
      { successMessage: t('notifications.save_success') },
    )
  } else {
    result = await execute(
      () => definizioneStore.create(payload),
      { successMessage: t('notifications.save_success') },
    )
  }
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
    :title="t('ui.admin.definizione')"
    :icon="MANAGE_ICONS.LIST"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="onSave"
  >
    <div class="form-grid">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('ui.admin.definizione_codice') }}</label>
          <InputText v-model="form.codice" maxlength="80"
            :invalid="campiErrati.includes('codice')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('ui.admin.definizione_schema_dati') }}</label>
          <InputText v-model="form.schema_dati" maxlength="80"
            :invalid="campiErrati.includes('schema_dati')"
          />
        </div>
      </div>

      <div class="form-field">
        <label>{{ t('ui.admin.definizione_descrizione') }}</label>
        <InputText v-model="form.descrizione" maxlength="200"
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>

      <div class="form-field">
        <label>{{ t('ui.admin.definizione_vista_sql') }}</label>
        <InputText v-model="form.vista_sql" maxlength="120"
          :invalid="campiErrati.includes('vista_sql')"
        />
        <Message
          severity="info"
          :closable="false"
          size="small"
          class="mt-025"
        >
          {{ t('ui.admin.definizione_vista_sql_hint') }}
        </Message>
      </div>

      <div class="form-field">
        <label>{{ t('ui.admin.definizione_note') }}</label>
        <Textarea v-model="form.note" rows="3" auto-resize
          :invalid="campiErrati.includes('note')"
        />
      </div>

      <div class="form-field form-field-inline">
        <Checkbox v-model="form.attivo" binary input-id="ui-def-attivo"
          :invalid="campiErrati.includes('attivo')"
        />
        <label for="ui-def-attivo">{{ t('common.active') }}</label>
      </div>
      <Message
        v-if="!form.attivo"
        severity="warn"
        :closable="false"
        size="small"
      >
        {{ t('ui.admin.definizione_disattivata_hint') }}
      </Message>
    </div>
  </AppDrawer>
</template>

<style scoped>
.form-field-inline {
  flex-direction: row;
  align-items: center;
  gap: 0.5rem;
}
</style>

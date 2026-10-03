<script setup>
// Scopo: Drawer modifica template email (solo edit, i template sono seedati).
// Mostra variabili disponibili per il template, permette preview HTML
// renderizzata dal BE. Preview confinata in iframe sandbox per non eseguire
// script/CSS invasivo nella shell admin (vedi A12/C5 del WIP frontend amm).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import AppDrawer from '../../core/components/AppDrawer.vue'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { useEmailTemplatesStore } from '../stores/emailTemplates'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { previewEmailTemplate } from '../api/amministrazione'



const props = defineProps({
  visible: Boolean,
  mode: String,
  templateId: Number
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const { t } = useI18n()
const store = useEmailTemplatesStore()
const isReadonly = useInjectReadonly()
const { execute, loading: saving } = useApiHandler()

const form = ref({})
// Modifiche non salvate: fotografia dopo il caricamento del dettaglio, e
// chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })
const previewHtml = ref('')
const previewLoading = ref(false)
const showPreview = ref(false)

const canSave = computed(() => {
  if (isReadonly.value) return false
  const f = form.value
  return f.oggetto?.trim() && f.corpo_html?.trim()
})

watch(() => props.visible, async (vis) => {
  if (!vis) { showPreview.value = false; return }
  previewHtml.value = ''
  showPreview.value = false
  if (props.templateId) {
    await store.fetchDetail(props.templateId)
    const d = store.currentTemplate
    form.value = {
      codice: d?.codice || '',
      oggetto: d?.oggetto || '',
      corpo_html: d?.corpo_html || '',
      corpo_testo: d?.corpo_testo || '',
      lingua: d?.lingua || 'it',
      variabili_disponibili: d?.variabili_disponibili || []
    }
    fissa()
  }
})

async function handleSave() {
  if (isReadonly.value) return
  const payload = {
    oggetto: form.value.oggetto,
    corpo_html: form.value.corpo_html,
    corpo_testo: form.value.corpo_testo || null
  }
  const result = await execute(
    () => store.update(props.templateId, payload),
    { successMessage: t('notifications.save_success') }
  )
  // Salvataggio fallito: il drawer resta aperto col lavoro dell'operatore (il
  // padre su `saved` chiude — prima chiudeva anche sull'errore, e il lavoro
  // si perdeva senza conferma).
  if (result === null) return
  fissa()
  emit('saved')
}

async function handlePreview() {
  if (!props.templateId) return
  previewLoading.value = true
  try {
    // Costruisci variabili di esempio
    const vars = {}
    for (const v of form.value.variabili_disponibili || []) {
      vars[v] = `[${v}]`
    }
    const res = await previewEmailTemplate(props.templateId, vars)
    const data = res.data?.data
    previewHtml.value = data?.corpo_html || ''
    showPreview.value = true
  } catch {
    previewHtml.value = ''
  } finally {
    previewLoading.value = false
  }
}
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('amministrazione.email_template_title')"
    :icon="NAV_ICONS.TEMPLATE_EMAIL"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.COMPLEX"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="saving"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >
    <div class="form-grid">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('amministrazione.email_codice') }}</label>
          <InputText :modelValue="form.codice" disabled fluid />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.email_lingua') }}</label>
          <InputText :modelValue="form.lingua" disabled fluid />
        </div>
      </div>

      <div class="form-field" v-if="form.variabili_disponibili?.length">
        <label>{{ t('amministrazione.email_variabili') }}</label>
        <div class="email-variabili">
          <Tag v-for="v in form.variabili_disponibili" :key="v"
               :value="`{{${v}}}`" severity="info" />
        </div>
      </div>

      <div class="form-field">
        <label>{{ t('amministrazione.email_oggetto') }}</label>
        <InputText v-model="form.oggetto" :disabled="isReadonly" fluid />
      </div>

      <div class="form-field">
        <label>{{ t('amministrazione.email_corpo_html') }}</label>
        <Textarea v-model="form.corpo_html" :rows="12" fluid autoResize :disabled="isReadonly" />
      </div>

      <div class="form-field">
        <label>{{ t('amministrazione.email_corpo_testo') }}</label>
        <Textarea v-model="form.corpo_testo" :rows="5" fluid autoResize :disabled="isReadonly" />
      </div>

      <!-- `app-escape`: l'anteprima e' consultazione, resta cliccabile anche in
           sola lettura (il corpo protetto spegne tutto il resto). -->
      <div class="email-preview-azioni app-escape">
        <Button
          :label="t('amministrazione.email_preview')"
          :icon="MANAGE_ICONS.ANTEPRIMA"
          :loading="previewLoading"
          outlined
          size="small"
          @click="handlePreview"
        />
      </div>

      <!-- Preview confinata in iframe sandbox per non eseguire script/event/CSS
           dal corpo template (admin-modificabile). srcdoc isola l'HTML dal
           contesto della shell, sandbox="" rimuove tutti i privilegi. -->
      <div v-if="showPreview" class="app-preview-box">
        <iframe
          class="email-preview-iframe"
          sandbox=""
          :srcdoc="previewHtml"
        />
      </div>
    </div>
  </AppDrawer>
</template>

<style scoped>
.email-variabili {
  display: flex;
  gap: 0.25rem;
  flex-wrap: wrap;
}
.email-preview-azioni {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
/* `#fff` voluto: e' il fondo dell'email come la vedra' il destinatario, non
   una superficie dell'app — non segue il tema scuro. */
.email-preview-iframe {
  width: 100%;
  min-height: 300px;
  border: 0;
  background: #fff;
}
</style>

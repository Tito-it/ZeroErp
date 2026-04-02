<script setup>
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import { DRAWER_WIDTH } from '../../core/constants'
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
const previewHtml = ref('')
const previewLoading = ref(false)
const showPreview = ref(false)

const canSave = computed(() => {
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
  }
})

async function handleSave() {
  const payload = {
    oggetto: form.value.oggetto,
    corpo_html: form.value.corpo_html,
    corpo_testo: form.value.corpo_testo || null
  }
  await execute(
    () => store.update(props.templateId, payload),
    { successMessage: t('notifications.save_success') }
  )
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
  <Drawer
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle
        :action="t('common.edit')"
        title="Template Email"
        icon="pi pi-file-edit"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('amm.email_codice') }}</label>
            <InputText :modelValue="form.codice" disabled fluid />
          </div>
          <div class="form-field">
            <label>{{ t('amm.email_lingua') }}</label>
            <InputText :modelValue="form.lingua" disabled fluid />
          </div>
        </div>

        <div class="form-field" v-if="form.variabili_disponibili?.length">
          <label>{{ t('amm.email_variabili') }}</label>
          <div style="display: flex; gap: 0.25rem; flex-wrap: wrap;">
            <Tag v-for="v in form.variabili_disponibili" :key="v"
                 :value="`{{${v}}}`" severity="info" />
          </div>
        </div>

        <div class="form-field">
          <label>{{ t('amm.email_oggetto') }}</label>
          <InputText v-model="form.oggetto" fluid />
        </div>

        <div class="form-field">
          <label>{{ t('amm.email_corpo_html') }}</label>
          <Textarea v-model="form.corpo_html" :rows="12" fluid autoResize />
        </div>

        <div class="form-field">
          <label>{{ t('amm.email_corpo_testo') }}</label>
          <Textarea v-model="form.corpo_testo" :rows="5" fluid autoResize />
        </div>

        <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
          <Button
            :label="t('amm.email_preview')"
            icon="pi pi-eye"
            :loading="previewLoading"
            outlined
            size="small"
            @click="handlePreview"
          />
        </div>

        <div v-if="showPreview" class="app-preview-box">
          <div v-html="previewHtml" />
        </div>
      </div>
    </div>

    <template #footer>
      <DrawerFooter
        :loading="saving"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="emit('cancelled')"
      />
    </template>
  </Drawer>
</template>

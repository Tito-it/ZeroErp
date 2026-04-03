<script setup>
// Scopo: Drawer per creare/modificare un override personale su un parametro.
// Mostra la catena di fallback (default -> emittente -> gruppo -> utente)
// e consente all'operatore di impostare il proprio valore.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useImpostazioniStore } from '../stores/impostazioni'
import { DRAWER_WIDTH } from '../../core/constants'
import ParameterFallback from '../../core/components/ParameterFallback.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'

const { t } = useI18n()
const store = useImpostazioniStore()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: Boolean,
  parameter: { type: Object, default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const overrideValue = ref('')

const isEdit = computed(() => props.parameter?.user_override_id != null)

watch(() => props.visible, (v) => {
  if (!v || !props.parameter) return
  overrideValue.value = props.parameter.user_value ?? props.parameter.resolved_value ?? ''
})

const canSave = computed(() => overrideValue.value !== '')

async function handleSave() {
  if (!props.parameter) return
  const result = await execute(
    () => store.saveOverride(props.parameter.code, overrideValue.value),
    { successMessage: t('impostazioni.override_saved') }
  )
  if (result) {
    await store.fetchList()
    emit('saved', result)
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.SIMPLE }" :dismissable="true">
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('impostazioni.override_title')"
      />
    </template>

    <div class="app-drawer-content" v-if="parameter">
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('impostazioni.col_code') }}</label>
          <InputText :model-value="parameter.code" disabled />
        </div>

        <div class="form-field" v-if="parameter.description">
          <label>{{ t('impostazioni.col_description') }}</label>
          <div class="parameter-description">{{ parameter.description }}</div>
        </div>

        <div class="form-field">
          <label>{{ t('impostazioni.fallback_chain') }}</label>
          <ParameterFallback :parameter="parameter" />
        </div>

        <div class="form-field">
          <label>{{ t('impostazioni.your_override') }}</label>
          <InputText v-model="overrideValue" :placeholder="t('impostazioni.override_placeholder')" />
        </div>
      </div>

      <DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="close" />
    </div>
  </Drawer>
</template>

<style scoped>
.parameter-description {
  color: var(--p-text-muted-color);
  font-size: 0.85rem;
  padding: 0.25rem 0;
}
</style>

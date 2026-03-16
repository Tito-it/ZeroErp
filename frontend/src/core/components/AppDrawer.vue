<script setup>
import { useI18n } from 'vue-i18n'
import DrawerTitle from './DrawerTitle.vue'
import Drawer from 'primevue/drawer'
import Button from 'primevue/button'

const { t } = useI18n()

defineProps({
  visible: { type: Boolean, required: true },
  title: { type: String, required: true },
  width: { type: String, default: '640px' },
  loading: { type: Boolean, default: false },
  saveDisabled: { type: Boolean, default: false },
  saveLabel: { type: String, default: null },
  cancelLabel: { type: String, default: null }
})

const emit = defineEmits(['update:visible', 'save', 'cancel'])

function handleCancel() {
  emit('cancel')
  emit('update:visible', false)
}

function handleSave() {
  emit('save')
}
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: width }"
    :modal="true"
    :dismissable="true"
    @update:visible="emit('update:visible', $event)"
  >
    <template #header>
      <DrawerTitle :title="title" />
    </template>

    <div class="drawer-body">
      <slot />
    </div>

    <template #footer>
      <div class="drawer-footer">
        <Button
          :label="cancelLabel || t('common.cancel')"
          severity="secondary"
          text
          @click="handleCancel"
          :disabled="loading"
        />
        <Button
          :label="saveLabel || t('common.save')"
          @click="handleSave"
          :loading="loading"
          :disabled="saveDisabled || loading"
        />
      </div>
    </template>
  </Drawer>
</template>

<style scoped>
.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 0.25rem;
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--app-drawer-footer-border);
}
</style>

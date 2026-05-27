<script setup>
import DrawerTitle from './DrawerTitle.vue'
import FormFooter from './FormFooter.vue'
import Drawer from 'primevue/drawer'

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
      <FormFooter
        :save-label="saveLabel"
        :cancel-label="cancelLabel"
        :loading="loading"
        :disabled="saveDisabled"
        @cancel="handleCancel"
        @save="handleSave"
      />
    </template>
  </Drawer>
</template>

<style scoped>
.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 0.25rem;
}
</style>

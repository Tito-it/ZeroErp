<script setup>
import DrawerTitle from './DrawerTitle.vue'
import FormFooter from './FormFooter.vue'
import Drawer from 'primevue/drawer'
import { gestoreVisibile } from '../composables/useDrawerFormPreserve'

const props = defineProps({
  visible: { type: Boolean, required: true },
  title: { type: String, required: true },
  width: { type: String, default: '640px' },
  loading: { type: Boolean, default: false },
  saveDisabled: { type: Boolean, default: false },
  saveLabel: { type: String, default: null },
  cancelLabel: { type: String, default: null },
  // Modifiche non salvate: il consumatore passa `modificato` e
  // `chiudiConConferma` del suo useDrawerFormPreserve. Il guscio colora la
  // scritta dell'azione e chiede conferma su ogni uscita (X, ESC, clic fuori,
  // Annulla). Default: si esce e basta.
  action: { type: String, default: '' },
  modificato: { type: Boolean, default: false },
  confermaUscita: { type: Function, default: (chiudi) => chiudi() },
})

const emit = defineEmits(['update:visible', 'save', 'cancel'])

function handleCancel() {
  props.confermaUscita(() => {
    emit('cancel')
    emit('update:visible', false)
  })
}

function handleSave() {
  emit('save')
}
const suVisibile = gestoreVisibile(emit, handleCancel)
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: width }"
    :modal="true"
    :dismissable="true"
    @update:visible="suVisibile"
  >
    <template #header>
      <DrawerTitle :title="title" :action="action" :modificato="modificato" />
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

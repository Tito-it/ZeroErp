<script setup>
// Scopo: Select header "Lista corrente" — popola dropdown via API
//        admin (skip filtri permessi colonna). Riusa LookupSelect non
//        e' adatto: il backend non e' un lookup `id/codice/descrizione`
//        ma una API dedicata, e voglio caricare solo quando la pagina
//        admin si apre (non a ogni mount).
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import Message from 'primevue/message'
import { useUiAdminStore } from '../stores/uiAdmin'

defineProps({
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['change'])

const { t } = useI18n()
const store = useUiAdminStore()

onMounted(() => {
  store.loadListe().catch(() => { /* errore gia' in store.lastError */ })
})

function onChange(event) {
  store.selectLista(event.value)
  emit('change', event.value)
}
</script>

<template>
  <div class="lista-corrente-select">
    <label class="lista-corrente-label">
      {{ t('ui.admin.lista_corrente') }}
    </label>
    <Select
      :model-value="store.listaCorrenteId"
      :options="store.liste"
      :loading="store.loading"
      :disabled="disabled || store.loading"
      option-label="descrizione"
      option-value="id"
      :placeholder="t('ui.admin.lista_corrente_placeholder')"
      :filter="store.liste.length > 5"
      :show-clear="true"
      @change="onChange"
    />
    <Message
      v-if="store.lastError"
      severity="error"
      :closable="false"
      size="small"
      class="mt-025"
    >
      {{ t('ui.admin.lista_load_error') }}
    </Message>
  </div>
</template>

<style scoped>
.lista-corrente-select {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.lista-corrente-label {
  font-weight: 500;
  font-size: var(--app-font-size-base);
}
:deep(.p-select) {
  min-width: 280px;
}
</style>

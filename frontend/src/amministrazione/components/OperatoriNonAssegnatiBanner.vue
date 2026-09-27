<script setup>
// Scopo: banner informativo per il refactor operatore-emittenti.
// Mostrato in OperatoriListView quando esistono operatori che non sono
// stati ancora assegnati a un emittente fiscale durante la transizione
// (decisione D1 del WIP: "advise, don't enforce").
//
// Nascosto se count == 0.
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import { STATUS_ICONS } from '../../core/constants'

const { t } = useI18n()
defineProps({
  count: { type: Number, required: true },
})
</script>

<template>
  <Message v-if="count > 0" severity="warn" :closable="false" class="mt-05">
    <template #icon>
      <i :class="STATUS_ICONS.ERRORE" />
    </template>
    <strong>{{ t('amministrazione.banner_non_assegnati_title', { count }) }}</strong>
    <div class="app-banner-detail">
      {{ t('amministrazione.banner_non_assegnati_detail') }}
    </div>
  </Message>
</template>

<style scoped>
.app-banner-detail {
  font-size: 0.875rem;
  margin-top: 0.25rem;
}
</style>

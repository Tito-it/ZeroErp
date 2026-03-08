<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import InputNumber from 'primevue/inputnumber'
import Button from 'primevue/button'

const { t } = useI18n()

const props = defineProps({
  page: { type: Number, required: true },
  totalPages: { type: Number, required: true },
  totalRecords: { type: Number, required: true }
})

const emit = defineEmits(['go-to-page'])

const targetPage = ref(null)

function handleGoToPage() {
  if (targetPage.value != null) {
    emit('go-to-page', targetPage.value)
    targetPage.value = null
  }
}
</script>

<template>
  <div class="pagination-info">
    <span class="page-status">
      {{ t('pagination.page_of', { page: props.page, total: props.totalPages }) }}
      &mdash; {{ props.totalRecords }} {{ props.totalRecords === 1 ? 'record' : 'record' }}
    </span>

    <div class="go-to-page" v-if="props.totalPages > 1">
      <InputNumber
        v-model="targetPage"
        :min="1"
        :max="props.totalPages"
        :placeholder="t('pagination.go_to_page')"
        size="small"
        :input-style="{ width: '5rem' }"
        @keydown.enter="handleGoToPage"
      />
      <Button
        icon="pi pi-arrow-right"
        size="small"
        severity="secondary"
        text
        @click="handleGoToPage"
        :disabled="targetPage == null"
      />
    </div>
  </div>
</template>

<style scoped>
.pagination-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0;
  font-size: var(--app-font-size-sm);
  color: var(--p-text-muted-color);
}

.page-status {
  white-space: nowrap;
}

.go-to-page {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
</style>

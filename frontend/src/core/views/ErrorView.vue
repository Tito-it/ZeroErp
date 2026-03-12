<script setup>
// Scopo: pagina errore parametrica — legge errorKey e errorIcon dalla route meta.
// Sostituisce ForbiddenView e NotFoundView.
import { useI18n } from 'vue-i18n'
import { useRouter, useRoute } from 'vue-router'
import StatusPage from '../components/StatusPage.vue'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
</script>

<template>
  <StatusPage
    :icon="route.meta.errorIcon || 'pi pi-exclamation-triangle'"
    :title="t(`errors.${route.meta.errorKey}_title`)"
    :message="t(`errors.${route.meta.errorKey}_message`)"
    :action-label="t('errors.back_home')"
    action-icon="pi pi-home"
    @action="router.push('/')"
  />
</template>

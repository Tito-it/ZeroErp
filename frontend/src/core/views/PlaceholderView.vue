<script setup>
// Scopo: pagina placeholder riutilizzabile per aree non ancora sviluppate.
// Deriva la chiave i18n da route.meta.domain + route.meta.menuKey (es. amm-software + operatori → amm_software_operatori).
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import StatusPage from '../components/StatusPage.vue'
import { STATUS_ICONS } from '../constants'

const { t, tm, te } = useI18n()
const route = useRoute()

const props = defineProps({
  title: { type: String, default: '' },
  features: { type: Array, default: () => [] }
})

// Deriva la chiave placeholder da domain + menuKey (hyphen → underscore)
function placeholderKey() {
  const { domain, menuKey } = route.meta
  if (domain && menuKey) return `${domain}_${menuKey}`.replace(/-/g, '_')
  return null
}

const displayTitle = computed(() => {
  if (props.title) return props.title
  const key = placeholderKey()
  if (key && te(`placeholder.${key}.title`)) return t(`placeholder.${key}.title`)
  return t('placeholder.wip_title')
})

const displayFeatures = computed(() => {
  if (props.features.length > 0) return props.features
  const key = placeholderKey()
  if (key) {
    const raw = tm(`placeholder.${key}.features`)
    return Array.isArray(raw) ? raw : []
  }
  return []
})
</script>

<template>
  <StatusPage
    :icon="STATUS_ICONS.IN_COSTRUZIONE"
    :title="displayTitle"
    :message="t('placeholder.wip_message')"
    :features="displayFeatures"
    :features-label="t('placeholder.coming_soon')"
    show-card
  />
</template>

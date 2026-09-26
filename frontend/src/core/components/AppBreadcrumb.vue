<script setup>
// Scopo: breadcrumb automatico derivato dalla route meta (domain + menuKey)
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import { resolveTabLabel } from '../navigation'

const route = useRoute()
const { t } = useI18n()

const crumbs = computed(() => {
  const { domain, errorKey } = route.meta

  // Pagine errore
  if (errorKey) return [t(`errors.${errorKey}_title`)]

  // Home
  if (!domain || domain === 'home') return [t('nav.home')]

  // Dominio + eventuale voce menu L2 (via utility condivisa)
  const result = [t(`nav.${domain}`)]
  const menuLabel = resolveTabLabel(route.meta, t)
  // resolveTabLabel ritorna la label del menuKey se presente, altrimenti la label dominio.
  // Per il breadcrumb aggiungiamo il secondo segmento solo se e' diverso dal dominio.
  if (menuLabel && menuLabel !== result[0]) result.push(menuLabel)
  return result
})
</script>

<template>
  <nav v-if="crumbs.length > 0" class="app-breadcrumb" aria-label="Breadcrumb">
    <span
      v-for="(crumb, idx) in crumbs"
      :key="idx"
      class="breadcrumb-item"
      :class="{ active: idx === crumbs.length - 1 }"
    >
      <span class="breadcrumb-separator" v-if="idx > 0">/</span>
      {{ crumb }}
    </span>
  </nav>
</template>

<style scoped>
.app-breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.5rem 0;
  font-size: var(--app-font-size-sm);
  color: var(--app-text-muted);
}

.breadcrumb-item.active {
  color: var(--app-text-color);
  font-weight: 500;
}

.breadcrumb-separator {
  margin: 0 0.25rem;
  color: var(--app-text-muted);
}
</style>

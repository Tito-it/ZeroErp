<script setup>
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth'
const { t, locale } = useI18n()
const route = useRoute()
const auth = useAuthStore()

const areaTitle = computed(() => {
  const meta = route.meta
  const parts = []

  if (meta.domain) {
    parts.push(t(`nav.${meta.domain}`))
  }
  if (meta.section) {
    parts.push(meta.section)
  }

  return parts.join(' / ')
})

const companyName = computed(() => {
  const em = auth.user?.emittente
  return em?.ragione_sociale_completa || em?.emittente_descrizione || ''
})

const formattedDate = computed(() => {
  const now = new Date()
  return now.toLocaleDateString(locale.value === 'it' ? 'it-IT' : 'en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  })
})
</script>

<template>
  <header class="app-topbar">
    <div class="topbar-left">
      <i class="pi pi-building"></i>
      <span v-if="companyName" class="topbar-company">{{ companyName }}</span>
    </div>

    <div class="topbar-center">
      <span class="topbar-area-title">{{ areaTitle }}</span>
    </div>

    <div class="topbar-right">
      <span class="topbar-date">{{ formattedDate }}</span>
    </div>
  </header>
</template>

<style scoped>
.app-topbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  height: var(--app-topbar-height);
  min-height: var(--app-topbar-height);
  padding: 0 var(--app-content-padding);
  background: var(--app-topbar-bg);
  border-bottom: 1px solid var(--app-topbar-border);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.topbar-left i {
  font-size: 0.9rem;
}

.topbar-company {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topbar-center {
  display: flex;
  align-items: center;
  justify-content: center;
}

.topbar-area-title {
  font-size: var(--app-font-size-base);
  font-weight: 500;
  color: var(--app-topbar-breadcrumb-active-color);
  white-space: nowrap;
}

.topbar-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.topbar-date {
  white-space: nowrap;
}

/* Tablet — il nome azienda si tronca con ellipsis, non sparisce */
@media (max-width: 768px) {
  .topbar-company {
    max-width: 120px;
  }
}
</style>

<script setup>
// Scopo: topbar principale — emittente, area title, context chip, ricerca, data.
// Su mobile mostra hamburger per aprire il drawer sidebar.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import { useAuthStore } from '../../stores/auth'
import { useUiStore } from '../../stores/ui'
import { useContextStore } from '../../stores/context'
import { resolveTabLabel } from '../navigation'
import SearchDrawer from './SearchDrawer.vue'

const { t, locale } = useI18n()
const route = useRoute()
const auth = useAuthStore()
const ui = useUiStore()
const context = useContextStore()

defineProps({
  showHamburger: { type: Boolean, default: false }
})
const emit = defineEmits(['toggle-menu'])

const areaTitle = computed(() => {
  return resolveTabLabel(route.meta, t) || ''
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
      <!-- Hamburger su mobile -->
      <Button
        v-if="showHamburger"
        icon="pi pi-bars"
        text
        rounded
        size="small"
        class="topbar-hamburger"
        @click="emit('toggle-menu')"
      />
      <i v-else class="pi pi-building"></i>
      <span v-if="companyName" class="topbar-company">{{ companyName }}</span>
    </div>

    <div class="topbar-center">
      <span class="topbar-area-title">{{ areaTitle }}</span>
    </div>

    <div class="topbar-right">
      <!-- Chip contesto globale -->
      <Chip
        v-if="context.hasContext"
        :label="context.contextLabel"
        removable
        class="context-chip"
        @remove="context.clearContext()"
      >
        <template #default>
          <i :class="context.contextIcon" class="context-chip-icon" />
          <span class="context-chip-label">{{ context.contextLabel }}</span>
        </template>
      </Chip>

      <!-- Pulsante ricerca universale -->
      <Button
        icon="pi pi-search"
        text
        rounded
        size="small"
        v-tooltip.bottom="t('context.tooltip_search')"
        class="topbar-search-btn"
        @click="ui.openSearchDrawer()"
      />

      <span class="topbar-date">{{ formattedDate }}</span>
    </div>
  </header>

  <SearchDrawer v-model:visible="ui.searchDrawerVisible" />
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

.topbar-hamburger {
  color: var(--app-topbar-breadcrumb-color);
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
  gap: 0.5rem;
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.topbar-date {
  white-space: nowrap;
}

.topbar-search-btn {
  color: var(--app-topbar-breadcrumb-color);
}

.topbar-search-btn:hover {
  color: var(--app-topbar-breadcrumb-active-color);
}

/* Chip contesto globale */
.context-chip {
  cursor: default;
  font-size: var(--app-font-size-sm);
}

.context-chip-icon {
  margin-right: 0.35rem;
  font-size: 0.8rem;
}

.context-chip-label {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Mobile — nasconde data e azienda, semplifica */
@media (max-width: 767px) {
  .topbar-company,
  .topbar-date {
    display: none;
  }

  .topbar-left i.pi-building {
    display: none;
  }

  .context-chip-label {
    max-width: 120px;
  }
}

/* Tablet — il nome azienda si tronca con ellipsis */
@media (max-width: 1024px) and (min-width: 768px) {
  .topbar-company {
    max-width: 120px;
  }

  .context-chip-label {
    max-width: 120px;
  }
}
</style>

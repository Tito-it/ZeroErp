<script setup>
// Scopo: stato DOMINIO della sidebar morfica — pulsante Home + titolo dominio + voci menu L2.
// Icona stella per impostare la pagina preferita per il dominio.
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { computed, inject, ref } from 'vue'
import { useNavigationStore } from '../../stores/navigation'
import { useTabsStore } from '../../stores/tabs'
import SidebarItem from './SidebarItem.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const nav = useNavigationStore()
const tabs = useTabsStore()
const isCollapsed = inject('sidebarCollapsed', ref(false))

const emit = defineEmits(['navigate'])

const domainLabel = computed(() => {
  if (!nav.currentDomain) return ''
  return t(`nav.${nav.currentDomain}`)
})

function handleBackHome() {
  nav.clearDomain()
  router.push('/')
  emit('navigate')
}

function handleMenuClick(item) {
  // Apre la tab (o attiva quella esistente) — se limite raggiunto, blocca navigazione
  const opened = tabs.openTab({
    path: item.to,
    label: t(`nav_menu.${nav.currentDomain}.${item.key}`),
    domain: nav.currentDomain,
    icon: item.icon
  })
  if (!opened) return
  router.push(item.to)
  emit('navigate')
}

function handleToggleFavorite(item) {
  if (nav.isFavorite(item.to)) {
    nav.clearFavorite(nav.currentDomain)
  } else {
    nav.setFavorite(nav.currentDomain, item.to)
  }
}
</script>

<template>
  <div class="sidebar-domain">
    <!-- Pulsante ← Home -->
    <SidebarItem
      icon="pi pi-arrow-left"
      :label="t('nav.back_home')"
      class="back-home"
      @click="handleBackHome"
    />

    <div class="sidebar-divider"></div>

    <!-- Titolo dominio (solo se sidebar espansa) -->
    <div v-if="!isCollapsed" class="domain-title">
      {{ domainLabel }}
    </div>

    <!-- Voci menu L2 -->
    <SidebarItem
      v-for="item in nav.currentMenu"
      :key="item.key"
      :icon="item.icon"
      :label="t(`nav_menu.${nav.currentDomain}.${item.key}`)"
      :active="route.path === item.to"
      @click="handleMenuClick(item)"
    >
      <span class="menu-item-label">
        {{ t(`nav_menu.${nav.currentDomain}.${item.key}`) }}
      </span>
      <!-- Stella preferito -->
      <i
        v-if="!isCollapsed"
        class="pi favorite-star"
        :class="nav.isFavorite(item.to) ? 'pi-star-fill' : 'pi-star'"
        @click.stop="handleToggleFavorite(item)"
        v-tooltip.right="nav.isFavorite(item.to) ? t('nav.remove_favorite') : t('nav.set_favorite')"
      ></i>
    </SidebarItem>
  </div>
</template>

<style scoped>
.sidebar-domain {
  display: flex;
  flex-direction: column;
  gap: var(--app-sidebar-item-gap);
}

.domain-title {
  padding: 0.4rem 0.75rem;
  font-size: var(--app-font-size-sm);
  font-weight: 600;
  color: var(--p-text-muted-color);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.menu-item-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.favorite-star {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  opacity: 0;
  transition: opacity var(--app-transition-fast), color var(--app-transition-fast);
  cursor: pointer;
}

.sidebar-item:hover .favorite-star {
  opacity: 0.6;
}

.favorite-star:hover {
  opacity: 1 !important;
  color: var(--p-yellow-400);
}

.favorite-star.pi-star-fill {
  opacity: 1;
  color: var(--p-yellow-400);
}

.back-home {
  color: var(--p-text-muted-color);
}

.back-home:hover {
  color: var(--p-text-color);
}
</style>

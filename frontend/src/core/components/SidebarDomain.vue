<script setup>
// Scopo: stato DOMINIO della sidebar morfica — pulsante Home + titolo dominio + voci menu L2.
// Icona stella per impostare la pagina preferita per il dominio.
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { computed, inject, ref } from 'vue'
import { useNavigationStore } from '../../stores/navigation'
import { useTabsStore } from '../../stores/tabs'
import { useNotify } from '../composables/useNotify'
import { useNavigationFavorites } from '../composables/useNavigationFavorites'
import { NAV_ICONS, resolveNavigationLabel } from '../navigation'
import SidebarItem from './SidebarItem.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const nav = useNavigationStore()
const tabs = useTabsStore()
const notify = useNotify()
const { isMenuItemAllowed } = useNavigationFavorites()
const isCollapsed = inject('sidebarCollapsed', ref(false))

const visibleMenu = computed(() => nav.currentMenu.filter(isMenuItemAllowed))

const emit = defineEmits(['navigate'])
const openGroups = ref({})

const domainLabel = computed(() => {
  if (!nav.currentDomain) return ''
  return resolveNavigationLabel({ domain: nav.currentDomain }, t) || ''
})

function itemLabel(item) {
  return resolveNavigationLabel({ domain: nav.currentDomain, menuKey: item.key }, t) || item.key
}

function hasChildren(item) {
  return Array.isArray(item.children) && item.children.length > 0
}

function flatChildren(item) {
  return hasChildren(item) ? item.children : []
}

function isItemActive(item) {
  if (item.to && route.path === item.to) return true
  return flatChildren(item).some(child => route.path === child.to)
}

function isGroupOpen(item) {
  return openGroups.value[item.key] !== false || flatChildren(item).some(child => route.path === child.to)
}

function handleBackHome() {
  nav.clearDomain()
  router.push('/')
  emit('navigate')
}

function handleLeafClick(item) {
  // Apre la tab (o attiva quella esistente) — se limite raggiunto, blocca navigazione
  const opened = tabs.openTab({
    path: item.to,
    label: itemLabel(item),
    domain: nav.currentDomain,
    menuKey: item.key,
    icon: item.icon
  })
  if (!opened) return
  router.push(item.to)
  emit('navigate')
}

function handleMenuClick(item) {
  if (!hasChildren(item)) {
    handleLeafClick(item)
    return
  }
  if (isCollapsed.value) {
    handleLeafClick(item.children[0])
    return
  }
  openGroups.value = {
    ...openGroups.value,
    [item.key]: !isGroupOpen(item)
  }
}

function handleToggleFavorite(item) {
  if (!item.to) return
  const changed = nav.toggleFavorite(nav.currentDomain, item.to)
  if (!changed) {
    notify.warn(t('nav.preferiti_limite_raggiunto'))
  }
}
</script>

<template>
  <div class="sidebar-domain">
    <!-- Pulsante ← Home -->
    <SidebarItem
      :icon="NAV_ICONS.BACK"
      :label="t('nav.back_home')"
      class="back-home"
      @click="handleBackHome"
    />

    <div class="sidebar-divider"></div>

    <!-- Titolo dominio (solo se sidebar espansa) -->
    <div v-if="!isCollapsed" class="domain-title">
      {{ domainLabel }}
    </div>

    <!-- Voci menu L2 (filtrate su requireArea: una voce puntata su area
         BLOCCATA non viene mostrata) -->
    <template v-for="item in visibleMenu" :key="item.key">
      <SidebarItem
        :icon="item.icon"
        :label="itemLabel(item)"
        :active="isItemActive(item)"
        @click="handleMenuClick(item)"
      >
        <span class="menu-item-label">
          {{ itemLabel(item) }}
        </span>
        <i
          v-if="!isCollapsed && hasChildren(item)"
          class="pi group-chevron"
          :class="isGroupOpen(item) ? 'pi-chevron-down' : 'pi-chevron-right'"
        ></i>
        <!-- Stella preferito -->
        <i
          v-else-if="!isCollapsed"
          class="pi favorite-star"
          :class="nav.isFavoriteOfDomain(nav.currentDomain, item.to) ? 'pi-star-fill' : 'pi-star'"
          @click.stop="handleToggleFavorite(item)"
          v-tooltip.right="nav.isFavoriteOfDomain(nav.currentDomain, item.to) ? t('nav.remove_favorite') : t('nav.set_favorite')"
        ></i>
      </SidebarItem>

      <div v-if="!isCollapsed && hasChildren(item) && isGroupOpen(item)" class="sidebar-submenu">
        <SidebarItem
          v-for="child in item.children"
          :key="child.key"
          :icon="child.icon"
          :label="itemLabel(child)"
          :active="route.path === child.to"
          class="sidebar-subitem"
          @click="handleLeafClick(child)"
        >
          <span class="menu-item-label">
            {{ itemLabel(child) }}
          </span>
          <i
            class="pi favorite-star"
            :class="nav.isFavoriteOfDomain(nav.currentDomain, child.to) ? 'pi-star-fill' : 'pi-star'"
            @click.stop="handleToggleFavorite(child)"
            v-tooltip.right="nav.isFavoriteOfDomain(nav.currentDomain, child.to) ? t('nav.remove_favorite') : t('nav.set_favorite')"
          ></i>
        </SidebarItem>
      </div>
    </template>
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

.group-chevron {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
}

.sidebar-submenu {
  display: flex;
  flex-direction: column;
  gap: var(--app-sidebar-item-gap);
  padding-left: 1.25rem;
}

.sidebar-subitem {
  font-size: var(--app-font-size-sm);
}

.back-home {
  color: var(--p-text-muted-color);
}

.back-home:hover {
  color: var(--p-text-color);
}
</style>

<script setup>
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { computed } from 'vue'
import { useAuthStore } from '../../stores/auth'
import { useUiStore } from '../../stores/ui'
import { SIDEBAR_ITEMS } from '../navigation'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

const activePath = computed(() => {
  const path = route.path
  if (path === '/') return '/'
  return '/' + path.split('/')[1]
})

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <aside class="app-sidebar" :class="{ collapsed: ui.effectiveSidebarCollapsed }">
    <div class="sidebar-header">
      <span class="sidebar-logo">Z</span>
      <span v-if="!ui.effectiveSidebarCollapsed" class="sidebar-title">ZeroERP</span>
    </div>

    <nav class="sidebar-nav">
      <router-link
        v-for="item in SIDEBAR_ITEMS"
        :key="item.key"
        :to="item.to"
        class="sidebar-item"
        :class="{ active: activePath === item.to }"
        v-tooltip.right="ui.effectiveSidebarCollapsed ? t(`nav.${item.key}`) : null"
      >
        <i :class="item.icon"></i>
        <span v-if="!ui.effectiveSidebarCollapsed">{{ t(`nav.${item.key}`) }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <div class="sidebar-toggle" @click="ui.toggleSidebar()"
        v-tooltip.right="ui.effectiveSidebarCollapsed ? t('nav.collapse') : null"
      >
        <i :class="ui.effectiveSidebarCollapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'"></i>
        <span v-if="!ui.effectiveSidebarCollapsed">{{ t('nav.collapse') }}</span>
      </div>

      <div
        class="sidebar-user"
        @click="handleLogout"
        v-tooltip.right="ui.effectiveSidebarCollapsed ? t('auth.logout') : null"
      >
        <i class="pi pi-sign-out"></i>
        <span v-if="!ui.effectiveSidebarCollapsed">{{ t('auth.logout') }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  width: var(--app-sidebar-width);
  min-width: var(--app-sidebar-width);
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  background: var(--app-sidebar-bg);
  border-right: 1px solid var(--app-sidebar-border);
  overflow: hidden;
  transition: width var(--app-transition-normal), min-width var(--app-transition-normal);
}

.app-sidebar.collapsed {
  width: var(--app-sidebar-width-collapsed);
  min-width: var(--app-sidebar-width-collapsed);
}

.sidebar-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--app-sidebar-border);
}

.collapsed .sidebar-header {
  justify-content: center;
  padding: 1rem 0.5rem;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  justify-content: center;
  width: var(--app-logo-size);
  height: var(--app-logo-size);
  min-width: var(--app-logo-size);
  border-radius: var(--app-logo-radius);
  background: var(--app-logo-bg);
  color: var(--app-logo-color);
  font-weight: 700;
  font-size: var(--app-font-size-lg);
}

.sidebar-title {
  font-weight: 600;
  font-size: var(--app-font-size-lg);
  color: var(--p-text-color);
  white-space: nowrap;
}

.sidebar-nav {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--app-sidebar-item-gap);
  padding: 0.5rem;
  overflow-y: auto;
  min-height: 0;
}

.sidebar-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  border-radius: var(--app-sidebar-item-radius);
  color: var(--app-sidebar-item-color);
  text-decoration: none;
  font-size: var(--app-font-size-base);
  white-space: nowrap;
  transition: background var(--app-transition-fast), color var(--app-transition-fast);
}

.collapsed .sidebar-item {
  justify-content: center;
  padding: 0.6rem;
}

.sidebar-item:hover {
  background: var(--app-sidebar-item-hover-bg);
  color: var(--app-sidebar-item-hover-color);
}

.sidebar-item.active {
  background: var(--app-sidebar-item-active-bg);
  color: var(--app-sidebar-item-active-color);
}

.sidebar-item i {
  font-size: 1rem;
  width: 1.25rem;
  text-align: center;
}

.sidebar-footer {
  border-top: 1px solid var(--app-sidebar-border);
  padding: 0.5rem;
}

.sidebar-user,
.sidebar-toggle {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0.75rem;
  border-radius: var(--app-sidebar-item-radius);
  color: var(--app-sidebar-item-color);
  font-size: var(--app-font-size-sm);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--app-transition-fast);
}

.collapsed .sidebar-user,
.collapsed .sidebar-toggle {
  justify-content: center;
  padding: 0.5rem;
}

.sidebar-user:hover,
.sidebar-toggle:hover {
  background: var(--app-sidebar-item-hover-bg);
}

.sidebar-toggle {
  margin-top: 2px;
}
</style>

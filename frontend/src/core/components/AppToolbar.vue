<script setup>
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { computed } from 'vue'
import Button from 'primevue/button'

const { t } = useI18n()
const route = useRoute()

const tabs = computed(() => route.meta.tabs || [])
const actions = computed(() => route.meta.actions || [])
const hasToolbar = computed(() => tabs.value.length > 0 || actions.value.length > 0)
</script>

<template>
  <div v-if="hasToolbar" class="app-toolbar">
    <nav class="toolbar-tabs">
      <router-link
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.to"
        class="toolbar-tab"
        :class="{ active: $route.path === tab.to }"
      >
        {{ t(`nav.${tab.key}`, tab.label || tab.key) }}
      </router-link>
    </nav>

    <div class="toolbar-actions">
      <Button
        v-for="action in actions"
        :key="action.key"
        :label="t(`actions.${action.key}`, action.label || action.key)"
        :icon="action.icon"
        :severity="action.severity || 'primary'"
        size="small"
        @click="$emit(action.event || action.key)"
      />
    </div>
  </div>
</template>

<style scoped>
.app-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--app-toolbar-height);
  min-height: var(--app-toolbar-height);
  padding: 0 var(--app-content-padding);
  background: var(--app-toolbar-bg);
  border-bottom: 1px solid var(--app-toolbar-border);
}

.toolbar-tabs {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.toolbar-tab {
  display: flex;
  align-items: center;
  padding: 0.4rem 0.75rem;
  border-radius: var(--app-sidebar-item-radius);
  font-size: var(--app-font-size-sm);
  font-weight: 500;
  color: var(--app-topbar-breadcrumb-color);
  text-decoration: none;
  transition: background var(--app-transition-fast), color var(--app-transition-fast);
}

.toolbar-tab:hover {
  background: var(--app-toolbar-tab-hover-bg);
  color: var(--app-topbar-breadcrumb-active-color);
}

.toolbar-tab.active {
  background: var(--app-toolbar-tab-active-bg);
  color: var(--app-toolbar-tab-active-color);
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Tablet portrait */
@media (max-width: 768px) {
  .toolbar-tab {
    padding: 0.4rem 0.5rem;
    font-size: var(--app-font-size-sm);
  }
}
</style>

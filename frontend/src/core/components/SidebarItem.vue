<script setup>
// Scopo: voce sidebar riutilizzabile — icona + label + tooltip quando collapsed.
// Usato da SidebarHome e SidebarDomain per evitare duplicazione template.
// Possiede i propri stili (non dipende da :deep nel parent).
// Inietta lo stato collapsed dal parent (AppSidebar): nel drawer e' sempre espanso.
import { inject, ref } from 'vue'

const isCollapsed = inject('sidebarCollapsed', ref(false))

defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  active: { type: Boolean, default: false }
})

defineEmits(['click'])
</script>

<template>
  <div
    class="sidebar-item"
    :class="{ active, collapsed: isCollapsed }"
    @click="$emit('click')"
    v-tooltip.right="isCollapsed ? label : null"
  >
    <i :class="icon"></i>
    <span v-if="!isCollapsed">
      <slot>{{ label }}</slot>
    </span>
  </div>
</template>

<style scoped>
.sidebar-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.6rem 0.75rem;
  border-radius: var(--app-sidebar-item-radius);
  color: var(--app-sidebar-item-color);
  font-size: var(--app-font-size-base);
  white-space: nowrap;
  cursor: pointer;
  transition: background var(--app-transition-fast), color var(--app-transition-fast);
}

.sidebar-item.collapsed {
  justify-content: center;
  padding: 0.5rem 0.35rem;
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
  color: var(--app-icon-color);
}

/* In hover e active l'icona segue il colore del parent */
.sidebar-item:hover i,
.sidebar-item.active i {
  color: inherit;
}
</style>

<script setup>
// Scopo: voce sidebar riutilizzabile — icona + label + tooltip quando collapsed.
// Usato da SidebarHome e SidebarDomain per evitare duplicazione template.
// Possiede i propri stili (non dipende da :deep nel parent).
// Inietta lo stato collapsed dal parent (AppSidebar): nel drawer e' sempre espanso.
import { inject, ref } from 'vue'
import { MANAGE_ICONS } from '../constants'

const isCollapsed = inject('sidebarCollapsed', ref(false))

defineProps({
  icon: { type: String, required: true },
  label: { type: String, required: true },
  active: { type: Boolean, default: false },
  // La voce e' un GRUPPO (ha delle voci dentro). A sidebar chiusa resta
  // l'icona sola, e senza un segno nessuno penserebbe di cliccarla per
  // trovarne altre (rilievo in-app di Tid, 2026-10-06): il segno accanto e'
  // lo stesso del gruppo chiuso a sidebar aperta (`MANAGE_ICONS.SOTTOMENU`).
  gruppo: { type: Boolean, default: false }
})

defineEmits(['click'])
</script>

<template>
  <div
    class="sidebar-item"
    :class="{ active, collapsed: isCollapsed }"
    @click="$emit('click', $event)"
    v-tooltip.right="isCollapsed ? label : null"
  >
    <i :class="icon"></i>
    <i v-if="isCollapsed && gruppo" class="sidebar-item-gruppo app-sottomenu-icon" :class="MANAGE_ICONS.SOTTOMENU"></i>
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
  position: relative;
  justify-content: center;
  padding: 0.5rem 0.35rem;
}

/* Il segno del gruppo a sidebar chiusa: piccolo, sul bordo destro, fuori
   dal flusso — l'icona resta centrata come quella delle voci semplici. Il
   colore e' quello dell'icona (regole qui sotto). */
.sidebar-item .sidebar-item-gruppo {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: auto;
  font-size: 0.6rem;
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

/* ⭐ Il segno di sottomenu che il chiamante mette nello slot (SidebarDomain,
   gruppo a sidebar aperta) ha lo stesso colore dell'icona: una regola sola. */
.sidebar-item i,
.sidebar-item :slotted(.app-sottomenu-icon) {
  color: var(--app-icon-color);
}

/* In hover e active l'icona segue il colore del parent */
.sidebar-item:hover i,
.sidebar-item.active i,
.sidebar-item:hover :slotted(.app-sottomenu-icon),
.sidebar-item.active :slotted(.app-sottomenu-icon) {
  color: inherit;
}
</style>

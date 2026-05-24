<script setup>
// Scopo: barra azioni pagina/lista responsive e riusabile.
// Desktop: azione primaria + utility inline, azioni secondarie in menu.
// Mobile/tablet: azione primaria visibile, tutte le altre nel kebab.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import { MANAGE_ICONS } from '../constants'
import { menuItemClass } from '../utils/rowActions'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'

const props = defineProps({
  actions: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  menuTooltip: { type: String, default: '' },
})

const { t } = useI18n()
const auth = useAuthStore()
const isReadonly = useInjectReadonly()
const desktopMenuRef = ref(null)
const compactMenuRef = ref(null)

function isActionVisible(action) {
  if (action.visible === false) return false
  if (action.hideWhenReadonly && isReadonly.value) return false
  if (action.action && !auth.isActionAllowed(action.action)) return false
  return true
}

const visibleActions = computed(() => props.actions.filter(isActionVisible))
const primaryActions = computed(() => visibleActions.value.filter(a => a.kind === 'primary'))
const nonPrimaryActions = computed(() => visibleActions.value.filter(a => a.kind !== 'primary'))
const desktopInlineActions = computed(() =>
  nonPrimaryActions.value.filter(a => a.kind !== 'secondary' && a.inline !== false),
)
const desktopMenuActions = computed(() =>
  nonPrimaryActions.value.filter(a => a.kind === 'secondary' || a.inline === false),
)

function isActionDisabled(action) {
  return props.disabled || action.disabled === true
}

function buttonTooltip(action) {
  return action.tooltip || action.label
}

function buttonClass(action) {
  if (action.class) return action.class
  if (action.kind === 'primary') return 'app-page-action'
  if (action.severity === 'danger') return 'app-delete-btn'
  if (action.severity === 'primary') return 'app-action-btn'
  if (action.severity === 'info') return 'app-manage-btn'
  return 'app-reload-btn'
}

function buttonSeverity(action) {
  if (['warn', 'info', 'secondary'].includes(action.severity)) return action.severity
  return undefined
}

function runAction(action, event) {
  event?.stopPropagation()
  if (isActionDisabled(action)) return
  action.command?.()
}

// Scopo: mappa le azioni nel formato PrimeVue Menu.
// La classe della voce e' parallela al colore inline del bottone desktop:
// default = action (verde, come app-reload-btn) — utility/secondarie nel kebab
// mantengono lo stesso colore che avrebbero avute inline.
function menuItems(actions) {
  return actions.map(a => ({
    label: a.label,
    icon: a.icon,
    disabled: isActionDisabled(a),
    class: menuItemClass(a.severity, 'app-menu-item-action'),
    command: () => {
      if (!isActionDisabled(a)) a.command?.()
    },
  }))
}

const desktopMenuItems = computed(() => menuItems(desktopMenuActions.value))
const compactMenuItems = computed(() => menuItems(nonPrimaryActions.value))
const menuTooltipText = computed(() => props.menuTooltip || t('common.altre_azioni'))

function toggleDesktopMenu(event) {
  event.stopPropagation()
  desktopMenuRef.value?.toggle(event)
}

function toggleCompactMenu(event) {
  event.stopPropagation()
  compactMenuRef.value?.toggle(event)
}
</script>

<template>
  <div class="app-page-actions">
    <slot name="prefix" />

    <span class="app-page-actions-desktop">
      <Button
        v-for="a in desktopInlineActions"
        :key="a.key"
        :icon="a.icon"
        :label="a.showLabel ? a.label : undefined"
        text
        :severity="buttonSeverity(a)"
        :class="buttonClass(a)"
        :disabled="isActionDisabled(a)"
        v-tooltip.bottom="buttonTooltip(a)"
        @click="runAction(a, $event)"
      />
      <Button
        v-if="desktopMenuActions.length"
        :icon="MANAGE_ICONS.KEBAB"
        text
        rounded
        class="app-manage-btn"
        :disabled="disabled"
        v-tooltip.bottom="menuTooltipText"
        aria-haspopup="true"
        @click="toggleDesktopMenu"
      />
      <Menu ref="desktopMenuRef" :model="desktopMenuItems" popup />
    </span>

    <slot name="suffix" />

    <Button
      v-for="a in primaryActions"
      :key="a.key"
      :icon="a.icon"
      :label="a.label"
      :severity="a.severity"
      :class="buttonClass(a)"
      :disabled="isActionDisabled(a)"
      v-tooltip.bottom="buttonTooltip(a)"
      @click="runAction(a, $event)"
    />

    <span class="app-page-actions-compact">
      <Button
        v-if="nonPrimaryActions.length"
        :icon="MANAGE_ICONS.KEBAB"
        text
        rounded
        class="app-manage-btn"
        :disabled="disabled"
        v-tooltip.bottom="menuTooltipText"
        aria-haspopup="true"
        @click="toggleCompactMenu"
      />
      <Menu ref="compactMenuRef" :model="compactMenuItems" popup />
    </span>
  </div>
</template>

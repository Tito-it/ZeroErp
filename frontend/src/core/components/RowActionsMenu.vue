<script setup>
// Scopo: menu azioni di riga responsive per liste.
// - Desktop (hover + viewport >=1024px): pulsanti inline icon-only con tooltip.
// - Tablet/mobile/touch: kebab `⋮` con menu popup (label sempre visibili).
// Lo switch e' CSS-first (vedi .app-row-actions-inline / .app-row-actions-compact
// in main.css): il componente renderizza entrambe le varianti, il breakpoint
// ne mostra una sola. Resize e touch detection gestiti dal browser.
//
// Convenzioni centralizzate (NON hardcodare qui):
//   - icona kebab:          MANAGE_ICONS.KEBAB   (src/core/constants.js)
//   - stile bottone std:    .app-manage-btn      (main.css)
//   - stile bottone danger: .app-delete-btn      (main.css)
//   - larghezza colonna:    .app-col-actions     (main.css, responsive)
//   - voce menu danger:     .app-menu-item-danger (main.css)
//
// Uso tipico nelle liste:
//   <Column :header="t('dominio.col_azioni')" class="app-col-actions" :exportable="false">
//     <template #body="{ data }">
//       <RowActionsMenu :actions="buildRowActions(data)" />
//     </template>
//   </Column>
//
// Formato azione:
//   { key, label, icon, severity?, visible?: bool, disabled?: bool, command: () => void }
//
// Severity supportate (controllano colore inline + colore voce menu):
//   undefined     -> blu    (app-manage-btn)  — default
//   'primary'     -> verde  (app-action-btn)  — azione positiva / state transition
//   'warn'        -> arancio (PrimeVue severity=warn) — cautela / cambio stato
//   'danger'      -> rosso  (app-delete-btn + app-menu-item-danger nel popup)
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Menu from 'primevue/menu'
import Button from 'primevue/button'
import { MANAGE_ICONS } from '../constants'

const props = defineProps({
  actions: { type: Array, required: true },
  tooltip: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const { t } = useI18n()
const menuRef = ref(null)

// Scopo: azioni filtrate da usare in entrambe le varianti.
const visibleActions = computed(() =>
  props.actions.filter(a => a.visible !== false),
)

// Scopo: mappa per il formato PrimeVue Menu (variante compact).
const menuItems = computed(() =>
  visibleActions.value.map(a => ({
    label: a.label,
    icon: a.icon,
    disabled: a.disabled === true,
    class: a.severity === 'danger' ? 'app-menu-item-danger' : undefined,
    command: () => a.command?.(),
  })),
)

const buttonTooltip = computed(() => props.tooltip || t('common.altre_azioni'))
const isEmpty = computed(() => visibleActions.value.length === 0)

// Scopo: classe colore bottone inline in base a severity.
// 'warn' non ha classe custom: usa la severity nativa PrimeVue.
function inlineButtonClass(action) {
  switch (action.severity) {
    case 'danger': return 'app-delete-btn'
    case 'primary': return 'app-action-btn'
    case 'warn': return ''
    default: return 'app-manage-btn'
  }
}

// Scopo: severity nativa PrimeVue (solo per 'warn', per riusare il colore orange).
function inlineButtonSeverity(action) {
  return action.severity === 'warn' ? 'warn' : undefined
}

function runAction(action, event) {
  event.stopPropagation()
  if (action.disabled === true) return
  action.command?.()
}

function toggle(event) {
  event.stopPropagation()
  menuRef.value?.toggle(event)
}
</script>

<template>
  <!-- Desktop: bottoni inline icon-only con tooltip. -->
  <span class="app-row-actions-inline">
    <Button
      v-for="a in visibleActions"
      :key="a.key"
      :icon="a.icon"
      text
      rounded
      size="small"
      :severity="inlineButtonSeverity(a)"
      :class="inlineButtonClass(a)"
      :disabled="disabled || a.disabled === true"
      v-tooltip.top="a.label"
      @click="runAction(a, $event)"
    />
  </span>

  <!-- Tablet / touch: kebab menu. -->
  <span class="app-row-actions-compact">
    <Button
      :icon="MANAGE_ICONS.KEBAB"
      text
      rounded
      size="small"
      class="app-manage-btn"
      :disabled="disabled || isEmpty"
      v-tooltip.top="buttonTooltip"
      aria-haspopup="true"
      @click="toggle"
    />
    <Menu ref="menuRef" :model="menuItems" popup />
  </span>
</template>

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
//       <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
//     </template>
//   </Column>
//
// Formato azione:
//   { key, label, icon, severity?, visible?: bool, disabled?: bool, tooltip?: string, allowWhenInactive?: bool, command: () => void }
// Quando `tooltip` e' valorizzato sostituisce `label` come tooltip del bottone
// inline (utile per spiegare il motivo di un disabled, es. capability di riga).
// Se `row` ha `attivo=false` o `is_active=false`, le azioni sono disabilitate
// salvo `allowWhenInactive: true`.
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
import { menuItemClass } from '../utils/rowActions'

const props = defineProps({
  actions: { type: Array, required: true },
  row: { type: Object, default: null },
  tooltip: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  disableWhenInactive: { type: Boolean, default: true },
})

const { t } = useI18n()
const menuRef = ref(null)

// Scopo: azioni filtrate da usare in entrambe le varianti.
const visibleActions = computed(() =>
  props.actions.filter(a => a.visible !== false),
)

// Scopo: riconosce lo stato inattivo standard delle righe lista.
const isInactiveRow = computed(() => (
  props.disableWhenInactive
  && props.row != null
  && (props.row.attivo === false || props.row.is_active === false)
))

// Scopo: disabilita azioni operative su righe inattive, salvo escape esplicito.
function isActionDisabled(action) {
  return props.disabled
    || action.disabled === true
    || (isInactiveRow.value && action.allowWhenInactive !== true)
}

function actionTooltip(action) {
  if (isInactiveRow.value && action.allowWhenInactive !== true) {
    return t('common.azione_non_disponibile_record_inattivo')
  }
  return action.tooltip || action.label
}

// Scopo: mappa per il formato PrimeVue Menu (variante compact).
// La classe della voce e' parallela al colore inline del bottone desktop:
// default = manage (blu, come app-manage-btn) — coerente con inlineButtonClass.
const menuItems = computed(() =>
  visibleActions.value.map(a => ({
    label: a.label,
    icon: a.icon,
    disabled: isActionDisabled(a),
    class: menuItemClass(a.severity, 'app-menu-item-manage'),
    command: () => {
      if (!isActionDisabled(a)) a.command?.()
    },
  })),
)

const isEmpty = computed(() => visibleActions.value.length === 0)
const allActionsDisabled = computed(() =>
  !isEmpty.value && visibleActions.value.every(a => isActionDisabled(a)),
)
const buttonTooltip = computed(() => {
  if (isInactiveRow.value && allActionsDisabled.value) {
    return t('common.azione_non_disponibile_record_inattivo')
  }
  return props.tooltip || t('common.altre_azioni')
})

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
  if (isActionDisabled(action)) return
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
      :disabled="isActionDisabled(a)"
      v-tooltip.top="actionTooltip(a)"
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

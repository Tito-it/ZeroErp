<script setup>
// Scopo: barra azioni pagina/lista responsive e riusabile.
// Desktop: azione primaria + utility inline, azioni secondarie in menu.
// Mobile/tablet: azione primaria visibile, tutte le altre nel kebab.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import ActionBadge from './ActionBadge.vue'
import { MANAGE_ICONS } from '../constants'
import { useActionBar } from '../composables/useActionBar'
import { conTastoDiAzione, useScorciatoie } from '../composables/useScorciatoie'

const props = defineProps({
  actions: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  menuTooltip: { type: String, default: '' },
})

// Motore condiviso (B9): filtro visibilita'/disabled/tooltip/dispatch + voci Menu.
const {
  visibleActions, primaryActions, isActionDisabled, buttonTooltip,
  runAction, menuItems, menuTooltipText,
  desktopMenuRef, compactMenuRef, toggleDesktopMenu, toggleCompactMenu, haBadgeIn,
} = useActionBar(() => props.actions, {
  disabled: () => props.disabled,
  menuTooltip: () => props.menuTooltip,
  defaultMenuItemClass: 'app-menu-item-action',
})

// ⭐ I tasti funzione (`useScorciatoie`, 2026-10-04): la barra si iscrive
//    con le sue azioni visibili e il suo stesso motore (spento/esecuzione), e
//    il tooltip DICE il tasto («Ricarica lista (F5)»). Un tooltip su piu'
//    righe porta un motivo, non un nome: li' il tasto non si aggiunge.
const { t, te } = useI18n()
const radice = ref(null)
useScorciatoie({
  elemento: () => radice.value,
  azioni: () => visibleActions.value,
  spenta: isActionDisabled,
  esegui: (a) => runAction(a),
})
function tooltipConTasto(a) {
  const base = buttonTooltip(a)
  return typeof base === 'string' ? conTastoDiAzione(t, te, base, a.key) : base
}

// Partizionamento per kind specifico della barra pagina.
const nonPrimaryActions = computed(() => visibleActions.value.filter(a => a.kind !== 'primary'))
const desktopInlineActions = computed(() =>
  nonPrimaryActions.value.filter(a => a.kind !== 'secondary' && a.inline !== false),
)
const desktopMenuActions = computed(() =>
  nonPrimaryActions.value.filter(a => a.kind === 'secondary' || a.inline === false),
)

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

const desktopMenuItems = computed(() => menuItems(desktopMenuActions.value))
const compactMenuItems = computed(() => menuItems(nonPrimaryActions.value))

// ⭐ Il numero dell'azione (`badge`, 2026-10-04): pallino sull'icona
//    (`ActionBadge`), «azione (n)» nella voce di menu, punto sul kebab che lo
//    contiene. «Personalizza colonne» con le colonne nuove: prima il numero
//    stava nell'etichetta di un pulsante a sola icona, e non si vedeva.
const desktopMenuHasBadge = computed(() => haBadgeIn(desktopMenuActions.value))
const compactHasBadge = computed(() => haBadgeIn(nonPrimaryActions.value))
</script>

<template>
  <div ref="radice" class="app-page-actions">
    <slot name="prefix" />

    <span class="app-page-actions-desktop">
      <!-- ⛔ Il tooltip sta sull'INVOLUCRO, non sul Button: un `<button disabled>`
           non emette eventi del mouse, quindi appeso al Button non comparirebbe
           mai — e a pulsante spento e' esattamente quando serve, perche' porta
           il MOTIVO (`enabled:false` + `reason` dal DB via `useDrawerActions`).
           Vedi `.app-action-tooltip-wrap` in main.css. -->
      <span
        v-for="a in desktopInlineActions"
        :key="a.key"
        class="app-action-tooltip-wrap"
        v-tooltip.bottom="tooltipConTasto(a)"
      >
        <Button
          :icon="a.icon"
          :label="a.showLabel ? a.label : undefined"
          text
          :severity="buttonSeverity(a)"
          :class="buttonClass(a)"
          :disabled="isActionDisabled(a)"
          @click="runAction(a, $event)"
        />
        <ActionBadge :valore="a.badge" />
      </span>
      <span v-if="desktopMenuActions.length" class="app-action-tooltip-wrap">
        <Button
          :icon="MANAGE_ICONS.KEBAB"
          text
          rounded
          class="app-manage-btn"
          :disabled="disabled"
          v-tooltip.bottom="menuTooltipText"
          aria-haspopup="true"
          @click="toggleDesktopMenu"
        />
        <ActionBadge v-if="desktopMenuHasBadge" punto :valore="1" />
      </span>
      <Menu ref="desktopMenuRef" :model="desktopMenuItems" popup />
    </span>

    <slot name="suffix" />

    <span
      v-for="a in primaryActions"
      :key="a.key"
      class="app-action-tooltip-wrap"
      v-tooltip.bottom="tooltipConTasto(a)"
    >
      <Button
        :icon="a.icon"
        :label="a.label"
        :severity="a.severity"
        :class="buttonClass(a)"
        :disabled="isActionDisabled(a)"
        @click="runAction(a, $event)"
      />
    </span>

    <span class="app-page-actions-compact">
      <span v-if="nonPrimaryActions.length" class="app-action-tooltip-wrap">
        <Button
          :icon="MANAGE_ICONS.KEBAB"
          text
          rounded
          class="app-manage-btn"
          :disabled="disabled"
          v-tooltip.bottom="menuTooltipText"
          aria-haspopup="true"
          @click="toggleCompactMenu"
        />
        <ActionBadge v-if="compactHasBadge" punto :valore="1" />
      </span>
      <Menu ref="compactMenuRef" :model="compactMenuItems" popup />
    </span>
  </div>
</template>

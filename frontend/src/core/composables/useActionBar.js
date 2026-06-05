// Scopo: motore condiviso delle barre azioni (B9 2026-06-05, regola del 2).
//        `PageActionsBar` e `DrawerActionsBar` sono mirror template ma sotto
//        duplicavano riga-per-riga ~8 helper: filtro visibilita'
//        (visible/hideWhenReadonly/permesso), disabled, tooltip, dispatch,
//        mappatura voci Menu PrimeVue, toggle dei due popup. Qui vivono una
//        volta sola; le due barre tengono solo i computed di partizionamento
//        per `kind` (legittimamente diversi) + `buttonClass`/`buttonSeverity`/
//        `buttonOutlined` + il template.
//
// Divergenze parametrizzate:
//   - `defaultMenuItemClass`: colore default voce kebab (`app-menu-item-action`
//     per Page, `app-menu-item-manage` per Drawer);
//   - `menuLabel`: etichetta voce kebab (default `a => a.label`; Drawer passa
//     la variante col counter "(N)").
//
// Ortogonale a `useDrawerActions` (che COSTRUISCE le azioni `kind:'state'` da
// `availableActions` BE; questo le FILTRA/dispatcha).
//
// Uso (nel componente barra):
//   const {
//     visibleActions, primaryActions, isActionDisabled, buttonTooltip,
//     runAction, menuItems, menuTooltipText,
//     desktopMenuRef, compactMenuRef, toggleDesktopMenu, toggleCompactMenu,
//   } = useActionBar(() => props.actions, {
//     disabled: () => props.disabled,
//     menuTooltip: () => props.menuTooltip,
//     defaultMenuItemClass: 'app-menu-item-action',
//   })
//   // il componente deriva i propri desktopInline/desktopMenu/... da visibleActions

import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { menuItemClass } from '../utils/rowActions'
import { useInjectReadonly } from './useReadonlyMode'
import { useAuthStore } from '../../stores/auth'

export function useActionBar(getActions, options = {}) {
  const {
    disabled = () => false,
    menuTooltip = () => '',
    defaultMenuItemClass = 'app-menu-item-action',
    menuLabel = (a) => a.label,
  } = options

  const { t } = useI18n()
  const auth = useAuthStore()
  const isReadonly = useInjectReadonly()
  const desktopMenuRef = ref(null)
  const compactMenuRef = ref(null)

  // Filtra le azioni in base a visible/hideWhenReadonly/permessi.
  function isActionVisible(action) {
    if (action.visible === false) return false
    if (action.hideWhenReadonly && isReadonly.value) return false
    if (action.action && !auth.isActionAllowed(action.action)) return false
    return true
  }

  const visibleActions = computed(() => getActions().filter(isActionVisible))
  const primaryActions = computed(() => visibleActions.value.filter((a) => a.kind === 'primary'))

  function isActionDisabled(action) {
    return disabled() || action.disabled === true
  }

  function buttonTooltip(action) {
    return action.tooltip || action.label
  }

  function runAction(action, event) {
    event?.stopPropagation()
    if (isActionDisabled(action)) return
    action.command?.()
  }

  // Mappa una lista di azioni nel formato PrimeVue Menu. La classe della voce
  // segue il colore inline (default parametrico); `menuLabel` permette il
  // suffisso counter (Drawer).
  function menuItems(list) {
    return list.map((a) => ({
      label: menuLabel(a),
      icon: a.icon,
      disabled: isActionDisabled(a),
      class: menuItemClass(a.severity, defaultMenuItemClass),
      command: () => {
        if (!isActionDisabled(a)) a.command?.()
      },
    }))
  }

  const menuTooltipText = computed(() => menuTooltip() || t('common.altre_azioni'))

  function toggleDesktopMenu(event) {
    event.stopPropagation()
    desktopMenuRef.value?.toggle(event)
  }

  function toggleCompactMenu(event) {
    event.stopPropagation()
    compactMenuRef.value?.toggle(event)
  }

  return {
    isActionVisible,
    visibleActions,
    primaryActions,
    isActionDisabled,
    buttonTooltip,
    runAction,
    menuItems,
    menuTooltipText,
    desktopMenuRef,
    compactMenuRef,
    toggleDesktopMenu,
    toggleCompactMenu,
  }
}

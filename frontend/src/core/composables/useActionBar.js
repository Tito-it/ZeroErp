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
//   (L'etichetta di menu col numero, «Gestisci righe (5)», era una
//   divergenza della sola Drawer: dal 2026-10-04 e' di tutte e due le barre,
//   `etichettaConBadge`, perche' anche la lista ha azioni col numero.)
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

// Scopo: l'azione porta un numero (`badge`)? Vuoto = null, undefined, '' o
//        ZERO: il pallino dice «qui c'e' qualcosa», e «Gestisci righe» con 0
//        righe non informa (Tid 2026-10-25). Regola unica del pallino
//        (`ActionBadge`), del punto sul kebab e dell'etichetta di menu: chi
//        passa il conteggio grezzo non deve tradurre lo zero in `null`.
export function haBadge(action) {
  const badge = action?.badge
  return badge != null && badge !== '' && badge !== 0 && badge !== '0'
}

// Scopo: l'etichetta di un'azione in un MENU, col suo numero: «Gestisci
//        righe (5)». Nel menu il pallino non c'e', il numero va nel testo.
export function etichettaConBadge(action) {
  return haBadge(action) ? `${action.label} (${action.badge})` : action.label
}

export function useActionBar(getActions, options = {}) {
  const {
    disabled = () => false,
    menuTooltip = () => '',
    defaultMenuItemClass = 'app-menu-item-action',
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
    const text = action.tooltip || action.label
    // Tooltip multi-riga (es. i motivi ostativi multipli della capability
    // emetti-DDT, brief guard-righe Rev 2): la directive rende il testo in un
    // textNode, quindi senza `white-space: pre-line` i '\n' collassano in
    // spazi. Si passa la forma oggetto con `class` — chiave SUPPORTATA dalla
    // directive PrimeVue 4 (value/disabled/escape/class/fitContent/id/
    // showDelay/hideDelay/autoHide); lo stile vive in main.css come tutte le
    // classi app-*. NB: `pt` NON e' letto dalla directive (solo dai
    // componenti): passarlo qui sarebbe un no-op silenzioso.
    return text?.includes?.('\n')
      ? { value: text, class: 'app-tooltip-multiline' }
      : text
  }

  function runAction(action, event) {
    event?.stopPropagation()
    if (isActionDisabled(action)) return
    action.command?.()
  }

  // Mappa una lista di azioni nel formato PrimeVue Menu. La classe della voce
  // segue il colore inline (default parametrico); l'etichetta porta il numero
  // dell'azione (`etichettaConBadge`).
  function menuItems(list) {
    return list.map((a) => ({
      label: etichettaConBadge(a),
      icon: a.icon,
      disabled: isActionDisabled(a),
      class: menuItemClass(a.severity, defaultMenuItemClass),
      command: () => {
        if (!isActionDisabled(a)) a.command?.()
      },
    }))
  }

  // Scopo: qualche azione dell'elenco porta un numero? Il punto sul kebab
  //        compatto: dice «qui dentro c'e' un conteggio» senza sommarne di
  //        eterogenei (il numero esatto e' nella voce del menu).
  function haBadgeIn(list) {
    return list.some(haBadge)
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
    haBadgeIn,
  }
}

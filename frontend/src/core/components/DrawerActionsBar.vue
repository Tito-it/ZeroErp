<script setup>
// Scopo: barra azioni dei drawer entita' (sotto l'header), responsive e
//   riusabile. Mirror funzionale di PageActionsBar (azioni di pagina) per il
//   contesto drawer.
//
// Semantica kind (allineata a PageActionsBar + estensione 'manage'/'state'):
//   - 'primary'    -> inline sempre (desktop e mobile). Azione critica/terminale
//                     che l'operatore deve poter raggiungere in 1 click su
//                     ogni viewport (es. Annulla contratto DRAFT, Accetta
//                     preventivo).
//   - 'state'      -> inline desktop, dentro kebab compact. Transizioni di
//                     stato data-driven (`availableActions` da BE).
//   - 'manage'     -> inline desktop con badge counter opzionale, dentro
//                     kebab compact (label suffissata col counter).
//                     Apertura sub-drawer (gestisci righe/note/...).
//   - 'secondary'  -> dentro kebab desktop E compact. Utility/diagnostica
//                     che non e' parte del flusso principale.
//
// Switch responsive CSS-first via @media (hover: none), (max-width: 1024px)
// in main.css sulle classi .app-drawer-actions-desktop / -compact. Il
// componente renderizza entrambe le varianti, il CSS ne mostra una sola.
//
// `class="app-escape"` e' applicata automaticamente a tutti i bottoni del
// BB: il drawer in modalita' readonly (pattern protect AS/400) lascia i
// pulsanti di azione operabili — il filtro effettivo per readonly e' la
// proprieta' `hideWhenReadonly: true` sulle singole azioni.
//
// Convenzioni centralizzate (NON hardcodare qui):
//   - icona kebab:           MANAGE_ICONS.KEBAB   (src/core/constants.js)
//   - tooltip kebab default: common.altre_azioni  (it.json)
//   - stile bottone std:     .app-manage-btn      (main.css)
//   - voce menu danger:      .app-menu-item-danger (main.css)
//
// Uso tipico nel drawer:
//   const drawerActions = computed(() => [
//     ...mapAvailableActionsToDrawerActions({ availableActions, t, onAction }),
//     { key: 'manage-righe', kind: 'manage', label: t(...), icon: MANAGE_ICONS.RIGHE,
//       badge: righeCount.value, command: () => righeVisible = true },
//     { key: 'pdf', kind: 'secondary', label: t(...), icon: 'pi pi-file-pdf',
//       command: onScaricaPdf },
//   ])
//
//   <DrawerActionsBar :actions="drawerActions" />
//
// Formato azione (vedi anche useDrawerActions.js):
//   { key, kind, label, icon, severity?, outlined?, badge?, tooltip?, visible?,
//     disabled?, hideWhenReadonly?, action?: 'permesso.codename', command: () => void }
//
// severity: pass-through PrimeVue (`primary`/`success`/`warn`/`info`/`danger`/`secondary`).
// outlined: default true per kind:'manage', false altrove. Override esplicito ammesso
//   (es. kind:'state' severity:'danger' outlined:true per cessazione/annullamento).
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

// Scopo: filtra le azioni in base a visible/hideWhenReadonly/permessi.
function isActionVisible(action) {
  if (action.visible === false) return false
  if (action.hideWhenReadonly && isReadonly.value) return false
  if (action.action && !auth.isActionAllowed(action.action)) return false
  return true
}

const visibleActions = computed(() => props.actions.filter(isActionVisible))
const primaryActions = computed(() => visibleActions.value.filter(a => a.kind === 'primary'))
const inlineDesktopActions = computed(() =>
  visibleActions.value.filter(a => a.kind === 'state' || a.kind === 'manage'),
)
const desktopMenuActions = computed(() =>
  visibleActions.value.filter(a => a.kind === 'secondary'),
)
const compactMenuActions = computed(() =>
  visibleActions.value.filter(a => a.kind !== 'primary'),
)

function isActionDisabled(action) {
  return props.disabled || action.disabled === true
}

function buttonTooltip(action) {
  return action.tooltip || action.label
}

// Scopo: classe pulsante inline. Per kind:'manage' usa il pattern blu standard
//   (app-manage-btn) condiviso con le liste; per gli altri kind lascia la
//   colorazione a PrimeVue nativo via `severity`. `app-escape` sempre presente
//   per restare cliccabile in modalita' readonly.
function buttonClass(action) {
  const escape = 'app-escape'
  if (action.class) return `${action.class} ${escape}`
  if (action.kind === 'manage') return `app-manage-btn ${escape}`
  return escape
}

// Scopo: severity pass-through PrimeVue. Per kind:'manage' resta undefined
//   perche' il colore arriva dalla classe app-manage-btn.
function buttonSeverity(action) {
  if (action.kind === 'manage') return undefined
  return action.severity
}

// Scopo: outlined default per kind:'manage' (icon+label leggero, no shouty),
//   override esplicito ammesso per azioni di stato che lo richiedono
//   (es. severity:'danger' outlined:true per annullamento).
function buttonOutlined(action) {
  if (action.outlined != null) return action.outlined
  return action.kind === 'manage'
}

// Scopo: per le voci dentro Menu popup, se l'azione ha un badge counter
//   lo appendiamo alla label (es. "Gestisci righe (5)"). Pattern di lettura
//   coerente con le liste lookup multi-riga.
function menuLabel(action) {
  if (action.badge != null && action.badge !== '') {
    return `${action.label} (${action.badge})`
  }
  return action.label
}

// Scopo: voci PrimeVue Menu coerenti col colore inline. Default = manage (blu),
//   come kind:'manage' inline che usa app-manage-btn. Severity esplicite (danger,
//   primary, warn, ...) mappate via helper centralizzato.
function menuItems(list) {
  return list.map(a => ({
    label: menuLabel(a),
    icon: a.icon,
    disabled: isActionDisabled(a),
    class: menuItemClass(a.severity, 'app-menu-item-manage'),
    command: () => {
      if (!isActionDisabled(a)) a.command?.()
    },
  }))
}

const desktopMenuItems = computed(() => menuItems(desktopMenuActions.value))
const compactMenuItems = computed(() => menuItems(compactMenuActions.value))
const menuTooltipText = computed(() => props.menuTooltip || t('common.altre_azioni'))

// Scopo: segnala con un dot la presenza di counter manage nel kebab compact,
//   senza esporre il numero (sommare counter eterogenei sarebbe ambiguo).
//   Il numero esatto resta visibile come suffisso label nella voce menu.
const compactHasBadge = computed(() =>
  compactMenuActions.value.some(a => a.kind === 'manage' && a.badge != null && a.badge !== ''),
)

function runAction(action, event) {
  event?.stopPropagation()
  if (isActionDisabled(action)) return
  action.command?.()
}

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
  <div v-if="visibleActions.length" class="app-drawer-actions">
    <slot name="prefix" />

    <span class="app-drawer-actions-desktop">
      <span v-for="a in inlineDesktopActions" :key="a.key" class="app-drawer-action-wrap">
        <Button
          :icon="a.icon"
          :label="a.label"
          :outlined="buttonOutlined(a)"
          :severity="buttonSeverity(a)"
          :class="buttonClass(a)"
          :disabled="isActionDisabled(a)"
          v-tooltip.bottom="buttonTooltip(a)"
          @click="runAction(a, $event)"
        />
        <span
          v-if="a.kind === 'manage' && a.badge != null && a.badge !== ''"
          class="app-drawer-action-badge"
        >{{ a.badge }}</span>
      </span>
      <Button
        v-if="desktopMenuActions.length"
        :icon="MANAGE_ICONS.KEBAB"
        text
        rounded
        size="small"
        class="app-manage-btn app-escape"
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
      :outlined="buttonOutlined(a)"
      :severity="buttonSeverity(a)"
      :class="buttonClass(a)"
      :disabled="isActionDisabled(a)"
      v-tooltip.bottom="buttonTooltip(a)"
      @click="runAction(a, $event)"
    />

    <span class="app-drawer-actions-compact">
      <span class="app-drawer-action-wrap">
        <Button
          v-if="compactMenuActions.length"
          :icon="MANAGE_ICONS.KEBAB"
          text
          rounded
          size="small"
          class="app-manage-btn app-escape"
          :disabled="disabled"
          v-tooltip.bottom="menuTooltipText"
          aria-haspopup="true"
          @click="toggleCompactMenu"
        />
        <span v-if="compactHasBadge" class="app-drawer-action-badge app-drawer-action-badge-dot" />
      </span>
      <Menu ref="compactMenuRef" :model="compactMenuItems" popup />
    </span>
  </div>
</template>

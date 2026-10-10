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
// Switch responsive CSS-first via @media (hover: none), (max-width: 1023.98px)
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
// `infoKey` (2026-08-04, brief-db-vie-uscita-operatore §4 — regola R3): chiave
// i18n emessa dal DB (campo `stato_info_key` delle capability) che spiega
// all'operatore in che stato si trova il documento e cosa fare invece (es. DDT
// CONSEGNATO -> «per farla rientrare si registra un reso»). Il BB risolve la
// chiave con `labelOrCode` (fail-visible: chiave assente -> la chiave grezza,
// mai testo sparito) e la rende come nota discreta accanto alle azioni. Nessun
// testo viene dal DB: viaggiano solo indirizzi i18n.
//
// ⚠️ La nota NON e' piu' subordinata alla lista di azioni vuota (decisione §5
// del test in-app, Tid 2026-08-10, applicata da `20260810-04/-05/-06`): e'
// **informazione di stato** e compare anche accanto a un pulsante vivo — es.
// ordine EVASO col push ancora abilitato. Da qui il rinome del campo, che
// prima si chiamava `nessuna_azione_key`: quel nome descriveva il presupposto
// caduto, non il dato.
// ⚠️ Il campo e' SEMPRE presente nel blob, col valore a `null` quando non si
// applica: va guardato il VALORE, non la presenza della chiave.
// ⚠️ Asimmetria VOLUTA lato DB: la proprieta' nel `meta` dello stato si chiama
// ancora `nessuna_azione_key` — rinominarla e' una slice a se', perche'
// `scripts/check_i18n_keys.py` trova le chiavi seminate proprio per quel nome
// e cambiarlo senza toccare il guard lo renderebbe verde per cecita'.
//
// Uso tipico nel drawer:
//   const drawerActions = computed(() => [
//     ...mapAvailableActionsToDrawerActions({ availableActions, t, onAction }),
//     { key: 'manage-righe', kind: 'manage', label: t(...), icon: MANAGE_ICONS.RIGHE,
//       badge: righeCount.value, command: () => righeVisible = true },
//     { key: 'pdf', kind: 'secondary', label: t(...), icon: MANAGE_ICONS.PDF,
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
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Menu from 'primevue/menu'
import ActionBadge from './ActionBadge.vue'
import { MANAGE_ICONS, STATUS_ICONS } from '../constants'
import { useActionBar } from '../composables/useActionBar'
import { labelOrCode } from '../utils/i18nLabel'

const props = defineProps({
  actions: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  menuTooltip: { type: String, default: '' },
  // Chiave i18n della spiegazione «qui non c'e' niente da azionare» (vedi
  // testata). Null/assente = nessuna nota, comportamento invariato.
  infoKey: { type: String, default: '' },
})

const { t, te } = useI18n()

// Motore condiviso (B9): voci Menu default blu (manage); la voce di menu
// porta il numero dell'azione («Gestisci righe (5)», `etichettaConBadge`).
const {
  visibleActions, primaryActions, isActionDisabled, buttonTooltip,
  runAction, menuItems, menuTooltipText,
  desktopMenuRef, compactMenuRef, toggleDesktopMenu, toggleCompactMenu, haBadgeIn,
} = useActionBar(() => props.actions, {
  disabled: () => props.disabled,
  menuTooltip: () => props.menuTooltip,
  defaultMenuItemClass: 'app-menu-item-manage',
})

// Partizionamento per kind specifico della barra drawer.
const inlineDesktopActions = computed(() =>
  visibleActions.value.filter(a => a.kind === 'state' || a.kind === 'manage'),
)
const desktopMenuActions = computed(() =>
  visibleActions.value.filter(a => a.kind === 'secondary'),
)
const compactMenuActions = computed(() =>
  visibleActions.value.filter(a => a.kind !== 'primary'),
)

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

const desktopMenuItems = computed(() => menuItems(desktopMenuActions.value))
const compactMenuItems = computed(() => menuItems(compactMenuActions.value))

// Il punto sul kebab compatto: qualche azione manage nel menu ha un numero.
const compactHasBadge = computed(() =>
  haBadgeIn(compactMenuActions.value.filter(a => a.kind === 'manage')),
)

// Nota «nessuna azione»: risolta fail-visible (chiave sconosciuta -> la chiave
// stessa, cosi' il buco si vede a schermo invece di sparire). Vuota = niente
// nota, e la barra torna a comparire solo se ci sono azioni.
const infoText = computed(() =>
  (props.infoKey ? labelOrCode(t, te, props.infoKey, props.infoKey) : ''),
)
</script>

<template>
  <div v-if="visibleActions.length || infoText" class="app-drawer-actions">
    <slot name="prefix" />

    <span class="app-drawer-actions-desktop">
      <!-- ⛔ Il tooltip sta sull'INVOLUCRO, non sul Button: un `<button disabled>`
           non emette eventi del mouse, quindi appeso al Button non comparirebbe
           mai — e a pulsante spento e' quando serve, perche' porta il MOTIVO
           che il DB manda con `enabled:false` + `reason`.
           ⭐ Qui l'involucro c'era gia' (gli serve per il badge): il tooltip si
           e' solo spostato di un nodo. -->
      <span
        v-for="a in inlineDesktopActions"
        :key="a.key"
        class="app-action-tooltip-wrap"
        v-tooltip.bottom="buttonTooltip(a)"
      >
        <Button
          :icon="a.icon"
          :label="a.label"
          :outlined="buttonOutlined(a)"
          :severity="buttonSeverity(a)"
          :class="buttonClass(a)"
          :disabled="isActionDisabled(a)"
          @click="runAction(a, $event)"
        />
        <ActionBadge v-if="a.kind === 'manage'" :valore="a.badge" />
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

    <span
      v-for="a in primaryActions"
      :key="a.key"
      class="app-action-tooltip-wrap"
      v-tooltip.bottom="buttonTooltip(a)"
    >
      <Button
        :icon="a.icon"
        :label="a.label"
        :outlined="buttonOutlined(a)"
        :severity="buttonSeverity(a)"
        :class="buttonClass(a)"
        :disabled="isActionDisabled(a)"
        @click="runAction(a, $event)"
      />
    </span>

    <span class="app-drawer-actions-compact">
      <span class="app-action-tooltip-wrap">
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
        <ActionBadge v-if="compactHasBadge" punto :valore="1" />
      </span>
      <Menu ref="compactMenuRef" :model="compactMenuItems" popup />
    </span>

    <!-- Perche' qui non c'e' nulla da azionare (R3 del brief vie d'uscita).
         Nota discreta, non un banner: convive con le azioni manage/secondary
         che restano disponibili anche negli stati chiusi (note, PDF). -->
    <span v-if="infoText" class="app-drawer-actions-info">
      <i :class="STATUS_ICONS.INFO" aria-hidden="true" />
      <span>{{ infoText }}</span>
    </span>
  </div>
</template>

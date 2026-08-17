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
//   { key, label, icon, severity?, visible?: bool, disabled?: bool, tooltip?: string, allowWhenInactive?: bool, action?: string, command: () => void }
//
// ⚠️ `action` = codename del permesso di processo (`auth.isActionAllowed`):
// senza quel permesso la voce NON viene renderizzata, come gia' fanno
// `PageActionsBar` e `DrawerActionsBar` via `useActionBar`. Fino al 2026-08-17
// questo componente IGNORAVA il campo: chi lo passava — `useLottoAzioni`
// («Riporta in lavorazione», «Annulla», «Numera») e `CommessaGestioneDrawer` —
// credeva di aver messo un cancello che non esisteva, e un operatore senza
// permesso vedeva l'azione nel kebab (rilievo di Tid). Il difetto era peggiore
// dell'assenza del campo: sembrava presidiato. Il gate vero resta il BE — questo
// e' solo il non-proporre.
// Quando `tooltip` e' valorizzato sostituisce `label` come tooltip del bottone
// inline (utile per spiegare il motivo di un disabled, es. capability di riga).
// Se `row` ha `attivo=false` o `is_active=false`, le azioni sono disabilitate
// salvo `allowWhenInactive: true`.
//
// ⚠️ Il motivo di un'azione DISABILITATA non puo' vivere in un tooltip nella
// variante kebab: il kebab e' la variante touch, e su touch non esiste hover —
// l'azione appariva grigia senza che nulla dicesse perche' (rilievo 2026-08-15,
// review della slice emittibilita'). Nel popup il motivo si RENDE, come riga
// secondaria sotto la label, via il template `#item` del Menu. Compare solo
// dove serve: azione disabilitata + motivo diverso dalla label. Senza motivo la
// voce e' identica a prima, che e' cio' che tiene fermi gli altri consumer.
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
import { useAuthStore } from '../../stores/auth'

const props = defineProps({
  actions: { type: Array, required: true },
  row: { type: Object, default: null },
  tooltip: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  disableWhenInactive: { type: Boolean, default: true },
  // Forza la variante kebab anche su desktop (es. liste responsive con spazio
  // stretto: comprimere le azioni recupera larghezza prima di ritirare colonne).
  // Lo switch di default resta CSS-first (touch / <1024px); questo prop lo
  // sovrascrive via classi modificatrici (vedi .app-row-actions-*--* in main.css).
  forceCompact: { type: Boolean, default: false },
})

const { t } = useI18n()
const auth = useAuthStore()
const menuRef = ref(null)

// Scopo: azioni filtrate da usare in entrambe le varianti. Stesso predicato di
//        `useActionBar` (PageActionsBar/DrawerActionsBar): un solo meccanismo di
//        gate per tutte e tre le barre, altrimenti la stessa azione compare o
//        sparisce a seconda di dove la si guarda.
//        ⚠️ Il permesso NASCONDE, non disabilita: un'azione grigia che non si
//        potra' mai premere e' una promessa che non si mantiene, e il motivo
//        («non hai il permesso») non e' qualcosa che l'operatore possa risolvere
//        da li'. Per cio' che invece dipende dallo STATO — e che quindi puo'
//        cambiare — resta `disabled` + `tooltip`, che spiega e resta a video.
const visibleActions = computed(() =>
  props.actions.filter(
    a => a.visible !== false
      && !(a.action && !auth.isActionAllowed(a.action)),
  ),
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

// Scopo: motivo da RENDERE sotto la label nel popup kebab (dove il tooltip non
//        arriva: niente hover su touch). Solo per azioni DISABILITATE — su
//        un'azione viva il tooltip e' un'etichetta, non una spiegazione — e
//        solo se dice qualcosa in piu' della label. Stringa vuota = nessuna
//        riga aggiunta, voce identica a prima.
function actionMotivo(action) {
  if (!isActionDisabled(action)) return ''
  if (isInactiveRow.value && action.allowWhenInactive !== true) {
    return t('common.azione_non_disponibile_record_inattivo')
  }
  return action.tooltip && action.tooltip !== action.label ? action.tooltip : ''
}

// Scopo: mappa per il formato PrimeVue Menu (variante compact).
// La classe della voce e' parallela al colore inline del bottone desktop:
// default = manage (blu, come app-manage-btn) — coerente con inlineButtonClass.
// `motivo` e' campo NOSTRO (PrimeVue ignora le chiavi che non conosce): lo
// legge il template `#item` qui sotto.
const menuItems = computed(() =>
  visibleActions.value.map(a => ({
    label: a.label,
    icon: a.icon,
    disabled: isActionDisabled(a),
    motivo: actionMotivo(a),
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
  <span
    class="app-row-actions-inline"
    :class="{ 'app-row-actions-inline--off': forceCompact }"
  >
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
  <span
    class="app-row-actions-compact"
    :class="{ 'app-row-actions-compact--on': forceCompact }"
  >
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
    <!-- Template `#item`: replica il markup di default di PrimeVue (le classi
         `p-menu-item-*` sono agganciate dal CSS `.app-menu-item-*`, non si
         rinominano) e aggiunge la riga del motivo quando c'e'. -->
    <Menu ref="menuRef" :model="menuItems" popup>
      <template #item="{ item, props: itemProps }">
        <a class="p-menu-item-link" v-bind="itemProps.action">
          <span class="p-menu-item-icon" :class="item.icon" />
          <span class="p-menu-item-label">
            {{ item.label }}
            <small v-if="item.motivo" class="app-menu-item-motivo">{{ item.motivo }}</small>
          </span>
        </a>
      </template>
    </Menu>
  </span>
</template>

<script setup>
// Scopo: stato DOMINIO della sidebar morfica — pulsante Home + titolo dominio + voci menu L2.
// Icona stella per impostare la pagina preferita per il dominio.
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { computed, inject, nextTick, ref } from 'vue'
import { useNavigationStore } from '../../stores/navigation'
import { useNotify } from '../composables/useNotify'
import { useNavigationFavorites } from '../composables/useNavigationFavorites'
import { NAV_ICONS, resolveNavigationLabel } from '../navigation'
import { MANAGE_ICONS } from '../constants'
import Menu from 'primevue/menu'
import SidebarItem from './SidebarItem.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const nav = useNavigationStore()
const notify = useNotify()
const { isMenuItemAllowed } = useNavigationFavorites()
const isCollapsed = inject('sidebarCollapsed', ref(false))

// ⭐ Filtrati anche i figli di un gruppo, e il gruppo senza figli visibili
//    sparisce. I cancelli del gruppo valgono gia' dal filtro sul gruppo; qui
//    restano quelli che un figlio dichiarasse per se'.
const visibleMenu = computed(() => nav.currentMenu
  .filter(isMenuItemAllowed)
  .map(item => (item.children
    ? { ...item, children: item.children.filter(isMenuItemAllowed) }
    : item))
  .filter(item => !item.children || item.children.length > 0))

const emit = defineEmits(['navigate'])
const openGroups = ref({})

const domainLabel = computed(() => {
  if (!nav.currentDomain) return ''
  return resolveNavigationLabel({ domain: nav.currentDomain }, t) || ''
})

function itemLabel(item) {
  return resolveNavigationLabel({ domain: nav.currentDomain, menuKey: item.key }, t) || item.key
}

function hasChildren(item) {
  return Array.isArray(item.children) && item.children.length > 0
}

function flatChildren(item) {
  return hasChildren(item) ? item.children : []
}

function isItemActive(item) {
  if (item.to && route.path === item.to) return true
  return flatChildren(item).some(child => route.path === child.to)
}

function isGroupOpen(item) {
  return openGroups.value[item.key] !== false || flatChildren(item).some(child => route.path === child.to)
}

function handleBackHome() {
  nav.clearDomain()
  router.push('/')
  emit('navigate')
}

function handleLeafClick(item) {
  // La scheda la apre il guard del router (unico punto, anche per la
  // sostituzione oltre il limite): qui si naviga e basta.
  router.push(item.to)
  emit('navigate')
}

// ⭐ A sidebar chiusa un gruppo e' un'icona sola: il click apre le sue voci
//    in un menu a comparsa ACCANTO al rail (Tid 2026-10-06). ⛔ Fino ad allora
//    portava alla prima voce, e le altre del gruppo non si raggiungevano.
const gruppoMenu = ref(null)
const gruppoMenuItems = ref([])
// L'icona a cui il popup si affianca: presa dall'evento, non dai campi
// interni di PrimeVue (`target` del Menu), che un aggiornamento puo' cambiare.
let gruppoAncora = null

function apriGruppoAComparsa(item, event) {
  gruppoAncora = event?.currentTarget ?? null
  gruppoMenuItems.value = [{
    label: itemLabel(item),
    items: item.children.map(child => ({
      key: child.key,
      label: itemLabel(child),
      icon: child.icon,
      command: () => handleLeafClick(child),
    })),
  }]
  gruppoMenu.value?.toggle(event)
  // ⛔ Non basta `@show`: col popup aperto su un gruppo, il click su un ALTRO
  //    gruppo lo chiude (listener di click esterno, in cattura) e lo riapre
  //    nello stesso tick — PrimeVue non rientra in `onEnter`, niente `show`,
  //    e il popup restava accanto al gruppo di prima con le voci del nuovo.
  nextTick(affiancaAlRail)
}

// Scopo: il popup di PrimeVue si apre SOTTO l'icona, sopra le voci che
//        seguono: lo si sposta a destra del rail, allineato all'icona.
function affiancaAlRail() {
  const el = gruppoMenu.value?.container
  if (!el || !gruppoAncora) return
  const r = gruppoAncora.getBoundingClientRect()
  el.style.top = `${r.top + window.scrollY}px`
  el.style.left = `${r.right + window.scrollX + 4}px`
}

function handleMenuClick(item, event) {
  if (!hasChildren(item)) {
    handleLeafClick(item)
    return
  }
  if (isCollapsed.value) {
    apriGruppoAComparsa(item, event)
    return
  }
  openGroups.value = {
    ...openGroups.value,
    [item.key]: !isGroupOpen(item)
  }
}

function handleToggleFavorite(item) {
  if (!item.to) return
  const changed = nav.toggleFavorite(nav.currentDomain, item.to)
  if (!changed) {
    notify.warn(t('nav.preferiti_limite_raggiunto'))
  }
}
</script>

<template>
  <div class="sidebar-domain">
    <!-- Pulsante ← Home -->
    <SidebarItem
      :icon="NAV_ICONS.BACK"
      :label="t('nav.back_home')"
      class="back-home"
      @click="handleBackHome"
    />

    <div class="sidebar-divider"></div>

    <!-- Titolo dominio (solo se sidebar espansa) -->
    <div v-if="!isCollapsed" class="domain-title">
      {{ domainLabel }}
    </div>

    <!-- Voci menu L2 (filtrate su requireArea: una voce puntata su area
         BLOCCATA non viene mostrata) -->
    <template v-for="item in visibleMenu" :key="item.key">
      <SidebarItem
        :icon="item.icon"
        :label="itemLabel(item)"
        :active="isItemActive(item)"
        :gruppo="hasChildren(item)"
        @click="handleMenuClick(item, $event)"
      >
        <span class="menu-item-label">
          {{ itemLabel(item) }}
        </span>
        <i
          v-if="!isCollapsed && hasChildren(item)"
          class="app-sottomenu-icon"
          :class="isGroupOpen(item) ? MANAGE_ICONS.SOTTOMENU_APERTO : MANAGE_ICONS.SOTTOMENU"
        ></i>
        <!-- Stella preferito -->
        <i
          v-else-if="!isCollapsed"
          class="favorite-star"
          :class="nav.isFavoriteOfDomain(nav.currentDomain, item.to) ? [MANAGE_ICONS.PREFERITO_ATTIVO, 'favorite-star-attiva'] : MANAGE_ICONS.PREFERITI"
          @click.stop="handleToggleFavorite(item)"
          v-tooltip.right="nav.isFavoriteOfDomain(nav.currentDomain, item.to) ? t('nav.remove_favorite') : t('nav.set_favorite')"
        ></i>
      </SidebarItem>

      <div v-if="!isCollapsed && hasChildren(item) && isGroupOpen(item)" class="sidebar-submenu">
        <SidebarItem
          v-for="child in item.children"
          :key="child.key"
          :icon="child.icon"
          :label="itemLabel(child)"
          :active="route.path === child.to"
          class="sidebar-subitem"
          @click="handleLeafClick(child)"
        >
          <span class="menu-item-label">
            {{ itemLabel(child) }}
          </span>
          <i
            class="favorite-star"
            :class="nav.isFavoriteOfDomain(nav.currentDomain, child.to) ? [MANAGE_ICONS.PREFERITO_ATTIVO, 'favorite-star-attiva'] : MANAGE_ICONS.PREFERITI"
            @click.stop="handleToggleFavorite(child)"
            v-tooltip.right="nav.isFavoriteOfDomain(nav.currentDomain, child.to) ? t('nav.remove_favorite') : t('nav.set_favorite')"
          ></i>
        </SidebarItem>
      </div>
    </template>

    <Menu ref="gruppoMenu" :model="gruppoMenuItems" popup class="app-sidebar-gruppo-popup" />
  </div>
</template>

<style scoped>
.sidebar-domain {
  display: flex;
  flex-direction: column;
  gap: var(--app-sidebar-item-gap);
}

.domain-title {
  padding: 0.4rem 0.75rem;
  font-size: var(--app-font-size-sm);
  font-weight: 600;
  color: var(--app-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.menu-item-label {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.favorite-star {
  font-size: 0.75rem;
  color: var(--app-text-muted);
  opacity: 0;
  transition: opacity var(--app-transition-fast), color var(--app-transition-fast);
  cursor: pointer;
}

.sidebar-item:hover .favorite-star {
  opacity: 0.6;
}

.favorite-star:hover {
  opacity: 1 !important;
  color: var(--p-yellow-400);
}

/* Classe di stato, non il glifo: se `PREFERITO_ATTIVO` cambia disegno la
   stella accesa resta accesa. */
.favorite-star.favorite-star-attiva {
  opacity: 1;
  color: var(--p-yellow-400);
}

.sidebar-submenu {
  display: flex;
  flex-direction: column;
  gap: var(--app-sidebar-item-gap);
  padding-left: 1.25rem;
}

.sidebar-subitem {
  font-size: var(--app-font-size-sm);
}

.back-home {
  color: var(--app-text-muted);
}

.back-home:hover {
  color: var(--app-text-color);
}
</style>

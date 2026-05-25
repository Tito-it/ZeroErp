<script setup>
// Scopo: render atomico di un preferito di navigazione, in variante sidebar o tile Home.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNavigationStore } from '../../stores/navigation'
import { useNavigationFavorites } from '../composables/useNavigationFavorites'

const props = defineProps({
  domain: { type: String, required: true },
  path: { type: String, required: true },
  variant: { type: String, default: 'sidebar' },
  collapsed: { type: Boolean, default: false },
  draggable: { type: Boolean, default: false }
})

const emit = defineEmits(['navigate', 'removed', 'dragstart', 'dragover', 'drop', 'dragend'])

const { t } = useI18n()
const nav = useNavigationStore()
const { resolveFavorite, navigateToFavorite } = useNavigationFavorites()

const favorite = computed(() => resolveFavorite(props.domain, props.path))

function onNavigate() {
  if (!favorite.value) return
  const opened = navigateToFavorite(favorite.value)
  if (opened) emit('navigate', favorite.value)
}

function onRemove() {
  nav.removeFavorite(props.domain, props.path)
  emit('removed', { domain: props.domain, path: props.path })
}
</script>

<template>
  <div
    v-if="favorite"
    class="favorite-item"
    :class="[
      `favorite-item--${variant}`,
      { 'favorite-item--collapsed': collapsed, 'favorite-item--draggable': draggable }
    ]"
    :draggable="draggable"
    v-tooltip.right="favorite.tooltip"
    @click="onNavigate"
    @dragstart="$emit('dragstart', $event)"
    @dragover="$emit('dragover', $event)"
    @drop="$emit('drop', $event)"
    @dragend="$emit('dragend', $event)"
  >
    <i
      v-if="draggable && !collapsed"
      class="pi pi-bars favorite-item__handle"
      aria-hidden="true"
    ></i>
    <i class="favorite-item__icon" :class="favorite.icon" aria-hidden="true"></i>

    <span v-if="!collapsed" class="favorite-item__text">
      <span class="favorite-item__label">{{ favorite.label }}</span>
      <span v-if="variant === 'tile'" class="favorite-item__domain">{{ favorite.domainLabel }}</span>
    </span>

    <button
      v-if="!collapsed"
      type="button"
      class="favorite-item__remove"
      :aria-label="t('nav.preferiti_rimuovi')"
      v-tooltip.top="t('nav.preferiti_rimuovi')"
      @click.stop="onRemove"
    >
      <i class="pi pi-star-fill" aria-hidden="true"></i>
    </button>
  </div>
</template>

<style scoped>
.favorite-item {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  color: var(--app-sidebar-item-color);
  cursor: pointer;
  transition: background var(--app-transition-fast), color var(--app-transition-fast), border-color var(--app-transition-fast);
}

.favorite-item:hover {
  background: var(--app-sidebar-item-hover-bg);
  color: var(--app-sidebar-item-hover-color);
}

.favorite-item--sidebar {
  min-height: 2.35rem;
  padding: 0.55rem 0.75rem;
  border-radius: var(--app-sidebar-item-radius);
  font-size: var(--app-font-size-sm);
}

.favorite-item--tile {
  position: relative;
  min-height: 8.5rem;
  flex-direction: column;
  justify-content: center;
  align-items: flex-start;
  gap: 0.55rem;
  padding: 1rem;
  border: 1px solid var(--app-card-border);
  border-radius: var(--app-card-radius);
  background: var(--app-card-bg);
  color: var(--p-text-color);
}

.favorite-item--tile:hover {
  border-color: var(--app-card-hover-border);
  background: var(--app-card-hover-bg);
}

.favorite-item--collapsed {
  justify-content: center;
  padding: 0.5rem 0.35rem;
}

.favorite-item--draggable {
  cursor: grab;
}

.favorite-item--draggable:active {
  cursor: grabbing;
}

.favorite-item__handle {
  font-size: 0.75rem;
  color: var(--p-text-muted-color);
  opacity: 0.65;
}

.favorite-item__icon {
  width: 1.25rem;
  text-align: center;
  color: var(--app-icon-color);
}

.favorite-item--tile .favorite-item__icon {
  width: auto;
  font-size: 1.5rem;
  color: var(--app-card-icon-color);
}

.favorite-item:hover .favorite-item__icon {
  color: inherit;
}

.favorite-item__text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

/* In variante tile il parent e' `flex-direction: column`: `flex: 1` espande
 * in ALTEZZA, non in larghezza. Senza `width: 100%` esplicito il container
 * testo ha larghezza intrinseca del contenuto e l'ellipsis non scatta
 * (label tipo "Unita' misura" sborda fuori dal padding del tile).
 * Riserviamo anche `padding-right` per non sovrapporci al bottone remove
 * posizionato absolute in alto a destra. */
.favorite-item--tile .favorite-item__text {
  width: 100%;
  padding-right: 1.5rem;
}

.favorite-item__label,
.favorite-item__domain {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.favorite-item__label {
  font-weight: 500;
}

/* Label tile: font piu' compatto per evitare overflow su tile stretti
 * (es. mobile grid a 2 colonne, label tipo "Approvazioni prezzo"). */
.favorite-item--tile .favorite-item__label {
  font-size: 0.85rem;
}

.favorite-item__domain {
  color: var(--p-text-muted-color);
  font-size: 0.75rem;
}

.favorite-item__remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.6rem;
  height: 1.6rem;
  border: 0;
  border-radius: 999px;
  background: transparent;
  color: var(--p-yellow-400);
  cursor: pointer;
  opacity: 0;
  transition: opacity var(--app-transition-fast), background var(--app-transition-fast);
}

.favorite-item:hover .favorite-item__remove,
.favorite-item__remove:focus-visible {
  opacity: 1;
}

.favorite-item__remove:hover {
  background: color-mix(in srgb, var(--p-yellow-400) 14%, transparent);
}

.favorite-item--tile .favorite-item__remove {
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
}
</style>

<script setup>
// Scopo: dashboard home — benvenuto, sessioni attive, 4 card placeholder dashboard
import { ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import { useAuthStore } from '../../stores/auth'
import { useUiStore } from '../../stores/ui'
import { useNavigationFavorites } from '../composables/useNavigationFavorites'
import { MANAGE_ICONS } from '../constants'
import FavoriteItem from '../components/FavoriteItem.vue'
import SessioniAttivePanel from '../components/SessioniAttivePanel.vue'

const { t } = useI18n()
const auth = useAuthStore()
const ui = useUiStore()
const { visibleFavorites, reorderVisibleDomainFavorites } = useNavigationFavorites()
const draggedFavorite = ref(null)
// Stato espanso/collassato del pannello preferiti — persistito per-utente nel
// ui store (stesso pattern di isDark): la scelta sopravvive a logout/login
// dello stesso utente e non si confonde con quella di altri operatori sullo
// stesso browser. Default: collassato (coerente con SessioniAttivePanel).
const { favoritesExpanded } = storeToRefs(ui)

// 4 card placeholder per futura dashboard KPI
const dashCards = [
  { key: 'dash-1', labelKey: 'home.dash_1', icon: 'pi pi-wrench' },
  { key: 'dash-2', labelKey: 'home.dash_2', icon: 'pi pi-wrench' },
  { key: 'dash-3', labelKey: 'home.dash_3', icon: 'pi pi-wrench' },
  { key: 'dash-4', labelKey: 'home.dash_4', icon: 'pi pi-wrench' }
]

function onFavoriteDragStart(favorite, event) {
  draggedFavorite.value = favorite
  event.dataTransfer.effectAllowed = 'move'
}

function onFavoriteDragOver(event) {
  if (!draggedFavorite.value) return
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

function onFavoriteDrop(targetFavorite, event) {
  event.preventDefault()
  if (!draggedFavorite.value) return
  const source = draggedFavorite.value
  if (source.domain !== targetFavorite.domain || source.path === targetFavorite.path) return

  const domainPaths = visibleFavorites.value
    .filter(favorite => favorite.domain === source.domain)
    .map(favorite => favorite.path)
  const fromIndex = domainPaths.indexOf(source.path)
  const toIndex = domainPaths.indexOf(targetFavorite.path)
  if (fromIndex === -1 || toIndex === -1) return

  const next = [...domainPaths]
  next.splice(toIndex, 0, next.splice(fromIndex, 1)[0])
  reorderVisibleDomainFavorites(source.domain, next)
}

function onFavoriteDragEnd() {
  draggedFavorite.value = null
}
</script>

<template>
  <div class="home-view">
    <h2>{{ t('home.welcome_user', { name: auth.displayName || t('home.welcome_fallback') }) }}</h2>

    <SessioniAttivePanel />

    <!-- Pannello preferiti — pattern espandibile/collassabile mutuato da
         SessioniAttivePanel: header sempre visibile con badge count + chevron
         toggle, body (grid) reso solo se expanded. Se zero preferiti il
         pannello mostra l'empty-state didattico (no header collapse perche'
         non c'e' contenuto da collassare). -->
    <section class="favorites-panel" v-if="visibleFavorites.length > 0">
      <div class="favorites-panel__header">
        <h3 class="favorites-panel__title">
          <i class="pi pi-star" aria-hidden="true"></i>
          <span>{{ t('nav.preferiti') }}</span>
          <Badge :value="visibleFavorites.length" severity="info" />
        </h3>
        <Button
          :icon="favoritesExpanded ? MANAGE_ICONS.COLLAPSE : MANAGE_ICONS.EXPAND"
          text
          rounded
          size="small"
          :aria-label="favoritesExpanded ? t('nav.preferiti_comprimi') : t('nav.preferiti_espandi')"
          v-tooltip.left="favoritesExpanded ? t('nav.preferiti_comprimi') : t('nav.preferiti_espandi')"
          @click="ui.toggleFavoritesExpanded()"
        />
      </div>

      <div v-if="favoritesExpanded" class="favorites-grid">
        <FavoriteItem
          v-for="favorite in visibleFavorites"
          :key="`${favorite.domain}:${favorite.path}`"
          :domain="favorite.domain"
          :path="favorite.path"
          variant="tile"
          draggable
          @dragstart="event => onFavoriteDragStart(favorite, event)"
          @dragover="onFavoriteDragOver"
          @drop="event => onFavoriteDrop(favorite, event)"
          @dragend="onFavoriteDragEnd"
        />
      </div>
    </section>

    <section v-else class="favorites-panel">
      <div class="app-empty-state">
        <i class="pi pi-star" aria-hidden="true"></i>
        <span>{{ t('nav.preferiti_empty_hint') }}</span>
      </div>
    </section>

    <div class="dashboard-grid">
      <div
        v-for="card in dashCards"
        :key="card.key"
        class="dash-card"
      >
        <i :class="card.icon"></i>
        <span>{{ t(card.labelKey) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  max-width: 900px;
  margin: auto;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-height: 100%;
  width: 100%;
}

.home-view h2 {
  margin-bottom: 1.5rem;
  font-weight: 600;
  color: var(--p-text-color);
}

.favorites-panel {
  width: 100%;
  margin-bottom: 1.5rem;
}

.favorites-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.favorites-panel__title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0;
  font-size: var(--app-font-size-base);
  font-weight: 600;
  color: var(--p-text-color);
}

.favorites-panel__title i {
  color: var(--p-yellow-400);
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
  width: 100%;
}

.dash-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem 1rem;
  border-radius: var(--app-card-radius);
  background: var(--app-card-bg);
  border: 1px solid var(--app-card-border);
  color: var(--p-text-muted-color);
  font-size: 0.9rem;
  font-weight: 500;
}

.dash-card i {
  font-size: 1.75rem;
  color: var(--p-text-muted-color);
}

/* Tablet landscape */
@media (max-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  }

  .favorites-grid {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  }
}

/* Tablet portrait / mobile */
@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .favorites-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .dash-card {
    padding: 1.25rem 0.75rem;
  }
}
</style>

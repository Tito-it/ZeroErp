<script setup>
// Scopo: dashboard home — benvenuto, sessioni attive, preferiti di
// navigazione e griglia di card KPI configurabili per utente.
//
// I due meccanismi della home sono distinti e ortogonali, non vanno
// confusi:
//   - PREFERITI: scorciatoie a voci di menu, persistite in localStorage
//     user-scoped (stores/navigation). Rispondono a "dove voglio andare".
//   - CARD KPI: widget configurabili persistiti a DB (ui.dashboard_*),
//     risolti con cascata preset+permessi. Rispondono a "devo andarci?".
import { onActivated, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { useI18n } from 'vue-i18n'
import Badge from 'primevue/badge'
import Button from 'primevue/button'
import { useAuthStore } from '../../stores/auth'
import { useUiStore } from '../../stores/ui'
import { useNavigationFavorites } from '../composables/useNavigationFavorites'
import { useDashboardConfig } from '../composables/useDashboardConfig'
import { useWidgetNavigation } from '../composables/useWidgetNavigation'
import { MANAGE_ICONS, STATUS_ICONS } from '../constants'
import FavoriteItem from '../components/FavoriteItem.vue'
import SessioniAttivePanel from '../components/SessioniAttivePanel.vue'
import KpiCard from '../components/dash/KpiCard.vue'
import DashboardWidgetModal from '../components/dash/DashboardWidgetModal.vue'

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

// ── Card KPI configurabili ──────────────────────────────────────────
// Codice stabile della dashboard home in ui.dashboard_definizione.
const DASHBOARD_CODICE = 'home'

const {
  config: dashConfig,
  loaded: dashLoaded,
  loading: dashLoading,
  widgetNuovi,
  widgetVisibili,
  dimensioneMax,
  poolVuoto,
  loadAll: loadDashboard,
  applyChange: applyDashChange,
  save: saveDashboard,
  reset: resetDashboard,
  contatoreDi,
} = useDashboardConfig(DASHBOARD_CODICE)

const { resolveWidgetTarget, navigateToWidget } = useWidgetNavigation()

const personalizzaVisible = ref(false)

// onActivated e non onMounted: sotto KeepAlive (AppLayout) la home viene
// messa in cache — al rientro config e contatori KPI vanno rinfrescati,
// altrimenti i numeri restano quelli della prima visita (scatta anche al
// primo mount). Fallimento gia' notificato da useApiHandler: qui non
// serve altro che non bloccare il resto della pagina (preferiti e
// sessioni restano utilizzabili).
onActivated(loadDashboard)

// Scopo: una card e' cliccabile solo se il suo deep-link risolve a una
//        voce di menu permessa. Un widget informativo (senza deep_link)
//        o un seed incoerente danno una card non cliccabile invece di un
//        vicolo cieco.
function isWidgetCliccabile(widget) {
  return resolveWidgetTarget(widget?.deep_link) !== null
}

function onApriWidget(widget) {
  navigateToWidget(widget?.deep_link)
}

// Scopo: applica la selezione/ordine scelti nella modale e salva.
// Il payload della modale porta SOLO {codice, ordine, visibile}: va fuso
// coi widget correnti per codice, non sostituito — altrimenti la griglia
// perde i campi di catalogo (etichetta, deep_link, contatore_key) finche'
// il reload post-save non riesce, e a save fallito resterebbe rotta.
// ⚠️ Senza `widget` la modale non ha cambiato niente: si salva senza toccarli.
async function onPersonalizzaApply(payload) {
  if (payload.widget) applyDashChange(c => {
    const perCodice = new Map((c.widget || []).map(w => [w.codice, w]))
    c.widget = payload.widget.map(w => ({
      ...perCodice.get(w.codice),
      ...w,
    }))
  })
  const result = await saveDashboard()
  if (result !== null) personalizzaVisible.value = false
}

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
          <i :class="MANAGE_ICONS.PREFERITI" aria-hidden="true"></i>
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
        <i :class="MANAGE_ICONS.PREFERITI" aria-hidden="true"></i>
        <span>{{ t('nav.preferiti_empty_hint') }}</span>
      </div>
    </section>

    <!-- Card KPI configurabili. La sezione compare solo a fetch riuscita:
         prima del load non si dichiara nulla, ne' card ne' assenza di
         card (empty-state onesto). -->
    <section v-if="dashLoaded" class="dash-panel">
      <div class="dash-panel-header">
        <h3 class="dash-panel-title">{{ t('home.kpi_titolo') }}</h3>
        <Badge v-if="widgetNuovi > 0" :value="widgetNuovi" severity="info" />
        <Button
          class="dash-panel-action"
          :icon="MANAGE_ICONS.PERSONALIZZA"
          text
          rounded
          :aria-label="t('home.personalizza_titolo')"
          v-tooltip.bottom="t('home.personalizza_titolo')"
          @click="personalizzaVisible = true"
        />
      </div>

      <div v-if="widgetVisibili.length > 0" class="app-dash-cards">
        <KpiCard
          v-for="widget in widgetVisibili"
          :key="widget.codice"
          :widget="widget"
          :contatore="contatoreDi(widget)"
          :loading="dashLoading"
          :cliccabile="isWidgetCliccabile(widget)"
          @apri="onApriWidget"
        />
      </div>

      <!-- Empty-state onesto, differenziato: invitare a "scegliere le card"
           chi non ne ha nessuna disponibile sarebbe una bugia. -->
      <div v-else class="app-empty-state">
        <i :class="STATUS_ICONS.VUOTO" aria-hidden="true"></i>
        <span>{{ poolVuoto ? t('home.kpi_empty_nessuna_disponibile') : t('home.kpi_empty_hint') }}</span>
      </div>
    </section>

    <DashboardWidgetModal
      v-model:visible="personalizzaVisible"
      :config="dashConfig"
      :widget-nuovi="widgetNuovi"
      :dimensione-max="dimensioneMax"
      :loading="dashLoading"
      @apply="onPersonalizzaApply"
      @reset="resetDashboard"
    />
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
  color: var(--app-text-color);
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
  color: var(--app-text-color);
}

.favorites-panel__title i {
  color: var(--p-yellow-400);
}

.favorites-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 0.75rem;
}

/* Pannello card KPI. La griglia interna usa la classe globale
   `.app-dash-cards` (main.css), la stessa dei cruscotti vendite: le card
   della home e quelle dei cruscotti devono respirare identiche. */
.dash-panel {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.dash-panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.dash-panel-title {
  margin: 0;
  font-size: var(--app-font-size-sm);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--app-text-muted);
}

/* Il bottone "personalizza" si stacca a destra dal titolo. */
.dash-panel-action {
  margin-left: auto;
}

/* Tablet landscape */
@media (max-width: 1023.98px) {
  .favorites-grid {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  }
}

/* Tablet portrait / mobile */
@media (max-width: 767.98px) {
  .favorites-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

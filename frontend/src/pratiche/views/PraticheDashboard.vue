<script setup>
// Scopo: Dashboard pratiche con sidebar coda lavoro + master-detail (SearchTable + FlussiPanel).
// Layout: desktop = sidebar 280px + area principale con SearchTable sopra e FlussiPanel sotto.
// Tablet: sidebar collassa in toggle, flussi passano da split a tab.
// Riusa: PraticheCodaLavoro, PraticheSearchTable, PraticaFlussiPanel, PraticaDrawer, FlussoDrawer.
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { usePraticheStore } from '../stores/pratiche'
import PraticheCodaLavoro from '../components/PraticheCodaLavoro.vue'
import PraticheSearchTable from '../components/PraticheSearchTable.vue'
import PraticaFlussiPanel from '../components/PraticaFlussiPanel.vue'
import PraticaDrawer from '../components/PraticaDrawer.vue'
import FlussoDrawer from '../components/FlussoDrawer.vue'

const { t } = useI18n()
const store = usePraticheStore()
const drawer = useDrawerState()
const { execute } = useApiHandler()
useReadonlyMode(READONLY_DOMAINS.PRATICHE)

// --- Coda lavoro ---
onMounted(() => { store.loadCodaLavoro() })

function onCodaSelectFlusso(item) {
  // Seleziona la pratica nella tabella e carica i flussi
  store.selectedPraticaId = item.pratica_id
  loadFlussiForPratica(item.pratica_id)
}

async function onPrendiInCarico(item) {
  const result = await execute(
    () => store.prendiInCarico(item.flusso_id),
    { successMessage: t('pratiche.preso_in_carico') }
  )
  if (result !== null) {
    await store.loadCodaLavoro()
    if (store.selectedPraticaId) await loadFlussiForPratica(store.selectedPraticaId)
  }
}

// --- Flussi della pratica selezionata ---
const flussi = ref([])
const flussiLoading = ref(false)
const selectedFlussoId = ref(null)

async function loadFlussiForPratica(praticaId) {
  if (!praticaId) { flussi.value = []; return }
  flussiLoading.value = true
  try {
    flussi.value = await store.loadFlussi(praticaId)
  } finally {
    flussiLoading.value = false
  }
}

// Quando cambia la pratica selezionata nella SearchTable
function onRowClick(data) {
  store.selectedPraticaId = data.id
  loadFlussiForPratica(data.id)
}

// Codice della pratica selezionata (per barra contesto sopra flussi)
const selectedPraticaCodice = computed(() => {
  if (!store.selectedPraticaId) return null
  const item = store.items.find(i => i.id === store.selectedPraticaId)
  return item?.codice || null
})

// --- FlussoDrawer ---
const flussoDrawerVisible = ref(false)
const flussoSelezionato = ref(null)

function onOpenFlusso(flusso) {
  flussoSelezionato.value = flusso
  flussoDrawerVisible.value = true
}

async function onFlussoSaved() {
  flussoDrawerVisible.value = false
  if (store.selectedPraticaId) await loadFlussiForPratica(store.selectedPraticaId)
  await store.loadCodaLavoro()
}

// --- PraticaDrawer ---
async function onDrawerSaved() {
  store.filters.offset = 0
  if (store.hasSearched) await store.fetchList()
  await store.loadCodaLavoro()
  if (store.selectedPraticaId) await loadFlussiForPratica(store.selectedPraticaId)
  drawer.close()
}

// Watch selectedPraticaId per caricare flussi (copre anche cambio da altri componenti)
watch(() => store.selectedPraticaId, (id, oldId) => {
  if (id && id !== oldId) loadFlussiForPratica(id)
  else if (!id) flussi.value = []
})

// Ricalcola layout DataTable quando hasSearched cambia (sidebar/flussi appaiono/scompaiono).
// ResizeObserver sul container: deterministico, senza setTimeout.
const dashboardRef = ref(null)
let resizeObserver = null

onMounted(() => {
  if (dashboardRef.value) {
    resizeObserver = new ResizeObserver(() => {
      window.dispatchEvent(new Event('resize'))
    })
    resizeObserver.observe(dashboardRef.value)
  }
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
})
</script>

<template>
  <div ref="dashboardRef" class="app-page pratiche-dashboard">

    <!-- Sidebar: Coda lavoro -->
    <aside v-if="store.hasSearched" class="dashboard-sidebar">
      <div class="dashboard-sidebar-spacer" />
      <PraticheCodaLavoro
        :items="store.codaLavoro"
        :loading="store.codaLoading"
        :selected-flusso-id="selectedFlussoId"
        @select-flusso="onCodaSelectFlusso"
        @prendi-in-carico="onPrendiInCarico"
      />
    </aside>

    <!-- Area principale -->
    <main class="dashboard-main">

      <!-- SearchTable pratiche (sempre visibile — contiene filtri e placeholder) -->
      <div class="dashboard-table">
        <PraticheSearchTable
          @new="drawer.openCreate"
          @row-click="onRowClick"
        />
      </div>

      <!-- Barra contesto pratica + flussi — v-show mantiene spazio nel flex layout -->
      <div class="dashboard-flussi-wrapper">
        <div class="dashboard-flussi-context">
          <span v-if="selectedPraticaCodice" class="flussi-context-label">
            <i class="pi pi-folder-open" />
            {{ t('pratiche.visualizzazione_pratica', { codice: selectedPraticaCodice }) }}
          </span>
          <span v-else class="flussi-context-hint">
            {{ t('pratiche.flussi_panel_vuoto') }}
          </span>
        </div>
        <div class="dashboard-flussi">
          <PraticaFlussiPanel
            :flussi="flussi"
            :loading="flussiLoading"
            :pratica-id="store.selectedPraticaId"
            @open-flusso="onOpenFlusso"
          />
        </div>
      </div>

    </main>

    <!-- Drawer: Creazione/Dettaglio pratica -->
    <PraticaDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :pratica-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <!-- Drawer: Esecuzione flusso -->
    <FlussoDrawer
      :visible="flussoDrawerVisible"
      @update:visible="v => flussoDrawerVisible = v"
      :flusso="flussoSelezionato"
      :pratica-id="store.selectedPraticaId"
      @saved="onFlussoSaved"
    />

  </div>
</template>

<style scoped>
.pratiche-dashboard {
  display: flex;
  flex-direction: row;
  height: 100%;
  overflow: hidden;
  gap: 0;
}

.dashboard-sidebar {
  width: 260px;
  min-width: 260px;
  flex-shrink: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Spacer: allinea coda lavoro con le prime righe della tabella (toolbar + paginator) */
.dashboard-sidebar-spacer {
  height: 90px;
  flex-shrink: 0;
  background: var(--surface-ground);
}

.dashboard-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 0;
}

/* Tabella: occupa lo spazio restante, overflow gestito internamente da DataTable */
.dashboard-table {
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

/* Wrapper flussi: altezza fissa, non comprimibile */
.dashboard-flussi-wrapper {
  height: 230px;
  flex: 0 0 230px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Barra contesto pratica sopra il separatore */
.dashboard-flussi-context {
  display: flex;
  align-items: center;
  padding: 0.35rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 600;
  background: var(--surface-ground);
  border-top: 2px solid var(--p-info-color, var(--p-primary-color));
  flex: 0 0 auto;
}

.flussi-context-label {
  color: var(--p-info-color, var(--p-primary-color));
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.flussi-context-hint {
  color: var(--text-color-secondary);
  font-style: italic;
  font-weight: 400;
}

.dashboard-flussi {
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
}

/* Tablet/mobile: layout verticale, container scrolla */
@media (max-width: 1279px) {
  .pratiche-dashboard {
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
  }
  .dashboard-sidebar {
    width: 100%;
    min-width: 100%;
    height: 160px;
    flex: 0 0 160px;
    border-right: none;
    border-bottom: 2px solid var(--p-info-color, var(--p-primary-color));
  }
  .dashboard-sidebar-spacer { display: none; }
  .dashboard-main {
    overflow: visible;
    flex: 0 0 auto;
  }
  .dashboard-table {
    overflow: visible;
    flex: 0 0 auto;
  }
  .dashboard-flussi-wrapper {
    height: 200px;
    flex: 0 0 200px;
  }
}
</style>

<script setup>
// Scopo: Dashboard pratiche con sidebar coda lavoro + master-detail (SearchTable + roadmap percorso).
// Layout: desktop = sidebar 280px + area principale con SearchTable sopra e roadmap sotto.
// Tablet: sidebar collassa in toggle.
// Riusa: PraticheCodaLavoro, PraticheSearchTable, PraticaPercorso, PraticaDrawer, FlussoDrawer.
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, STATI_PRATICA_TERMINALI } from '../../core/constants'
import { usePraticheStore } from '../stores/pratiche'
import PraticheCodaLavoro from '../components/PraticheCodaLavoro.vue'
import PraticheSearchTable from '../components/PraticheSearchTable.vue'
import PraticaPercorso from '../components/PraticaPercorso.vue'
import PraticaDrawer from '../components/PraticaDrawer.vue'
import FlussoDrawer from '../components/FlussoDrawer.vue'
import PreventiviDrawer from '../../vendite/preventivi/components/PreventiviDrawer.vue'
import { collegaPratica } from '../../vendite/preventivi/api/preventiviApi'
import { getFlusso, createFlusso } from '../api/pratiche-api'

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
  loadPercorsoPratica(item.pratica_id)
}

async function onPrendiInCarico(item) {
  const result = await execute(
    () => store.prendiInCarico(item.flusso_id),
    { successMessage: t('pratiche.preso_in_carico') }
  )
  if (result !== null) {
    await store.loadCodaLavoro()
    if (store.selectedPraticaId) await loadPercorsoPratica(store.selectedPraticaId)
  }
}

// --- Percorso (roadmap) della pratica selezionata ---
const percorso = ref([])
const percorsoLoading = ref(false)
const selectedFlussoId = ref(null)

async function loadPercorsoPratica(praticaId) {
  if (!praticaId) { percorso.value = []; return }
  percorsoLoading.value = true
  try {
    percorso.value = await store.loadPercorso(praticaId)
  } finally {
    percorsoLoading.value = false
  }
}

// Quando cambia la pratica selezionata nella SearchTable
function onRowClick(data) {
  store.selectedPraticaId = data.id
  loadPercorsoPratica(data.id)
}

// Apre la scheda pratica (drawer edit) sulla pratica selezionata: e' qui che
// vivono le azioni di stato (Apri/Sospendi/Chiudi/Annulla). Il row-click resta
// dedicato alla selezione per la roadmap percorso; la scheda si apre da qui.
// Passiamo solo l'id: il drawer rifa' la fetchDetail, indipendentemente dal
// fatto che la riga provenga dalla SearchTable o dalla coda lavoro.
function onApriScheda() {
  if (!store.selectedPraticaId) return
  drawer.editRow({ id: store.selectedPraticaId }, 'id')
}

// Codice della pratica selezionata (per barra contesto sopra flussi)
const selectedPraticaCodice = computed(() => {
  if (!store.selectedPraticaId) return null
  const item = store.items.find(i => i.id === store.selectedPraticaId)
  return item?.codice || null
})

// Pratica selezionata in stato terminale (CHIUSA/ANNULLATA) → percorso e flussi
// in sola lettura: niente nuovi step, flussi esistenti consultabili ma non
// modificabili. La scheda pratica (PraticaDrawer) si auto-protegge dal proprio
// dettaglio, qui copriamo percorso + drawer flusso che vivono nella dashboard.
// Lo stato si legge dalla riga in `store.items` (ricerca). La coda lavoro
// esclude le pratiche terminali (fn_coda_lavoro_operatore) quindi non puo'
// selezionare una terminale non presente in `store.items`; oltre alla difesa
// DB (guard che rifiuta le operazioni su pratica terminale).
const selectedPraticaReadonly = computed(() => {
  if (!store.selectedPraticaId) return false
  const item = store.items.find(i => i.id === store.selectedPraticaId)
  return item ? STATI_PRATICA_TERMINALI.includes(item.stato_codice_interno) : false
})

// --- FlussoDrawer ---
const flussoDrawerVisible = ref(false)
const flussoSelezionato = ref(null)

// Azione roadmap in corso: blocca i click (anti doppia creazione).
const percorsoBusy = ref(false)

// Apre un flusso esistente dalla roadmap (per id → carica il dettaglio).
async function onOpenFlussoById(flussoId) {
  percorsoBusy.value = true
  try {
    const res = await execute(() => getFlusso(store.selectedPraticaId, flussoId))
    if (res !== null) {
      flussoSelezionato.value = res
      flussoDrawerVisible.value = true
    }
  } finally {
    percorsoBusy.value = false
  }
}

// Crea uno step della roadmap (template-bound) e lo apre. Il guard prerequisiti
// DB (esito-aware, BEFORE INSERT) rifiuta con errore parlante se non abilitato.
async function onCreateFlusso(templateFlussoId) {
  percorsoBusy.value = true
  try {
    const res = await execute(
      () => createFlusso(store.selectedPraticaId, { template_flusso_id: templateFlussoId }),
      { successMessage: t('pratiche.flusso_creato') }
    )
    if (res !== null) {
      await loadPercorsoPratica(store.selectedPraticaId)
      flussoSelezionato.value = await execute(() => getFlusso(store.selectedPraticaId, res.flusso_id))
      if (flussoSelezionato.value !== null) flussoDrawerVisible.value = true
    }
  } finally {
    percorsoBusy.value = false
  }
}

async function onFlussoSaved() {
  flussoDrawerVisible.value = false
  if (store.selectedPraticaId) await loadPercorsoPratica(store.selectedPraticaId)
  await store.loadCodaLavoro()
}

// tipo_prestazione della pratica selezionata: discrimina il routing PREVENTIVI
// nel FlussoDrawer (APPROVAZIONE_CLIENTE → M2, PREVENTIVAZIONE → apri preventivo).
const selectedPraticaTipo = computed(() => {
  if (!store.selectedPraticaId) return ''
  const item = store.items.find(i => i.id === store.selectedPraticaId)
  return item?.tipo_prestazione_codice || ''
})

// --- PreventivoDrawer (testa del flusso: PREVENTIVAZIONE) ---
const preventivoDrawerVisible = ref(false)
const preventivoCtxPraticaId = ref(null)
const preventivoLinked = ref(false)

// Apertura dal flusso PREVENTIVAZIONE: crea il preventivo collegato alla pratica.
function onOpenPreventivo(praticaId) {
  preventivoCtxPraticaId.value = praticaId
  preventivoLinked.value = false
  preventivoDrawerVisible.value = true
}

// Al primo salvataggio con id, aggancia il preventivo come ROOT alla pratica
// (idempotente lato BE; flag per evitare chiamate ripetute sui salvataggi
// successivi). È la testa che abilita M2 e l'handler a valle.
async function onPreventivoSaved(result) {
  const preventivoId = result?.id
  if (preventivoCtxPraticaId.value && preventivoId && !preventivoLinked.value) {
    const ok = await execute(
      () => collegaPratica(preventivoId, { pratica_id: preventivoCtxPraticaId.value }),
      { successMessage: t('pratiche.preventivo_collegato') }
    )
    if (ok !== null) preventivoLinked.value = true
  }
  if (store.selectedPraticaId) await loadPercorsoPratica(store.selectedPraticaId)
}

// --- PraticaDrawer ---
async function onDrawerSaved() {
  store.filters.offset = 0
  if (store.hasSearched) await store.fetchList()
  await store.loadCodaLavoro()
  if (store.selectedPraticaId) await loadPercorsoPratica(store.selectedPraticaId)
  drawer.close()
}

// Watch selectedPraticaId per caricare flussi (copre anche cambio da altri componenti)
watch(() => store.selectedPraticaId, (id, oldId) => {
  if (id && id !== oldId) loadPercorsoPratica(id)
  else if (!id) percorso.value = []
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
            <Button
              :label="t('pratiche.apri_scheda')"
              icon="pi pi-external-link"
              text
              size="small"
              class="app-escape"
              @click="onApriScheda"
            />
          </span>
          <span v-else class="flussi-context-hint">
            {{ t('pratiche.flussi_panel_vuoto') }}
          </span>
        </div>
        <div class="dashboard-flussi">
          <PraticaPercorso
            :percorso="percorso"
            :loading="percorsoLoading"
            :pratica-id="store.selectedPraticaId"
            :busy="percorsoBusy"
            :readonly="selectedPraticaReadonly"
            @open-flusso="onOpenFlussoById"
            @create-flusso="onCreateFlusso"
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
      :tipo-prestazione-codice="selectedPraticaTipo"
      :readonly="selectedPraticaReadonly"
      @saved="onFlussoSaved"
      @open-preventivo="onOpenPreventivo"
    />

    <!-- Drawer: Preventivo collegato (testa PREVENTIVAZIONE). praticaId nasconde
         l'azione accetta dal drawer: l'accettazione passa dal flusso M2. -->
    <PreventiviDrawer
      :visible="preventivoDrawerVisible"
      @update:visible="v => preventivoDrawerVisible = v"
      mode="create"
      :pratica-id="preventivoCtxPraticaId"
      @saved="onPreventivoSaved"
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

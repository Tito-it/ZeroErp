<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: ⭐ I FONDI FATTURA CHE CHIEDONO UNA PERSONA. Elenco dei casi in cui il
//        giro automatico si FERMA e non prosegue da solo: quattro motivi, un
//        vocabolario chiuso, e per ognuno una riga che resta lì finché
//        qualcuno non decide.
//
// ⭐ PERCHÉ ESISTE QUESTA PAGINA (2026-08-22). La vista, il catalogo della
// lista e l'endpoint c'erano dal 15-08 — mancava solo il posto da cui
// guardarli: nessun `.vue` montava `vendite.fondi_fattura_da_decidere`, quindi
// l'elenco esisteva e nessun operatore poteva aprirlo. È anche la ragione per
// cui il presidio dei seed contava 47 liste e il registro delle liste MONTATE
// ne contava 46: la differenza era esattamente questa.
//
// ⚠️ SOLA LETTURA, e non è una fase del lavoro: la vista PRESENTA e non sana.
// Nessuna di queste righe ha un gemello automatico che la corregge — sanarle
// vorrebbe dire muovere denaro senza che nessuno l'abbia deciso. Le azioni
// (emettere il fondo, correggere l'utility, annullare l'atto) vivono dove
// vivono già: sul documento. Da qui ci si arriva col click sulla riga.
//
// 📌 Coda di lavoro, non lista storica: nessun floor temporale di default
// (vedi lo store) — l'arretrato è il motivo per cui si apre questa pagina.
import { onMounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import Select from 'primevue/select'
import Tag from 'primevue/tag'

import ExportDialog from '../../core/components/ExportDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useNotify } from '../../core/composables/useNotify'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { extractApiError } from '../../core/utils/apiError'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { motivoFondoDaDecidereSeverity } from '../../core/utils/severity'
import FatturaDrawer from './FatturaDrawer.vue'
import { exportFondiFatturaDaDecidere } from '../api/fondiFattura'
import { useFondiFatturaDaDecidereStore } from '../stores/fondiFatturaDaDecidere'

// Vocabolario CHIUSO dei motivi (quattro letterali nei rami della UNION della
// vista: nessun dato li produce). Vive qui e non in `constants.js` perché è
// l'unico consumatore; il giorno del secondo si estrae.
// ⚠️ L'ORDINE è quello di lettura, non alfabetico: prima i due casi da
// DECIDERE, poi i due da CORREGGERE.
const MOTIVI = [
  'PROPOSTA_SENZA_ATTO',
  'NON_PIU_CAPIENTE',
  'IMPORTO_NON_CORRISPONDENTE',
  'UTILITY_NON_ATTRIBUIBILE',
]

const { t, te } = useI18n()
const notify = useNotify()
const store = useFondiFatturaDaDecidereStore()

const {
  onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, exportDialogVisible, exportLoading, onExportConfirm,
  onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn: exportFondiFatturaDaDecidere,
  // Closure lazy (valutata al click): l'export porta gli STESSI filtri e lo
  // stesso ordinamento della lista a video. Un file che ignora il filtro
  // attivo è un secondo elenco, e nessuno se ne accorge finché non lo apre.
  getExportParams: (fmt) => {
    const p = { formato: fmt }
    if (store.filters.motivo) p.motivo = store.filters.motivo
    if (store.filters.order_by) {
      p.order_by = store.filters.order_by
      p.order_dir = store.filters.order_dir || 'desc'
    }
    return p
  },
  // Nessun "Nuovo": una riga di questo elenco non si crea, si risolve.
  searchTableOptions: { defaultSortField: 'data', defaultSortOrder: 'desc' },
})

// --- Filtro motivo (unico filtro: la coda è già ristretta dalla vista) ---
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: motivoFilter, onChange: onMotivoChange } = bindSelect('motivo')

const motivoOptions = computed(() => [
  { value: null, label: t('vendite.fondi_fattura_da_decidere.motivo_tutti') },
  ...MOTIVI.map((m) => ({ value: m, label: motivoLabel(m) })),
])

// Decodifica fail-visible (pattern labelOrCode): un motivo che il database
// aggiungesse domani mostrerebbe il CODICE grezzo, mai la chiave i18n
// letterale — si vede che manca una traduzione, non si vede un elenco rotto.
function motivoLabel(codice) {
  return labelOrCode(t, te, `vendite.fondi_fattura_da_decidere.motivo.${codice}`, codice)
}

// ⭐ CHIAVE DI RIGA, COMPOSTA QUI. La lista non ha un id proprio: la vista è
// una UNION e le sue righe sono identificate dalla COPPIA (fattura, atto) —
// esattamente il tiebreak che il backend usa nell'ORDER BY.
// ⚠️ Che la coppia sia unica non lo dice il dato (in sviluppo l'elenco è
// vuoto: misurato, zero righe e zero atti fondo — quindi non si poteva
// verificare contando): lo dice la FORMA della vista. Una fattura compare o
// SENZA atto — i rami `senza_atto` sono mutuamente esclusivi (`utility_id`
// nullo o no) e attraversano un solo `tipo_fondo` (`F_F_ADD_ACC`) — oppure
// con i suoi atti, che hanno id distinti.
// 📌 Serve per davvero: senza `data-key` PrimeVue ripiega sull'indice di riga,
// e su un elenco che si riordina e si pagina l'indice cambia sotto le mani
// (selezione ed espansione finirebbero sulla riga sbagliata).
const righe = computed(() =>
  store.items.map((r) => ({
    ...r,
    riga_key: `${r.fattura_sorgente_id}:${r.fondo_source_id ?? 0}`,
  })),
)

// --- Apertura del documento (l'unica via d'uscita dalla riga) ---
const fatturaDrawerVisible = ref(false)
const fatturaDrawerId = ref(null)

// Scopo: apre la fattura sorgente. È il motivo per cui `fattura_sorgente_id`
//        sta a catalogo — la decisione si prende guardando il documento, non
//        la riga di elenco.
function apriFattura(event) {
  const id = event?.data?.fattura_sorgente_id
  if (!id) return
  fatturaDrawerId.value = id
  fatturaDrawerVisible.value = true
}

// Scopo: carica la lista con toast d'errore (fail-visible: lo store propaga).
async function load() {
  try {
    await store.fetchList()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  }
}

onMounted(load)
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters" :inert="perimetroBloccato">
        <div class="form-field">
          <label>{{ t('vendite.fondi_fattura_da_decidere.filtro_motivo') }}</label>
          <Select
            v-model="motivoFilter"
            :options="motivoOptions"
            option-label="label"
            option-value="value"
            @update:model-value="onMotivoChange"
          />
        </div>
      </div>
      <!-- Icone a destra, e su schermo stretto la barra le raccoglie da sé nel
           kebab: è il meccanismo standard di PageActionsBar. -->
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <!-- Colonne, ordine e visibilità dal catalogo
         `vendite.fondi_fattura_da_decidere`: qui restano solo le celle con un
         rendering proprio. Le altre (importi, date, anno/numero/serie) le rende
         il BB dal `formato` dichiarato nel seed. -->
    <ListaConfigurabile
      ref="listaRef"
      codice="vendite.fondi_fattura_da_decidere"
      data-key="riga_key"
      :rows="righe"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="apriFattura"
      @config-loaded="onConfigLoaded"
    >
      <!-- Il motivo è la colonna che si legge per prima: colore che separa
           «devo decidere» (arancio) da «qui c'è qualcosa di rotto» (rosso) —
           sono due lavori diversi, spesso di due persone diverse. -->
      <template #cell-motivo="{ data }">
        <Tag
          :value="motivoLabel(data.motivo)"
          :severity="motivoFondoDaDecidereSeverity(data.motivo)"
        />
      </template>

      <!-- ⚠️ Lo stato dell'atto è NULL per COSTRUZIONE su tre rami della vista
           su quattro (l'atto non esiste ancora). Il trattino lo dice: una cella
           bianca si legge come «dato mancante», che è un'altra cosa. -->
      <template #cell-stato_atto="{ data }">
        <span v-if="data.stato_atto">{{ data.stato_atto }}</span>
        <span v-else class="app-cella-vuota">—</span>
      </template>
      <template #cell-origine="{ data }">
        <span v-if="data.origine">{{ data.origine }}</span>
        <span v-else class="app-cella-vuota">—</span>
      </template>

      <template #empty>
        <div class="app-empty-state">
          <i class="pi pi-check-circle" />
          <p>{{ t('vendite.fondi_fattura_da_decidere.nessuna_riga') }}</p>
        </div>
      </template>
    </ListaConfigurabile>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />

    <!-- Consultazione del documento da cui nasce la riga. -->
    <FatturaDrawer
      v-model:visible="fatturaDrawerVisible"
      :fattura-id="fatturaDrawerId"
    />
  </div>
</template>

<style scoped>
.app-cella-vuota {
  color: var(--app-text-muted);
}
</style>

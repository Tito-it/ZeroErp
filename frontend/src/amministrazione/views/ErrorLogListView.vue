<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: la consultazione di `dbops.error_log` per i tecnici (pezzo E del
//        piano BE/FE dell'osservabilita'): `<ListaConfigurabile
//        codice="dbops.error_log">` con i filtri della whitelist del backend
//        (area, funzione a prefisso, codice, tx_id, date), export, e il kebab
//        di riga — «Dettaglio» (il `context` com'e'), «Giornale di questa
//        transazione» (deep-link al giornale trasversale, `?tx_id=`),
//        «Copia tx_id». Sola consultazione: niente «Nuovo», niente click di
//        riga (il dettaglio e' un'azione, e la riga ha altre due).
//
// ⚠️ `area` e' un testo LIBERO, non un select sul catalogo
//    `config.aree_funzionali`: `error_log.area` non ha FK (e' il primo
//    argomento di `fn_log_and_raise_error`) e porta valori che quel catalogo
//    non conosce — `database`, `script`, `dbops`, `backend`. Un select li
//    nasconderebbe, e con loro meta' del registro. Scostamento dal piano §4.2,
//    dichiarato nel registro del piano.
// ⚠️ Niente casella di ricerca: il backend non ha ricerca testuale — ogni
//    filtro e' esatto o a prefisso e ha il suo indice (P-3).
// ⚠️ Niente `useReadonlyMode` (tolto il 2026-10-06, Tid): dietro `adminOnly`
//    di Strumenti → Diagnostica non c'e' un livello d'area da risolvere — o
//    sei super admin, o non arrivi alla pagina. Come ProcessiAutomaticiListView.
import { ref, computed, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ErrorLogDettaglioDrawer from '../components/ErrorLogDettaglioDrawer.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useDebouncedAction } from '../../core/composables/useDebouncedAction'
import { useNotify } from '../../core/composables/useNotify'
import { useAuthStore } from '../../stores/auth'
import { useErrorLogStore } from '../stores/errorLog'
import { exportErrorLogs } from '../api/amministrazione'
import { classeErroreSeverity } from '../../core/utils/severity'
import { MANAGE_ICONS, READONLY_DOMAINS } from '../../core/constants'
import FiltroPeriodo from '../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'

const { t } = useI18n()
const store = useErrorLogStore()
const notify = useNotify()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const {
  onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm,
} = useListaConfigurabilePage(store, {
  exportFn: exportErrorLogs,
  // Il file E' la lista: filtri e ordine dalla SEDE UNICA dello store
  // (`paramsFiltro`), non ricostruiti qui — la forma con cui l'export
  // perdeva filtri per strada (catalogo BB, `useListaStoreCore`).
  getExportParams: (fmt) => ({ formato: fmt, ...store.paramsFiltro() }),
  searchTableOptions: {
    // Allineato al preset del seed (`occurred_at desc`).
    defaultSortField: 'occurred_at',
    defaultSortOrder: 'desc',
  },
})

const { bindPeriodo } = useStoreFilterBindings(store, applyFilters)
// Il periodo e' UN filtro con due estremi: un binding, un componente.
const periodo = bindPeriodo()

// I quattro filtri di testo scrivono lo store e rilanciano da pagina 1 dopo
// il debounce standard; una stringa vuota torna `null`, cosi' il core non
// manda un parametro vuoto. `Enter` applica subito.
const applicaTesto = useDebouncedAction(applyFilters, { detailed: true })
function onTestoInput(chiave, valore) {
  const pulito = (valore ?? '').trim()
  store.filters[chiave] = pulito === '' ? null : pulito
  applicaTesto.run()
}
function onTestoEnter() {
  applicaTesto.flush()
}

// --- Dettaglio ---
const dettaglioVisible = ref(false)
function apriDettaglio(riga) {
  store.rigaCorrente = riga
  dettaglioVisible.value = true
}

// --- Il ponte verso il giornale di dominio ---
// E' un'OFFERTA, non una promessa: il pulsante compare solo se chi guarda
// raggiunge l'area vendite. Sull'amministrazione (SUPER_ADMIN) e' sempre
// vero; la regola resta scritta per il giorno di un permesso «tecnici».
const giornaleRaggiungibile = computed(() => !auth.isAreaBlocked(READONLY_DOMAINS.VENDITE))
function apriGiornale(riga) {
  router.push({ name: 'strumenti-giornale', query: { tx_id: riga.tx_id } })
}

// Scopo: copia il `tx_id` negli appunti, con un toast di conferma.
async function copiaTxId(riga) {
  try {
    await navigator.clipboard.writeText(riga.tx_id)
    notify.success(t('amministrazione.error_log.tx_id_copiato'))
  } catch {
    notify.error(t('amministrazione.error_log.tx_id_non_copiato'))
  }
}

// Scopo: le azioni di riga. L'ordine e' quello dell'uso: prima il dettaglio
//        (sempre), poi il ponte, poi la copia.
function buildRowActions(data) {
  return [
    {
      key: 'dettaglio',
      label: t('amministrazione.error_log.azione_dettaglio'),
      icon: MANAGE_ICONS.INSPECT,
      command: () => apriDettaglio(data),
    },
    {
      key: 'giornale',
      label: t('amministrazione.error_log.azione_giornale'),
      icon: MANAGE_ICONS.GIORNALE,
      visible: giornaleRaggiungibile.value && !!data.tx_id,
      command: () => apriGiornale(data),
    },
    {
      key: 'copia-tx-id',
      label: t('amministrazione.error_log.azione_copia_tx_id'),
      icon: MANAGE_ICONS.COPIA,
      visible: !!data.tx_id,
      command: () => copiaTxId(data),
    },
  ]
}

// Scopo: il deep-link `?tx_id=` (dal giornale trasversale, o incollato):
//        scrive il filtro e ricarica. Idempotente e in `onActivated`, non in
//        `onMounted`: sotto KeepAlive il secondo arrivo non rimonta
//        (`feedback_keepalive_onactivated`). Senza query e' un semplice
//        rinfresco della lista.
// ⚠️ La query si PULISCE dopo l'uso (`router.replace`, come `?open=` dei
//    lotti): lasciata li', ri-forzerebbe il filtro a ogni ritorno sulla
//    scheda anche dopo che l'operatore l'ha tolto a mano — `?tx_id=` e' un
//    ingresso, non lo specchio dello stato (stessa regola di `useTabDaQuery`).
function applicaDeepLink() {
  const txId = typeof route.query.tx_id === 'string' ? route.query.tx_id.trim() : ''
  if (!txId) {
    store.fetchList()
    return
  }
  const query = { ...route.query }
  delete query.tx_id
  router.replace({ query })
  store.filters.tx_id = txId
  // Un filo attraversa qualunque data: il floor temporale lo nasconderebbe.
  store.filters.data_da = null
  applyFilters()
}

onActivated(applicaDeepLink)
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <InputText
          class="app-filter-w-sm"
          :model-value="store.filters.area ?? ''"
          :placeholder="t('amministrazione.error_log.col_area')"
          @update:model-value="(v) => onTestoInput('area', v)"
          @keyup.enter="onTestoEnter"
        />
        <InputText
          :model-value="store.filters.function_name ?? ''"
          :placeholder="t('amministrazione.error_log.filtro_funzione')"
          @update:model-value="(v) => onTestoInput('function_name', v)"
          @keyup.enter="onTestoEnter"
        />
        <InputText
          :model-value="store.filters.codice ?? ''"
          :placeholder="t('amministrazione.error_log.col_codice')"
          @update:model-value="(v) => onTestoInput('codice', v)"
          @keyup.enter="onTestoEnter"
        />
        <InputText
          :model-value="store.filters.tx_id ?? ''"
          class="app-filter-w-lg"
          :placeholder="t('amministrazione.error_log.col_tx_id')"
          @update:model-value="(v) => onTestoInput('tx_id', v)"
          @keyup.enter="onTestoEnter"
        />
        <FiltroPeriodo :periodo="periodo" />
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="dbops.error_log"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @config-loaded="onConfigLoaded"
    >
      <!-- `occurred_at` non ha slot: il seed dichiara `datetime_short` e il
           formatter del catalogo la rende gia' cosi'. -->
      <template #cell-classe="{ data }">
        <Tag v-if="data.classe" :value="data.classe" :severity="classeErroreSeverity(data.classe)" />
        <span v-else>—</span>
      </template>
      <template #cell-function_name="{ data }">
        <span class="app-mono app-error-log-mono">{{ data.function_name }}</span>
      </template>
      <template #cell-codice="{ data }">
        <span class="app-mono app-error-log-mono">{{ data.codice }}</span>
      </template>
      <template #cell-tx_id="{ data }">
        <span class="app-mono app-error-log-mono">{{ data.tx_id }}</span>
      </template>
      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </ListaConfigurabile>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />

    <ErrorLogDettaglioDrawer
      v-model:visible="dettaglioVisible"
      :riga="store.rigaCorrente"
    />
  </div>
</template>

<style scoped>
.app-error-log-mono {
  font-size: 0.85em;
}
</style>

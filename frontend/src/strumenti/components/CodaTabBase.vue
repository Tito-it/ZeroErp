<!--
  Copyright (C) 2026 Michele Carlo Titini

  This program is free software: you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation, either version 3 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program.  If not, see <https://www.gnu.org/licenses/>.
-->
<script setup>
// Scopo: LO SCHELETRO comune delle due schede «Code di lavoro» (lavori e
//        stampa): toolbar filtri, stato del worker, lista configurabile,
//        caricamento con refresh periodico silenzioso, colonna «stato» con la
//        rotellina sulle righe vive, empty state.
//
// ⭐ Estratto il 2026-08-27 (ok Tid). Le due schede erano gemelle al 94% —
//    208 righe divergenti su 222 solo per i nomi — e la duplicazione non era
//    teorica: nella stessa giornata la stessa identica modifica e' stata fatta
//    TRE volte su entrambe (il refresh silenzioso, `useRefreshPeriodico`, la
//    rotellina con il suo import e il suo stile). La terza volta e' il momento
//    in cui si smette di copiare.
//
// ⚠️ Quello che le due schede hanno DAVVERO di diverso resta fuori di qui, e
//    non e' poco: le colonne di dominio (tipo job / fattura, emittente,
//    operatore, esito), le azioni di riga con il drawer di dettaglio (solo
//    lavori: la stampa non ha azioni, P-4 — il drainer ritenta da solo) e il
//    click sulla riga. Arrivano per SLOT e per prop, non sono stati piegati a
//    un denominatore comune: un componente base che prova a contenere anche le
//    differenze diventa un albero di `v-if` peggiore delle due copie.
//
// ⚠️ Le colonne di dominio si passano come slot `#cell-<codice>` sul CALLER e
//    arrivano qui: sono inoltrate una per una a `<ListaConfigurabile>`. Fanno
//    eccezione `cell-stato` e `empty`, che questo componente rende da se'
//    perche' sono la parte identica.
import { computed, onMounted, ref, useSlots } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useNotify } from '../../core/composables/useNotify'
import { useRefreshPeriodico } from '../../core/composables/useRefreshPeriodico'
import { rigaCodaViva } from '../../core/composables/useQueueCountsPolling'
import { extractApiError } from '../../core/utils/apiError'
import { useCodaFiltri } from '../composables/useCodaFiltri'
import CodaFiltriToolbar from './CodaFiltriToolbar.vue'
import CodaWorkerStato from './CodaWorkerStato.vue'

const props = defineProps({
  // Store Pinia della coda (interfaccia useSearchTable-compatibile).
  store: { type: Object, required: true },
  // Codice della lista configurabile a catalogo (`dbops.coda_lavori`, …).
  codice: { type: String, required: true },
  // Chiave della coda per lo stato del worker (`coda_lavori` / `coda_stampa`).
  coda: { type: String, required: true },
  // Vocabolario stato→severity della coda: alimenta le opzioni del filtro.
  statoMap: { type: Object, required: true },
  // Risolutore del colore del Tag di stato.
  statoSeverity: { type: Function, required: true },
  emptyKey: { type: String, required: true },
  emptyIcon: { type: String, default: 'pi pi-inbox' },
  // Loading AGGIUNTIVO del caller (un'azione di riga in corso), sommato a
  // quello della lista.
  extraLoading: { type: Boolean, default: false },
  // Azioni di riga: `null` = la coda non ne ha e la colonna non compare.
  buildRowActions: { type: Function, default: null },
  // Click sulla riga: `null` = riga non cliccabile.
  onRowClick: { type: Function, default: null },
})

const { t } = useI18n()
const notify = useNotify()
const slots = useSlots()

// ⚠️ Alias locale dello store, e non e' cosmetico: `props.store` e' uno store
//    Pinia, cioe' un oggetto che ESISTE per essere mutato (i filtri sono suoi).
//    Scriverci sopra come `props.store.filters…` accende pero'
//    `vue/no-mutating-props`, che ha ragione in generale — un prop non si
//    tocca. L'alias dice a chi legge che la mutazione e' voluta e riguarda lo
//    store, non la prop.
// ⚠️ La prop non e' reattivamente sostituibile: ogni scheda monta il proprio
//    store una volta e non lo cambia. Se un domani lo cambiasse, questo alias
//    resterebbe indietro — allora servirebbe un `computed`.
const store = props.store

const { statoOptions, ambitoOptions } = useCodaFiltri(props.statoMap)

// Stato worker: ricaricato insieme alla lista, così «Ricarica» aggiorna anche
// l'ultimo giro (altrimenti resterebbe fermo al primo ingresso nel tab).
const workerStatoRef = ref(null)

// Scopo: fetch con refresh worker e cattura errore (fail-visible: una tabella
//        vuota per errore non deve sembrare «coda vuota»).
// `silent` = giro di sfondo del refresh periodico: aggiorna i dati SENZA
// accendere la maschera di caricamento del DataTable (che lampeggerebbe ogni
// quindici secondi sotto gli occhi di chi legge) e SENZA aprire un toast su un
// colpo a vuoto. Il «Ricarica» a mano resta rumoroso: lì l'operatore ha
// chiesto una risposta e deve averla, anche quando è un errore.
async function load({ silent = false } = {}) {
  workerStatoRef.value?.refresh()
  try {
    await store.fetchList({ silent })
  } catch (err) {
    if (!silent) notify.error(extractApiError(err, t('common.error')))
  }
}

const {
  onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, { onReload: load })

// Cambio filtro toolbar: si riparte da pagina 1.
function onFilterChange() {
  store.filters.offset = 0
  load()
}

// Primo caricamento al mount: con <Tabs lazy> ogni attivazione del tab è un
// MOUNT (pattern ResiCodaTable); la freshness al rientro rotta la gestisce
// l'onActivated di useSearchTable dentro lo scaffolding.
onMounted(load)

// ⛔ Senza questo la scheda era una FOTOGRAFIA: caricava all'apertura e al
// «Ricarica», e nient'altro — mentre il badge della topbar, un piano più su, si
// aggiornava da solo ogni 60s. Due letture della stessa coda, una viva e una
// congelata. Rilievo in-app di Tid, 2026-08-27: «il lavoro in esecuzione non si
// vede, si vede solo quando ha finito».
// ⚠️ Il ciclo di vita (tab del browser, scheda KeepAlive, smontaggio) è tutto
// dentro il BB: qui non c'è niente da ricordarsi di fermare o riprendere.
useRefreshPeriodico(() => load({ silent: true }))

// Slot di dominio da inoltrare a `<ListaConfigurabile>`.
// ⚠️ Si escludono quelli che questo componente gestisce DA SÉ: inoltrarli
//    significherebbe dichiarare due volte lo stesso nome sullo stesso
//    componente (`cell-stato`, `empty`, `actions`) oppure renderli due volte
//    (`extra`, che vive fuori dalla lista). Oggi nessun caller li passa e non
//    si vedrebbe niente: e' un presidio per il prossimo, non una correzione.
const SLOT_PROPRI = ['cell-stato', 'empty', 'actions', 'extra']
const slotDaInoltrare = computed(
  () => Object.keys(slots).filter((n) => !SLOT_PROPRI.includes(n)),
)

// Il caller ricarica dopo un'azione di riga (annulla / requeue / dettaglio).
defineExpose({ load })
</script>

<template>
  <div class="app-tab-content">
    <CodaFiltriToolbar
      :filtri="store.filters"
      :stato-options="statoOptions"
      :ambito-options="ambitoOptions"
      :page-actions="pageActions"
      :filtri-inerti="perimetroBloccato"
      @change="onFilterChange"
    >
      <template #actions-suffix>
        <ListaConfigStatusTag :dirty="dirty" />
      </template>
    </CodaFiltriToolbar>

    <!-- Liveness del drainer: dice se la coda sta girando o è ferma. Il
         conteggio delle sue esecuzioni è volutamente assente (un poller a
         1/min produce numeri enormi che non informano su nulla). -->
    <CodaWorkerStato ref="workerStatoRef" :coda="coda" />

    <ListaConfigurabile
      ref="listaRef"
      :codice="codice"
      data-key="id"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading || extraLoading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="(data) => onRowClick?.(data)"
      @config-loaded="onConfigLoaded"
    >
      <!-- Colonne di dominio del caller, inoltrate una per una. -->
      <template v-for="nome in slotDaInoltrare" #[nome]="slotProps" :key="nome">
        <slot :name="nome" v-bind="slotProps" />
      </template>

      <!-- ⭐ La rotellina sulla riga VIVA: è lo stesso segnale del pulsante che
           l'ha accodata («Fattura adesso», «Rendi definitivo il mese»), e dice
           la stessa cosa — questo lavoro non è finito.
           ⚠️ Il predicato è `rigaCodaViva`, cioè PENDING **o** IN_CORSO, e non
           il solo IN_CORSO: i drainer sono oneshot e quella finestra dura
           millisecondi, quindi una rotellina legata a IN_CORSO sarebbe una
           rotellina che nessuno vede mai. Ciò che l'operatore attraversa è
           l'attesa in PENDING fino al tick del worker. -->
      <template #cell-stato="{ data }">
        <span class="app-cella-con-spinner">
          <i
            v-if="rigaCodaViva(data.stato)"
            class="pi pi-spin pi-spinner app-spinner-in-corso"
            v-tooltip.right="t('strumenti.code.riga_viva_hint')"
            :aria-label="t('strumenti.code.riga_viva_hint')"
          />
          <Tag :value="data.stato" :severity="statoSeverity(data.stato)" />
        </span>
      </template>

      <template v-if="buildRowActions" #actions="{ data, compact }">
        <RowActionsMenu
          :row="data"
          :actions="buildRowActions(data)"
          :force-compact="compact"
        />
      </template>

      <template #empty>
        <div class="app-empty-state">
          <i :class="emptyIcon" />
          <p>{{ t(emptyKey) }}</p>
        </div>
      </template>
    </ListaConfigurabile>

    <!-- Pannelli del caller (drawer di dettaglio, dialog). -->
    <slot name="extra" />
  </div>
</template>

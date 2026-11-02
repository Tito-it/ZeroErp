<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista dei TITOLI IVA di un soggetto (I7 / D10), aperta dalla sezione
// «Titoli IVA» del `SoggettoDrawer`. Apre il drawer del singolo titolo.
//
// ⭐ PORTATA SULLO STANDARD IL 2026-09-02 (rilievo di Tid in collaudo). Prima
//   era una `<ListaConfigurabile>` montata a mano, con le righe in due `ref`
//   locali: niente paginazione, niente «Personalizza colonne», niente export.
//   Cioe' fuori dallo standard delle altre quaranta liste — ma senza che
//   niente lo dicesse, che e' il modo in cui una schermata resta indietro.
//   Ora usa lo stesso scaffolding dei tab-lista dell'emittente
//   (`useDrawerTabLista` + `<DrawerTabLista>`), e le tre cose arrivano da li'.
//
// ⛔ NON adotta `useSoggettoRuoloCollection`, ed e' una non-adozione MOTIVATA
//   (stessa forma con cui quel composable dichiara di non coprire
//   `IndirizziSoggettoDrawer`): quel backbone possiede la macchina a stati di un
//   form INLINE a card. Un titolo ha figli — le righe di ambito, e col registro
//   dei movimenti ne avra' due — quindi vuole un drawer suo, e qui non resta
//   nessuno stato di form da condividere. Riusarlo vorrebbe dire tenere una
//   `formMode` che nessuno accende.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import {
  deleteSoggettoTitoloIva,
  exportSoggettoTitoliIva,
} from '../api/anagrafiche'
import { useSoggettoTitoliIvaStore } from '../stores/soggettoTitoliIva'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import TitoloIvaDrawer from './TitoloIvaDrawer.vue'
import Tag from 'primevue/tag'

const { t } = useI18n()
const { execute } = useApiHandler()
const isReadonly = useInjectReadonly()
const { confirmDelete } = useConfirmAction()
const store = useSoggettoTitoliIvaStore()

const props = defineProps({
  visible: { type: Boolean, default: false },
  soggettoId: { type: String, default: null },
  soggettoNome: { type: String, default: '' },
})
const emit = defineEmits(['update:visible', 'saved'])

const titoloDrawerVisible = ref(false)
const titoloSelezionatoId = ref(null)

// ⚠️ `parentId` porta l'id SOLO a drawer aperto, e il `null` non e' un
//    dettaglio: e' quello che dice al BB di chiamare `store.reset()` alla
//    chiusura. Senza, la lista del soggetto precedente resterebbe in memoria e
//    lampeggerebbe sotto il prossimo che si apre — dati veri di un padre
//    sbagliato, che e' il difetto che non fallisce.
// ⭐ E la guardia di versione che c'era qui a mano (`useFetchVersion`) non
//    serve piu': `useListaEmptyStateFetch` invalida da se' le fetch in volo.
const {
  onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm, reloadAll,
} = useDrawerTabLista(store, {
  parentId: () => (props.visible ? props.soggettoId : null),
  parentField: 'soggettoId',
  exportFn: (params) => exportSoggettoTitoliIva(props.soggettoId, params),
  // L'export segue la lista a video — ordinamento compreso — dalla sede unica
  // dello store (`paramsFiltro`), non da un ripiego ricopiato qui.
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
  newTooltipKey: 'anagrafiche.titoli_iva.aggiungi_titolo',
  onNew: () => apriTitolo(null),
})

// ⚠️ Le azioni di pagina arrivano TUTTE dallo scaffolding — reload,
//    «Personalizza colonne», «Esporta», «Nuovo» — e non si riscrivono qui, o
//    divergono dalle altre quaranta liste.
// ⛔ E in sola lettura il «Nuovo» NON si filtra a mano: lo scaffolding lo marca
//    `hideWhenReadonly` e `PageActionsBar` lo onora. Un secondo filtro qui
//    sarebbe una seconda regola sullo stesso invariante, e la copia rimasta
//    indietro e' il modo in cui il pulsante ricompare dove non deve.

function apriTitolo(id) {
  titoloSelezionatoId.value = id
  titoloDrawerVisible.value = true
}

// ⚠️ `reloadAll()` non e' awaitable (lo scaffolding non restituisce la
//    Promise), quindi non si finge che lo sia: si ricarica e si avvisa il
//    padre, che ricarica il suo. Un `await` qui darebbe l'impressione di un
//    ordine che non c'e'.
function onTitoloSaved() {
  reloadAll()
  emit('saved')
}

// ⚠️ La cancellazione la rifiuta il BE se il titolo ha gia' consumato plafond
//   (Q6): un registro e' la traccia di cio' che e' stato consumato. Qui non si
//   ri-deriva la regola — si chiede conferma e si lascia parlare il backend, che
//   dice anche COSA FARE al posto («si disattiva»).
function onDelete(riga) {
  confirmDelete(descriviTitolo(riga), async () => {
    const res = await execute(
      () => deleteSoggettoTitoloIva(props.soggettoId, riga.id),
      { successMessage: t('anagrafiche.titoli_iva.titolo_eliminato') },
    )
    if (res !== null) onTitoloSaved()
  })
}

function descriviTitolo(r) {
  return `${r.tipo_descrizione} — ${r.emittente_ragione_sociale}`
}

// Scopo: le azioni di riga, nella forma che `RowActionsMenu` si aspetta.
// ⭐ Prima era un `<Button>` nudo dentro una `<Column v-if="!isReadonly">`:
//    fuori standard (`frontend-standards` §«Colonna azioni di riga») e — piu'
//    concretamente — invisibile al generatore del seed, che riconosce la
//    colonna azioni dal suo header. E' il motivo per cui la riga a catalogo
//    mancava, ed e' arrivata solo con la richiesta DB-1.
// ⚠️ `visible` invece di un `v-if` sulla colonna: la colonna resta a catalogo e
//    il kebab sparisce da se' in sola lettura.
function buildRowActions(riga) {
  return [{
    key: 'elimina',
    label: t('common.delete'),
    icon: MANAGE_ICONS.DELETE,
    severity: 'danger',
    visible: !isReadonly.value,
    allowWhenInactive: true,
    command: () => onDelete(riga),
  }]
}

// Severity del residuo: sotto zero e' uno sfondamento, e si vede (Q4).
function residuoSeverity(r) {
  if (r.residuo == null) return 'secondary'
  return Number(r.residuo) < 0 ? 'danger' : 'success'
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :proteggi-corpo="false"
    :title="t('anagrafiche.titoli_iva.titolo_lista')"
    :icon="MANAGE_ICONS.TITOLI_IVA"
    :action="soggettoNome"
    :width="DRAWER_WIDTH.WIDE"
    footer="chiudi"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <DrawerTabLista
      ref="listaRef"
      codice="anagrafiche.soggetto_titoli_iva"
      :store="store"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      :page-actions="pageActions"
      :dirty="dirty"
      :perimetro-bloccato="perimetroBloccato"
      @page="onPage"
      @sort="onSort"
      @row-click="apriTitolo($event.id)"
      @config-loaded="onConfigLoaded"
    >
      <!-- Colonna composta da DUE campi: non ha un `campo_sorgente` e il
           catalogo la dichiara calcolata. -->
      <template #cell-validita="{ data }">
        {{ displayDate(data.valido_dal) }} —
        {{ data.valido_al ? displayDate(data.valido_al) : t('anagrafiche.titoli_iva.senza_scadenza') }}
      </template>
      <template #cell-residuo="{ data }">
        <!-- Il residuo esiste solo dove esiste un tetto: sui tipi senza
             plafond non si mostra uno zero, che sembrerebbe «esaurito». -->
        <Tag v-if="data.residuo != null" :value="formatCurrency(data.residuo)"
          :severity="residuoSeverity(data)" />
        <span v-else class="app-text-muted">—</span>
      </template>
      <template #cell-stato="{ data }">
        <Tag v-if="!data.attivo" :value="t('anagrafiche.titoli_iva.tag_non_attivo')" severity="secondary" />
        <!-- Q2: RISTRETTO senza righe non copre nessuna merce. Lo DICHIARA
             il backend (`ambito_incompleto`): qui non si ri-deriva. -->
        <Tag v-else-if="data.ambito_incompleto"
          :value="t('anagrafiche.titoli_iva.tag_ambito_incompleto')" severity="warn" />
        <Tag v-else :value="t('common.attivo')" severity="success" />
      </template>
      <template #actions="{ data }">
        <RowActionsMenu
          :row="data"
          :actions="buildRowActions(data)" />
      </template>
    </DrawerTabLista>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @confirm="onExportConfirm" />

    <TitoloIvaDrawer
      v-model:visible="titoloDrawerVisible"
      :soggetto-id="soggettoId"
      :titolo-id="titoloSelezionatoId"
      @saved="onTitoloSaved" />
  </AppDrawer>
</template>

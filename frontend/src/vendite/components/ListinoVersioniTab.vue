<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Il tab «Versioni» del drawer listino: la lista configurabile
//        `vendite.listini_versioni` (112) con `useDrawerTabLista` +
//        `<DrawerTabLista>`, la ricerca, «Nuova versione» fra le azioni di
//        pagina e il ciclo di vita della versione nel kebab di riga (attiva,
//        chiudi, clona, gestisci righe, elimina).
//        ⭐ Nato il 2026-10-31 (brief-db-liste-datatable-grezze-secondo-giro
//        riga 5, B3+B4 di Tid): fino a quel giorno le versioni erano una
//        `DataTable` nella riga espansa della lista listini, che caricava la
//        collezione intera di ogni listino della pagina. Azioni, dialog e
//        cella dello stato sono SPOSTATI da `ListiniSearchTable`, non copiati.
//        La colonna `giorni_alla_scadenza` e' la regola del DB
//        (`vendite.fn_listini_in_scadenza_senza_successore`): vuota = non in
//        scadenza.
//
// ⚠️ I drawer delle righe, della nuova versione e del clone vivono nella
//    vista (`ListiniView`): il tab li chiede con un evento, e la vista
//    ricarica il tab con `reload()` quando salvano.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'

import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useAzioneRiga } from '../../core/composables/useAzioneRiga'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS } from '../../core/constants'
import { passaggioPermesso } from '../../core/utils/azioniPermesse'
import { displayDate } from '../../core/utils/date'
import { statoVersioneListinoSeverity } from '../../core/utils/severity'
import { deleteVersione } from '../api/listini'
import { AZIONE_RIGA_VERSIONE_LISTINO, PASSAGGI_VERSIONE_LISTINO } from '../constants'
import { useListinoVersioniStore } from '../stores/listinoVersioni'
import AttivaVersioneDialog from './AttivaVersioneDialog.vue'
import ChiudiVersioneDialog from './ChiudiVersioneDialog.vue'

const props = defineProps({
  // Il listino del drawer: id per il path, il resto per i drawer della vista.
  listino: { type: Object, default: null },
  // Il tab e' aperto e visibile: senza, la lista si azzera e non legge.
  attivo: { type: Boolean, default: false },
})
// `cambiate`: una versione e' cambiata da QUI (attiva, chiudi, elimina): la
// vista rinfresca la lista listini (conteggio versioni, badge delle scadenze).
const emit = defineEmits(['open-righe', 'open-nuova-versione', 'open-clona-versione', 'cambiate'])

const { t } = useI18n()
const store = useListinoVersioniStore()
const { execute } = useApiHandler()
const { confirmDelete } = useConfirmAction()
// ⚠️ Il drawer non protegge il corpo di questo tab (la lista si consulta
//    anche in sola lettura): i verbi si nascondono qui, resta «Gestisci righe».
const isReadonly = useInjectReadonly()

// ⚠️ `parentId` porta l'id SOLO a tab aperto: il `null` alla chiusura dice al
//    BB di chiamare `store.reset()`, o le versioni del listino precedente
//    lampeggerebbero sotto il prossimo.
const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato, reloadAll,
} = useDrawerTabLista(store, {
  parentId: () => (props.attivo ? props.listino?.id ?? null : null),
  parentField: 'listinoId',
  newTooltipKey: 'vendite.listini.nuova_versione',
  onNew: () => emit('open-nuova-versione', props.listino),
})

// ⭐ «Attiva» dal modello del documento (giro 12, FE-L1 di
//    brief-modello-documento-vendita §16.5):
//    - PERMESSO ⇒ nascondi: la voce c'è solo se il passaggio è tra quelli che
//      l'operatore può fare dallo stato della versione (`azioni_permesse`, dal
//      lettore del DB che applica l'azione `attiva_listino`; BB
//      `passaggioPermesso`, fail-closed: un campo assente non apre niente).
//    - STATO ⇒ spegni col motivo: il motivo è il primo della stessa `fn_check`
//      con cui il verbo rifiuta, nelle colonne che il registro delle azioni di
//      riga dichiara per `AZIONE_RIGA_VERSIONE_LISTINO.ATTIVA` (BB `useAzioneRiga`).
// ⭐ «Elimina» e «Chiudi» allo stesso modo (§16.13 FE-E1, §16.16 FE-C1): spenti
//    col motivo dal registro. «Clona» non ha motivo: si clona da qualunque
//    stato (C-1 = a), e la voce è sempre accesa.
const attivazione = useAzioneRiga(AZIONE_RIGA_VERSIONE_LISTINO.ATTIVA)
const eliminazione = useAzioneRiga(AZIONE_RIGA_VERSIONE_LISTINO.ELIMINA)
const chiusura = useAzioneRiga(AZIONE_RIGA_VERSIONE_LISTINO.CHIUDI)

// Dialog conferma attivazione (D3, preview auto-close col dry_run) e
// programma chiusura (PATCH valido_al su ATTIVA). Dichiarati prima delle
// funzioni che li usano (TDZ).
const attivaDialogVisible = ref(false)
const chiusuraDialogVisible = ref(false)
const versioneDialog = ref(null)

function apriAttiva(ver) {
  versioneDialog.value = ver
  attivaDialogVisible.value = true
}

function apriChiusura(ver) {
  versioneDialog.value = ver
  chiusuraDialogVisible.value = true
}

// Scopo: dopo un verbo fatto da qui, la lista si rilegge e la vista lo sa.
//        ⚠️ `reloadAll()` non e' awaitable.
function cambiata() {
  reloadAll()
  emit('cambiate')
}

// O2: elimina una versione in stato BOZZA con conferma utente (il verbo del DB
// cancella anche righe e componenti, e rifiuta col suo codice).
function onEliminaVersione(ver) {
  confirmDelete(ver.codice_versione, async () => {
    const result = await execute(
      () => deleteVersione(props.listino.id, ver.id),
      { successMessage: t('vendite.listini.versione_eliminata') },
    )
    if (result !== null) cambiata()
  })
}

// Scopo: azioni di riga della versione, secondo lo stato del DATABASE (giro
//        12, FE-L2): fra la fine e il passaggio del job una versione è ATTIVA
//        con la chiusura programmata, e si mostra così.
function azioniVersione(ver) {
  return [
    {
      key: 'attiva',
      label: t('vendite.listini.attiva'),
      icon: MANAGE_ICONS.PUBLISH,
      severity: 'primary',
      visible: !isReadonly.value && passaggioPermesso(ver, PASSAGGI_VERSIONE_LISTINO.ATTIVA),
      disabled: attivazione.bloccata(ver),
      tooltip: attivazione.motivo(ver),
      command: () => apriAttiva(ver),
    },
    {
      key: 'chiudi',
      label: t('vendite.listini.chiudi'),
      icon: MANAGE_ICONS.CLOSE,
      severity: 'warn',
      visible: !isReadonly.value,
      disabled: chiusura.bloccata(ver),
      tooltip: chiusura.motivo(ver),
      command: () => apriChiusura(ver),
    },
    {
      key: 'clona',
      label: t('vendite.listini.clona_versione'),
      icon: MANAGE_ICONS.CLONE,
      visible: !isReadonly.value,
      command: () => emit('open-clona-versione', ver, props.listino),
    },
    {
      key: 'gestisci-righe',
      label: t('vendite.listini.gestisci_righe'),
      icon: MANAGE_ICONS.RIGHE,
      command: () => emit('open-righe', ver, props.listino),
    },
    {
      key: 'elimina-versione',
      label: t('vendite.listini.elimina_versione'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: !isReadonly.value,
      disabled: eliminazione.bloccata(ver),
      tooltip: eliminazione.motivo(ver),
      command: () => onEliminaVersione(ver),
    },
  ]
}

// La vista ricarica il tab quando salvano i suoi drawer (righe, nuova, clone).
defineExpose({ reload: reloadAll })
</script>

<template>
  <DrawerTabLista
    ref="listaRef"
    codice="vendite.listini_versioni"
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
    @row-click="(ver) => emit('open-righe', ver, listino)"
    @config-loaded="onConfigLoaded"
  >
    <template #filtri-sempre>
      <InputText v-model="searchText" class="app-filter-w-lg" :placeholder="t('common.search')" />
    </template>
    <template #cell-stato="{ data: ver }">
      <Tag :value="ver.stato" :severity="statoVersioneListinoSeverity(ver.stato)" />
      <!-- La chiusura programmata la dice il backend (ATTIVA con la fine
           scritta): il job la chiude quando la fine passa. -->
      <i v-if="ver.chiusura_programmata" :class="MANAGE_ICONS.CLOSE" class="ml-05 app-text-muted"
        v-tooltip.top="t('vendite.listini.chiusura_programmata_al', { data: displayDate(ver.valido_al) })" />
    </template>
    <template #actions="{ data: ver }">
      <RowActionsMenu :row="ver" :actions="azioniVersione(ver)" />
    </template>
  </DrawerTabLista>

  <AttivaVersioneDialog
    :visible="attivaDialogVisible"
    @update:visible="(v) => (attivaDialogVisible = v)"
    :listino-id="listino?.id ?? null"
    :versione="versioneDialog"
    @confirmed="cambiata"
  />

  <ChiudiVersioneDialog
    :visible="chiusuraDialogVisible"
    @update:visible="(v) => (chiusuraDialogVisible = v)"
    :listino-id="listino?.id ?? null"
    :versione="versioneDialog"
    @saved="cambiata"
  />
</template>

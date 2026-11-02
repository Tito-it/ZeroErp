<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL PIANO di un inventario — che cosa la registrazione scrivera',
//        posizione per posizione: contata, a sistema, differenza, esito. In un
//        dialog, sulla lista configurabile `magazzino.inventario_piano` (72).
//
// ⭐ E' LA FOTOGRAFIA CONTRO CUI SI CONFERMA (D-L2-n, Q-5): si apre DA SOLA
//    dopo un `CONFIRM` riuscito — sempre — e dal pulsante «Piano» in ogni
//    stato. In `DRAFT` e' un'anteprima; il DB non mette un vincolo di stato
//    sulla funzione, e qui non se ne inventa uno.
//
// ⭐ Le due righe che contano si VEDONO: `NON_CONTATA` (arancio — a registro
//    c'e' merce che il conteggio non ha nominato: resta com'era, ed e' il caso
//    di Tid) e `NON_POSTABILE` (rosso — la riga non passa la check, e finche'
//    c'e' la registrazione rifiuta TUTTO), col motivo dalla coppia
//    `posting_blocco_reason` / `_reason_key` che il piano porta in riga
//    (famiglia «riga» di api.md §Capability): la STESSA check della
//    primitiva, quindi tooltip e rifiuto non possono divergere.
//
// ⚠️ Lista in un dialog: blocco ad altezza definita (`app-dialog-lista`) e
//    store a dieci righe, col preset a catalogo che dice lo stesso numero
//    (frontend-standards §«Dialog con una lista dentro»).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'

import AppDialog from '../../core/components/AppDialog.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { bloccoAttivo, motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
import { STATUS_ICONS } from '../../core/constants'
import { esitoPianoSeverity } from '../../core/utils/severity'
import { exportPiano } from '../api/magazzino'
import { useEtichetteMagazzino } from '../etichette'
import { useInventarioPianoStore } from '../stores/inventarioPiano'

const props = defineProps({
  visible: { type: Boolean, default: false },
  inventarioId: { type: [Number, null], default: null },
  // Il riepilogo del piano dal dettaglio del documento (`piano_riepilogo`):
  // la riga di sintesi sopra la lista.
  riepilogo: { type: [Object, null], default: null },
})
const emit = defineEmits(['update:visible'])

const { t, te } = useI18n()
const { esitoPiano } = useEtichetteMagazzino()
const store = useInventarioPianoStore()

// ⭐ Il «padre» e' l'inventario A DIALOG APERTO: `null` alla chiusura, che e'
//    quello che dice allo scaffolding di azzerare lo store — il piano del
//    documento precedente non lampeggia sotto il prossimo.
const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm,
} = useDrawerTabLista(store, {
  parentId: () => (props.visible ? props.inventarioId : null),
  parentField: 'inventarioId',
  exportFn: (params) => exportPiano(props.inventarioId, params),
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
})

// La frase di sintesi: «N con differenza · M invariate · K non contate · J non
// registrabili». ⚠️ Solo se il dettaglio l'ha portata: senza, niente frase —
// non uno zero inventato.
const sintesi = computed(() => {
  const r = props.riepilogo
  if (!r) return null
  return t('magazzino.piano.riepilogo', {
    con_delta: r.n_con_delta ?? 0,
    invariate: r.n_invariate ?? 0,
    non_contate: r.n_non_contate ?? 0,
    non_postabili: r.n_non_postabili ?? 0,
  })
})

// Se ci sono righe NON registrabili la registrazione rifiutera' TUTTO: lo si
// dice in cima, non lo si lascia scoprire dal rifiuto.
const haNonPostabili = computed(() => Number(props.riepilogo?.n_non_postabili ?? 0) > 0)
</script>

<template>
  <!-- conferma-uscita: nessuna — l'unico campo e' la ricerca nel piano: filtrare e' leggere, uscendo non si perde niente (D-14) -->
  <AppDialog
    :visible="visible"
    :header="t('magazzino.piano.titolo')"
    width="xl"
    close-only
    @update:visible="(v) => emit('update:visible', v)"
  >
    <Message severity="info" :closable="false" size="small">
      {{ t('magazzino.piano.aiuto') }}
      <template v-if="sintesi"> {{ sintesi }}</template>
    </Message>
    <Message v-if="haNonPostabili" severity="error" :closable="false" size="small">
      {{ t('magazzino.piano.non_postabili_avviso') }}
    </Message>

    <!-- ⛔ «Non sono riuscito a leggere» non e' «non c'e' niente da scrivere». -->
    <Message v-if="store.erroreCaricamento" severity="warn" :closable="false" size="small">
      {{ t('magazzino.piano.non_letto') }}
    </Message>

    <DrawerTabLista
      ref="listaRef"
      class="app-dialog-lista"
      codice="magazzino.inventario_piano"
      data-key="chiave_riga"
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
      @config-loaded="onConfigLoaded"
    >
      <!-- La ricerca: colonne dal catalogo (`ricerca_full`), sotto 3 caratteri
           il termine non filtra; l'export porta la stessa `search`. -->
      <template #filtri-sempre>
        <InputText
          v-model="searchText"
          class="app-filter-w-lg"
          :placeholder="t('common.search')"
        />
      </template>

      <template #empty>
        <div v-if="!store.erroreCaricamento" class="app-empty-state">
          <i :class="STATUS_ICONS.VUOTO" />
          <p>{{ t('magazzino.piano.nessuna_riga') }}</p>
        </div>
      </template>

      <!-- L'esito: Tag col colore della mappa; su NON_POSTABILE il motivo
           nel tooltip (prefisso `posting_blocco`, BB `bloccoMotivo`). -->
      <template #cell-esito="{ data }">
        <Tag
          :value="esitoPiano(data.esito)"
          :severity="esitoPianoSeverity(data.esito)"
          v-tooltip.bottom="bloccoAttivo(data, 'posting_blocco')
            ? motivoBloccoRiga(t, te, data, 'posting_blocco')
            : undefined"
        />
      </template>
    </DrawerTabLista>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />
  </AppDialog>
</template>

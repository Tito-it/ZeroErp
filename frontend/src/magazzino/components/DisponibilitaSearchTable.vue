<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA DISPONIBILITA' — una lista configurabile per le due schede della
//        vista: per (articolo, magazzino) su `vw_disponibilita` (lista 75) e
//        per articolo, somma sui magazzini visibili (lista 76). La scheda la
//        dice la prop: stesso componente, due store, due cataloghi di colonne.
//
// ⭐ `disponibile = giacenza + bloccata` — la somma, mai «meno»: `bloccata` e'
//    NEGATIVA per costruzione (la somma firmata degli attesi APERTA in uscita,
//    D-L2-d). Una disponibilita' sotto zero e' una promessa non piu'
//    mantenibile — dopo una rettifica in meno, tipicamente — e si vede in ROSSO
//    (`cell-disponibile`): e' l'informazione per cui questa lista esiste.
//
// ⭐ `n_blocchi` e' cliccabile (solo per magazzino: i blocchi sono di una
//    coppia articolo-magazzino) e apre l'elenco delle promesse aperte in un
//    popover — il drill-down «gratis» di D-L2-j. Niente `DataTable` nel
//    popover: l'elenco e' corto per natura e si rende come lista.
//
// ⚠️ Sola lettura sulla disponibilita': niente «Nuovo», niente drawer — cambia
//    quando cambia il REGISTRO. L'unico gesto e' il BLOCCO manuale (Lotto 3
//    R-5, scheda per magazzino): «Blocca merce» sulla riga, «Libera» nel
//    popover dei blocchi; azione `blocca_merce` (permesso => nascondi), il
//    cancello vero e' il backend e il verbo DB. Dopo un gesto la lista si
//    rilegge: blocchi e disponibile cambiano.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ArticoloLookup from '../../catalogo/components/ArticoloLookup.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { formatNumber } from '../../core/utils/format'
import { exportDisponibilita, exportDisponibilitaArticoli } from '../api/magazzino'
import { useDisponibilitaArticoliStore, useDisponibilitaStore } from '../stores/disponibilita'
import { AZIONE_BLOCCA_MERCE, TAB_DISPONIBILITA } from '../vocabolari'
import DisponibilitaBlocchiPopover from './DisponibilitaBlocchiPopover.vue'
import BloccoApriDialog from './BloccoApriDialog.vue'
import BloccoLiberaDialog from './BloccoLiberaDialog.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { MANAGE_ICONS } from '../../core/constants'
import FiltriLista from '../../core/components/FiltriLista.vue'

const props = defineProps({
  scheda: {
    type: String,
    required: true,
    validator: (v) => Object.values(TAB_DISPONIBILITA).includes(v),
  },
})

const { t } = useI18n()
const isBlocked = useInjectBlocked()

// ⭐ La scheda decide store, catalogo ed export: le tre cose che cambiano.
//    ⚠️ La prop si legge UNA volta al setup, come `livello` di `SaldoPanel`:
//    un tab e' montato per scheda (`Tabs lazy`), e cambiarla senza `:key`
//    non e' un caso che questo componente serve.
const perMagazzino = props.scheda === TAB_DISPONIBILITA.MAGAZZINI
const store = perMagazzino ? useDisponibilitaStore() : useDisponibilitaArticoliStore()
const listaCodice = perMagazzino ? 'magazzino.disponibilita' : 'magazzino.disponibilita_articoli'
const exportFn = perMagazzino ? exportDisponibilita : exportDisponibilitaArticoli

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded,
  pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  exportFn,
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
  searchTableOptions: { defaultSortField: 'articolo_codice' },
})

// --- Filtri (toolbar caller) — binding store via BB ---
// L'articolo e' un lookup RICCO (`bindLookup`: il widget tiene l'oggetto, lo
// store l'id); i due interruttori scrivono `true | null` (`bindToggle`, i
// default: mai un `false` sul filo).
const { bindSelect, bindToggle, bindLookup } = useStoreFilterBindings(store, applyFilters)
const { value: magazzinoFilter, onChange: onMagazzinoChange } = bindSelect('magazzino_id')
const { value: articoloFilter, onChange: onArticoloChange } = bindLookup('articolo_id')
const { value: soloNegativa, onChange: onSoloNegativaChange } = bindToggle('solo_negativa')
const { value: soloConGiacenza, onChange: onSoloConGiacenzaChange } = bindToggle('solo_con_giacenza')

// --- Il popover dei blocchi (solo per magazzino) ---
const blocchiRef = ref(null)
function apriBlocchi(event, riga) {
  blocchiRef.value?.apri(event, riga)
}

// --- I blocchi manuali (solo per magazzino) ---
const rigaDaBloccare = ref(null)
const bloccoDaLiberare = ref(null)
function buildRowActions(riga) {
  return [{
    key: 'blocca',
    label: t('magazzino.blocchi.blocca'),
    icon: MANAGE_ICONS.BLOCCA_MERCE,
    action: AZIONE_BLOCCA_MERCE,
    command: () => { rigaDaBloccare.value = riga },
  }]
}

// La lista parte piena: nessun floor, e' la fotografia di oggi.
onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('magazzino.disponibilita.search_placeholder')"
            />
          </template>
          <LookupSelect
            v-if="perMagazzino"
            v-model="magazzinoFilter"
            class="app-filter-w-md"
            rel="magazzino.magazzini"
            :placeholder="t('magazzino.disponibilita.filtro_magazzino')"
            show-clear
            show-code
            @change="onMagazzinoChange"
          />
          <ArticoloLookup
            v-model="articoloFilter"
            class="app-filter-w-lg"
            :placeholder="t('magazzino.disponibilita.filtro_articolo')"
            :solo-attivi="false"
            @update:model-value="onArticoloChange"
          />
          <FiltroToggle
            v-model="soloNegativa"
            :label="t('magazzino.disponibilita.solo_negativa')"
            :hint="t('magazzino.disponibilita.solo_negativa_hint')"
            @change="onSoloNegativaChange"
          />
          <FiltroToggle
            v-model="soloConGiacenza"
            :label="t('magazzino.disponibilita.solo_con_giacenza')"
            @change="onSoloConGiacenzaChange"
          />
        </FiltriLista>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <!-- `chiave_riga`: le righe di una vista non hanno un `id`, e senza una
           chiave stabile PrimeVue le renderebbe con chiave `undefined`. -->
      <ListaConfigurabile
        ref="listaRef"
        :codice="listaCodice"
        data-key="chiave_riga"
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
        <!-- ⭐ Sotto zero e' ROSSO: e' la promessa non piu' mantenibile, il
             numero per cui questa lista esiste. -->
        <template #cell-disponibile="{ data }">
          <span
            :class="{ 'app-valore-negativo': Number(data.disponibile) < 0 }"
            v-tooltip.bottom="Number(data.disponibile) < 0
              ? t('magazzino.disponibilita.negativa_tooltip')
              : undefined"
          >
            {{ formatNumber(data.disponibile) }}
          </span>
        </template>

        <!-- Il numero apre l'elenco (solo per magazzino: i blocchi sono di una
             coppia). A zero non c'e' niente da aprire: resta un numero. -->
        <template v-if="perMagazzino" #cell-n_blocchi="{ data }">
          <Button
            v-if="Number(data.n_blocchi) > 0"
            :label="String(data.n_blocchi)"
            link
            size="small"
            @click.stop="apriBlocchi($event, data)"
          />
          <span v-else>{{ data.n_blocchi ?? 0 }}</span>
        </template>

        <template v-if="perMagazzino" #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </ListaConfigurabile>

      <DisponibilitaBlocchiPopover v-if="perMagazzino" ref="blocchiRef"
                                   @libera="(b) => { bloccoDaLiberare = b }" />
      <BloccoApriDialog
        v-if="perMagazzino"
        :visible="rigaDaBloccare !== null"
        :riga="rigaDaBloccare"
        @update:visible="(v) => { if (!v) rigaDaBloccare = null }"
        @aperto="store.fetchList()" />
      <BloccoLiberaDialog
        v-if="perMagazzino"
        :visible="bloccoDaLiberare !== null"
        :blocco="bloccoDaLiberare"
        @update:visible="(v) => { if (!v) bloccoDaLiberare = null }"
        @liberato="store.fetchList()" />
    </template>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />
  </div>
</template>

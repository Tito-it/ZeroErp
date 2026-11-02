<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista configurabile delle FAMIGLIE DI DOCUMENTO
//        (`<ListaConfigurabile codice="vendite.famiglie_documento">`): colonne,
//        ordine e visibilità dal catalogo `ui.lista_colonna`, con
//        personalizzazione per utente ed export.
//        Brief: brief-be-fe-crud-registri-di-numerazione §11.10 (FE-F6).
//
// ⭐ PERCHÉ VIVE IN AMMINISTRAZIONE E NON DENTRO I REGISTRI (decisione di Tid,
//    2026-09-02). I registri stanno nel drawer di UN emittente; una famiglia è
//    GLOBALE — non ha una colonna emittente e vale per tutti. Come tab
//    dell'emittente la stessa riga sarebbe comparsa modificabile aprendo un
//    emittente qualunque, e sarebbe sembrata sua. Il legame fra le due lo tiene
//    il drawer del registro, che dalla famiglia prende i default della forma.
//
// ⛔ Il CRUD è per il solo AMMINISTRATORE (D6): il cancello sta sull'endpoint
//    (`AdminAPIView`), non nel database — `vendite.famiglie_documento` non ha
//    RLS e non gliene si aggiunge una per un caso che un permesso risolve.
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import FamigliaDocumentoDrawer from '../components/FamigliaDocumentoDrawer.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useNotify } from '../../core/composables/useNotify'
import { bloccoAttivo, motivoBloccoRiga } from '../../core/utils/bloccoMotivo'
import { READONLY_DOMAINS, MANAGE_ICONS } from '../../core/constants'
import { useFamiglieDocumentoStore } from '../stores/famiglieDocumento'
import { exportFamiglie } from '../api/famiglieDocumento'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { buildAttivoOptions } from '../../core/utils/options'

const { t, te } = useI18n()
const notify = useNotify()
const store = useFamiglieDocumentoStore()
const drawer = useDrawerState()
const { confirmAction } = useConfirmAction()
const { isReadonly, isBlocked } = useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)

const {
  searchText, applyFilters, paginatorProps, onPage, onSort, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'amministrazione.famiglie_documento.new',
  onNew: () => drawer.openCreate(),
  exportFn: exportFamiglie,
  // ⭐ I filtri li dà lo STORE, gli stessi che ha appena usato per la lista: un
  //    secondo elenco qui esporterebbe un insieme diverso da quello a video.
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
  searchTableOptions: { defaultSortField: 'codice_interno' },
})

// ⛔ `null` = TUTTE, spente comprese: una famiglia spenta è la riga che spiega
//    perché una tabella non è più disponibile. Un default «solo attive»
//    nasconderebbe proprio quella.
// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: serieFilter, onChange: onSerieChange } = bindSelect('gestisce_serie')
// ⭐ Dal BB (regola del 2, ok Tid 2026-09-23). ⛔ Anche qui la tendina diceva
//    «Inattivo» e la colonna, resa da `AttivoTag`, «Non attivo».
const attivoOptions = buildAttivoOptions(t)
const serieOptions = [
  { label: t('amministrazione.famiglie_documento.serie_tutte'), value: null },
  { label: t('amministrazione.famiglie_documento.serie_si'), value: true },
  { label: t('amministrazione.famiglie_documento.serie_no'), value: false },
]

onMounted(() => { store.fetchList() })

function onRowClick(data) {
  drawer.editRow(data, 'id')
}

function onDrawerSaved() {
  drawer.close()
  store.fetchList()
}

// Scopo: azioni di riga — accendere e spegnere la famiglia.
// ⛔ Il pulsante si spegne col MOTIVO, e il motivo lo dice il backend
//    (`rimozione_blocco_*`, dalla stessa check che il guard DB chiama per
//    rifiutare): un'azione grigia e muta manda a indovinare.
function buildRowActions(data) {
  // ⛔ `bloccoAttivo` e non `!data.can_disattivare` scritto a mano: la domanda
  //    «posso?» ha una sede sola (`bloccoMotivo.js`), che guarda il FLAG del
  //    backend quando c'è e ripiega sulla presenza del motivo. Ricalcolarla qui
  //    sarebbe la seconda copia della stessa regola, e la prima a divergere.
  // ⚠️ Il `data.attivo &&` resta, ed è di questa maschera: su una riga già
  //    spenta l'azione è la RIATTIVAZIONE, che di guard non ne ha — e il
  //    motivo dello spegnimento non c'entra niente con lei.
  const bloccata = data.attivo && bloccoAttivo(data, 'rimozione_blocco', 'can_disattivare')
  return [
    {
      key: 'attivo',
      label: data.attivo
        ? t('amministrazione.famiglie_documento.action_disattiva')
        : t('amministrazione.famiglie_documento.action_attiva'),
      // Lo STESSO senso delle anagrafiche di magazzino (spegni/riaccendi): un
      // glifo per concetto, non uno per pagina (frontend-standards §«Dove vive
      // il NOME di un'icona»). Fino al 21-09 qui erano `CANCEL`/`RELOAD`.
      icon: data.attivo ? MANAGE_ICONS.DISATTIVA : MANAGE_ICONS.RIATTIVA,
      disabled: bloccata,
      tooltip: bloccata ? motivoBloccoRiga(t, te, data, 'rimozione_blocco') : undefined,
      // ⛔ `allowWhenInactive` NON è un di più: `RowActionsMenu` disabilita da
      //    sé le azioni sulle righe spente (`disableWhenInactive`, default
      //    true), e senza questo escape la RIATTIVAZIONE sarebbe spenta
      //    proprio sulle righe che deve riaccendere — con un tooltip che dice
      //    «azione non disponibile su record inattivo», cioè la cosa sbagliata.
      allowWhenInactive: true,
      command: () => cambiaAttivo(data),
    },
  ]
}

function cambiaAttivo(data) {
  confirmAction({
    header: data.attivo
      ? t('amministrazione.famiglie_documento.action_disattiva')
      : t('amministrazione.famiglie_documento.action_attiva'),
    message: data.attivo
      ? t('amministrazione.famiglie_documento.conferma_disattiva', { codice: data.codice_interno })
      : t('amministrazione.famiglie_documento.conferma_attiva', { codice: data.codice_interno }),
    onAccept: async () => {
      await store.cambiaAttivo(data.id, !data.attivo)
      notify.success(t('amministrazione.famiglie_documento.stato_aggiornato'))
    },
  })
}
</script>

<template>
  <div class="app-page">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('amministrazione.famiglie_documento.search_placeholder')"
            />
          </template>
          <!-- ⚠️ Il placeholder porta l'etichetta del DEFAULT: il valore di
               partenza e' `null` = tutte, e per PrimeVue `null` e' «niente
               selezionato» — senza, le due combo escono vuote su filtri che
               valgono «tutte». -->
          <Select
            v-model="attivoFilter"
            class="app-filter-w-sm"
            :options="attivoOptions"
            :placeholder="t('amministrazione.stato_all')"
            option-label="label"
            option-value="value"
            @change="onAttivoChange"
          />
          <Select
            v-model="serieFilter"
            class="app-filter-w-sm"
            :options="serieOptions"
            :placeholder="t('amministrazione.famiglie_documento.serie_tutte')"
            option-label="label"
            option-value="value"
            @change="onSerieChange"
          />
        </FiltriLista>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
          </template>
        </PageActionsBar>
      </div>

      <ListaConfigurabile
        ref="listaRef"
        codice="vendite.famiglie_documento"
        :rows="store.items"
        :total="store.totalRecords"
        :loading="store.loading"
        :paginator-options="paginatorProps"
        :page="tablePage"
        :sort-field="paginatorProps.sortField"
        :sort-order="paginatorProps.sortOrder"
        @page="onPage"
        @sort="onSort"
        @row-click="onRowClick"
        @config-loaded="onConfigLoaded"
      >
        <template #cell-attivo="{ data }">
          <!-- ⛔ Il prop si chiama `active`, NON `attivo`: con il nome sbagliato
             Vue non solleva niente, il prop resta al suo default `false` e la
             colonna dice «non attivo» su OGNI riga. Difetto visto in app il
             2026-09-02, su questa lista e sulla gemella. -->
        <AttivoTag :active="data.attivo" />
        </template>
        <!-- ⚠️ Colonna DERIVATA (`colonna_serie IS NOT NULL`): il catalogo la
             dichiara `boolean` con formato `yesno`, quindi il formatter del BB
             la renderebbe già — lo slot serve solo a dire, sulle famiglie che
             la serie non ce l'hanno, che non è un dato mancante. -->
        <template #cell-colonna_serie="{ data }">
          <span v-if="data.colonna_serie">{{ data.colonna_serie }}</span>
          <span v-else class="app-field-hint">{{ t('amministrazione.famiglie_documento.serie_assente') }}</span>
        </template>
        <!-- ⛔ Lo slot del kebab si chiama `#actions`: col nome sbagliato la
             colonna non viene resa affatto, e senza errori. -->
        <template v-if="!isReadonly" #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </ListaConfigurabile>

      <FamigliaDocumentoDrawer
        :visible="drawer.state.visible"
        @update:visible="(v) => drawer.state.visible = v"
        :famiglia-id="drawer.state.itemId"
        @saved="onDrawerSaved"
      />

      <ExportDialog
        v-model:visible="exportDialogVisible"
        :loading="exportLoading"
        @export="onExportConfirm"
      />
    </template>
  </div>
</template>

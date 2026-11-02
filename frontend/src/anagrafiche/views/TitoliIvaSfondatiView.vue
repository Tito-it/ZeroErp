<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Lista di PRESIDIO dei titoli IVA il cui consumo ha superato il tetto
// (Q4 del piano brief-be-fe-titoli-iva-soggetto).
//
// ⭐ ESISTE PERCHE' IL DB HA DECISO DI NON BLOCCARE lo sfondamento sulle
//   forzature, ed e' l'altra meta' di quella decisione: «una forzatura esiste
//   per registrare fatturazioni fuori dal sistema, e impedire di scriverla
//   impedirebbe di ACCORGERSENE. Il presidio giusto per quel caso e' una lista
//   di titoli sfondati che qualcuno guarda». Senza questa schermata, quella
//   decisione resterebbe una meta' sola.
//
// ⭐ CONVERTITA su `<ListaConfigurabile>` il 2026-09-02 (lista 63), e la
//   motivazione precedente — «lista semplice, si guarda e basta, non si esporta
//   e non si personalizza» — e' caduta insieme al difetto che nascondeva:
//   l'endpoint restituiva i primi **500** e non lo diceva a nessuno. Su un
//   presidio, dal 501-esimo caso in poi la forzatura non si vedeva. Ora pagina.
//
// ⚠️ Il perimetro emittente lo fa la RLS: un operatore vede solo i titoli degli
//   emittenti che ha in whitelist. Qui non si filtra niente a mano.
import { onActivated, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import ExportDialog from '../../core/components/ExportDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { useTitoliIvaSfondatiStore } from '../stores/titoliIvaSfondati'
import TitoloIvaDrawer from '../components/TitoloIvaDrawer.vue'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.ANAGRAFICHE)
const store = useTitoliIvaSfondatiStore()

const drawerVisible = ref(false)
const titoloSelezionato = ref({ soggettoId: null, titoloId: null })

// Scaffolding della lista configurabile (useSearchTable + pageActions).
// ⚠️ Niente `exportFn`: questa lista non ha endpoint di export, e il BB rende
//    l'azione condizionale — con l'handler assente il pulsante aprirebbe un
//    dialog che non scarica niente.
const {
  onPage, onSort, paginatorProps, tablePage, reload,
  listaRef, dirty,
  exportDialogVisible, exportLoading, onExportConfirm, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store)

onMounted(reload)
// ⚠️ `onActivated` e non solo `onMounted`: sotto KeepAlive il rientro nella tab
//    non rimonta il componente, e una lista di presidio che mostra dati vecchi
//    e' peggio di una vuota (`feedback_keepalive_onactivated`).
onActivated(reload)

// Scopo: apre il drawer del titolo su cui si e' cliccato.
// ⚠️ `<ListaConfigurabile>` emette `data` direttamente, non l'evento PrimeVue:
//    la firma e' diversa da quella della `<DataTable>` che c'era prima.
function onRowClick(data) {
  titoloSelezionato.value = { soggettoId: data.soggetto_id, titoloId: data.id }
  drawerVisible.value = true
}
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <Message severity="info" :closable="false">
      {{ t('anagrafiche.titoli_iva.sfondati_hint') }}
    </Message>

    <ListaConfigurabile
      ref="listaRef"
      codice="anagrafiche.titoli_iva_sfondati"
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
      <!-- Colonna composta da DUE campi: non ha un `campo_sorgente` e il
           catalogo la dichiara calcolata. -->
      <template #cell-validita="{ data }">
        {{ displayDate(data.valido_dal) }} —
        {{ data.valido_al ? displayDate(data.valido_al)
                          : t('anagrafiche.titoli_iva.senza_scadenza') }}
      </template>
      <!-- ⭐ `eccedenza` arriva ora dal BACKEND come colonna vera (alias SQL),
           non piu' calcolata qui: e' l'ordinamento che da' senso a questa
           lista, e una colonna calcolata dal frontend non si puo' ordinare. -->
      <template #cell-eccedenza="{ data }">
        <Tag :value="formatCurrency(data.eccedenza)" severity="danger" />
      </template>
    </ListaConfigurabile>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @confirm="onExportConfirm"
    />

    <TitoloIvaDrawer
      v-model:visible="drawerVisible"
      :soggetto-id="titoloSelezionato.soggettoId"
      :titolo-id="titoloSelezionato.titoloId"
      @saved="reload" />
  </div>
</template>

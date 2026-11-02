<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Tab "Flussi" della scheda pratica — SOLA LETTURA.
// Due liste informative:
//   1) Flussi istanziati della pratica: la lista a catalogo `pratiche.flussi`
//      (lista 85), su `useDrawerTabLista` + `<DrawerTabLista>`;
//   2) Step del percorso ancora da completare (roadmap residua).
// Creazione ed esecuzione dei flussi NON vivono qui: avvengono nel percorso
// template-driven della dashboard (PraticaPercorso + FlussoDrawer), unica
// sorgente di verita'. La vecchia creazione di "flusso generico" (senza
// template) e le azioni avvia/completa inline sono state rimosse (fuori modello).
//
// ⭐ La prima lista NON e' piu' una `DataTable` grezza (2026-09-27, brief-db-
//    liste-datatable-grezze riga 3): pagine, colonne scelte dall'operatore,
//    export e ricerca arrivano dal catalogo. L'esito si legge come
//    DESCRIZIONE (`esito_descrizione`), non piu' come codice grezzo.
// ⚠️ La seconda resta una `DataTable`, e fuori dal perimetro di quel giro:
//    non e' una lista di un endpoint suo, e' il percorso (`/percorso/`)
//    filtrato qui — per questo si ricarica INSIEME alla prima (`fetchExtra`),
//    cosi' «Ricarica» riallinea tutto il tab e non meta'.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { fetchPercorso } from '../api/pratiche-api'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { useNotify } from '../../core/composables/useNotify'
import { extractApiError } from '../../core/utils/apiError'
import { usePraticaFlussiStore } from '../stores/praticaFlussi'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { statoFlussoSeverity } from '../../core/utils/severity'
import { STATO_FLUSSO, RAMO_STEP } from '../../core/constants'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
// DataTable grezza: e' la SECONDA lista del tab, gli step residui del percorso
// (`/percorso/` filtrato in `stepNonEseguiti`) — una proiezione della pratica
// limitata dal suo template, senza endpoint ne' popolazione propri.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'

const { t } = useI18n()

const props = defineProps({
  praticaId: { type: Number, required: true },
  // ⭐ L'emittente (PK) della pratica aperta: lo porta il dettaglio che il
  //    drawer ha gia' letto. Serve alla lista `pratiche.flussi`, che NON e'
  //    `multi_emittente`: e' la richiesta a fissare l'emittente, o chi ne vede
  //    piu' d'uno riceverebbe «scegli un emittente» dentro una pratica gia'
  //    aperta. `null` finche' il dettaglio non e' arrivato: la lista aspetta.
  emittenteFiscaleId: { type: Number, default: null },
})

const store = usePraticaFlussiStore()
const notify = useNotify()
const percorso = ref([])
const percorsoLoading = ref(false)
const percorsoFv = useFetchVersion()

// ⚠️ Pratica nuova: il percorso della precedente se ne va SUBITO, e una sua
//    risposta ancora in volo non lo ripopola. La lettura nuova la fa il BB
//    (`fetchExtra`), quando anche l'emittente e' arrivato. Dichiarato PRIMA di
//    `useDrawerTabLista`: i watch girano nell'ordine di creazione.
watch(() => props.praticaId, () => {
  percorsoFv.invalidate()
  percorso.value = []
  percorsoLoading.value = false
})

// Scopo: il percorso della pratica (seconda lista). Separato dalla lista dei
//        flussi: ha il suo endpoint e il suo stato di caricamento.
// ⚠️ L'errore si dice (toast): il BB assorbe il rifiuto di `fetchExtra`, e un
//    percorso non letto a vista vuota sembrerebbe «niente da fare».
async function loadPercorso() {
  if (!props.praticaId) return
  const tag = percorsoFv.tag()
  percorsoLoading.value = true
  try {
    const res = await fetchPercorso(props.praticaId)
    if (!percorsoFv.isCurrent(tag)) return
    percorso.value = res.data.data.results || []
  } catch (err) {
    if (percorsoFv.isCurrent(tag)) notify.error(extractApiError(err, t('common.error')))
  } finally {
    if (percorsoFv.isCurrent(tag)) percorsoLoading.value = false
  }
}

const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useDrawerTabLista(store, {
  // Il padre composto: la pratica e il suo emittente. ⚠️ Finche' l'emittente
  //    non c'e' la lista non legge e resta in caricamento (`attesaPadre`).
  parentId: {
    praticaId: () => props.praticaId,
    emittenteId: () => props.emittenteFiscaleId,
  },
  fetchExtra: loadPercorso,
})

// Step del percorso ancora da completare: non esiste un'istanza COMPLETATO e
// lo step e' ancora percorribile (escludo il ramo morto di un bivio, che non
// sara' eseguito). Include "da creare" (flusso_id null) e in corso/da eseguire.
// Vista "cosa resta da fare", complementare alla lista flussi.
const stepNonEseguiti = computed(() =>
  percorso.value.filter(
    s => s.stato_codice_interno !== STATO_FLUSSO.COMPLETATO && s.ramo !== RAMO_STEP.RAMO_CHIUSO,
  ),
)
</script>

<template>
  <div>
    <!-- Lista 1: flussi istanziati (sola lettura) — lista a catalogo 85 -->
    <h4 class="pratica-flussi-titolo">{{ t('pratiche.flussi_titolo') }}</h4>
    <DrawerTabLista
      ref="listaRef"
      codice="pratiche.flussi"
      :emittente-esplicito="emittenteFiscaleId"
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
      <template #filtri-sempre>
        <InputText
          v-model="searchText"
          class="app-filter-w-lg"
          :placeholder="t('pratiche.flussi_cerca_placeholder')"
        />
      </template>
      <!-- La frase del dominio al posto dell'empty-state generico, e solo se
           la lettura e' riuscita: con `erroreCaricamento` la lista e' vuota
           per un'altra ragione. -->
      <template #empty>
        <span v-if="!store.erroreCaricamento">{{ t('pratiche.flussi_vuoti') }}</span>
      </template>
      <!-- Un flusso senza template e' un'attivita' generica: la cella lo dice
           invece di restare vuota, come faceva la tabella di prima. -->
      <template #cell-template_flusso="{ data }">
        {{ data.template_flusso_descrizione || t('pratiche.flusso_generico') }}
      </template>
      <template #cell-stato="{ data }">
        <Tag :value="data.stato_descrizione || data.stato_codice_interno" :severity="statoFlussoSeverity(data.stato_codice_interno)" />
      </template>
    </DrawerTabLista>

    <!-- Lista 2: step del percorso ancora da completare (sola lettura) -->
    <h4 class="pratica-flussi-titolo">{{ t('pratiche.flussi_step_da_completare') }}</h4>
    <DataTable
      :value="stepNonEseguiti"
      :loading="percorsoLoading"
      striped-rows
      class="app-datatable"
      data-key="template_flusso_id"
    >
      <Column field="sequenza" :header="t('pratiche.flusso_col_seq')" style="width: 60px;" />
      <Column field="template_flusso_codice" :header="t('pratiche.flusso_col_template')" style="width: 180px;">
        <template #body="{ data }">
          {{ data.template_flusso_descrizione || data.template_flusso_codice }}
        </template>
      </Column>
      <Column :header="t('pratiche.col_stato')" style="width: 120px;">
        <template #body="{ data }">
          <Tag
            v-if="data.flusso_id"
            :value="data.stato_descrizione || data.stato_codice_interno"
            :severity="statoFlussoSeverity(data.stato_codice_interno)"
          />
          <Tag v-else :value="t('pratiche.percorso_da_creare')" severity="secondary" />
        </template>
      </Column>
      <template #empty>
        <div class="text-center app-text-muted p-3">{{ t('pratiche.flussi_step_tutti_completati') }}</div>
      </template>
    </DataTable>
  </div>
</template>

<style scoped>
.pratica-flussi-titolo {
  margin: 0.75rem 0 0.4rem;
}
.pratica-flussi-titolo:first-child {
  margin-top: 0;
}
</style>

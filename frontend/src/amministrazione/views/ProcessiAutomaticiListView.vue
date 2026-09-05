<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Doc: Vue
-->
<script setup>
// Scopo: la schermata dei PROCESSI AUTOMATICI — quali programmi girano da soli,
//        di che classe sono, con quale identità e per quali aziende — più lo
//        stato dei sei presidi del cantiere «nessun processo senza operatore».
//
// ⭐ Fino al 2026-09-05 tutto questo si vedeva solo da `psql`, e
//    `GET /tracciamento/job-runs/` esisteva da mesi senza un solo consumatore
//    nel frontend. Un presidio che si interroga a mano lo guarda chi sta
//    lavorando a quel pezzo; uno che sta in una schermata lo guarda anche chi
//    passa di lì.
// ⛔ `amm-software` e non `strumenti`: le sei viste nominano TUTTE le aziende e
//    non hanno RLS, quindi il gate è `AdminAPIView` (SUPER_ADMIN). Il posto e il
//    permesso dicono la stessa cosa, e non c'è nessuna eccezione da ricordare.
// ⚠️ Niente `useReadonlyMode`: in `amm-software` non c'è un livello d'area da
//    risolvere — o sei super admin e vedi tutto, o non arrivi alla pagina. Un
//    terzo cancello che non decide niente sarebbe rumore.
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import { useProcessiAutomaticiStore } from '../stores/processiAutomatici'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useDrawerState } from '../../core/composables/useDrawerState'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ProcessoDrawer from '../components/ProcessoDrawer.vue'
import PresidiProcessiPanel from '../components/PresidiProcessiPanel.vue'
import { displayTimestamp } from '../../core/utils/date'

const { t } = useI18n()
const store = useProcessiAutomaticiStore()

// ⛔ Nessun `onNew` e nessun `exportFn`: lo scaffolding omette da sé le azioni
//    che non gli si passano. Il registro è catalogo — non si crea un processo
//    da qui — e l'export non ha endpoint.
const {
  searchText, applyFilters, paginatorProps, onPage, onSort, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'codice' },
})

const drawer = useDrawerState()
const classeFilter = ref(null)
const canaleFilter = ref(null)

const classeOptions = [
  { label: t('amministrazione.processi.classe_tutte'), value: null },
  { label: 'MANUTENZIONE', value: 'MANUTENZIONE' },
  { label: 'AMMINISTRAZIONE', value: 'AMMINISTRAZIONE' },
  { label: 'DOMINIO', value: 'DOMINIO' },
]
const canaleOptions = [
  { label: t('amministrazione.processi.canale_tutti'), value: null },
  { label: 'PGAGENT', value: 'PGAGENT' },
  { label: 'COMMAND', value: 'COMMAND' },
  { label: 'CODA', value: 'CODA' },
]

// ⚠️ I presidi si caricano una volta all'apertura e si ricaricano col
//    «Ricarica» della lista: un registro di catalogo non cambia ogni pochi
//    secondi, e un polling qui sarebbe lavoro sprecato che sfarfalla sotto gli
//    occhi di chi legge.
onMounted(() => {
  store.fetchList()
  store.caricaPresidi()
})

function applyExtraFilters() {
  store.filters.classe = classeFilter.value
  store.filters.canale = canaleFilter.value
  applyFilters()
}

function openDettaglio(row) {
  drawer.editRow(row, 'codice')
}

// Dopo la creazione di un utente tecnico cambiano sia la riga sia i presidi.
function onIdentitaCreata() {
  store.fetchList()
  store.caricaPresidi()
}
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('amministrazione.processi.search_placeholder')"
        />
        <Select
          v-model="classeFilter"
          :options="classeOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.processi.classe_tutte')"
          @change="applyExtraFilters"
        />
        <Select
          v-model="canaleFilter"
          :options="canaleOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.processi.canale_tutti')"
          @change="applyExtraFilters"
        />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <!-- ⛔ «Lista vuota» e «lista non letta» si assomigliano e dicono cose
         opposte: il BB dello store distingue, e qui si rende la differenza. -->
    <Message v-if="store.erroreCaricamento" severity="error" :closable="false">
      {{ t('amministrazione.processi.errore_caricamento') }}
    </Message>

    <ListaConfigurabile
      ref="listaRef"
      codice="amm.processi"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="openDettaglio"
      @config-loaded="onConfigLoaded"
    >
      <template #cell-classe="{ data }">
        <Tag :value="data.classe" severity="info" />
      </template>

      <template #cell-identita_attive="{ data }">
        <!-- ⭐ Tre stati, non due: «non ne vuole» non è «gliene manca una».
             Un processo di coda gira con l'identità di chi lo accoda, e
             mostrarlo come carente insegnerebbe a ignorare l'avviso. -->
        <span v-if="!data.vuole_identita" class="app-proc-na">—</span>
        <Tag
          v-else
          :value="String(data.identita_attive)"
          :severity="data.identita_attive > 0 ? 'success' : 'warn'"
        />
      </template>

      <template #cell-ultimo_run="{ data }">
        <span v-if="!data.ultimo_run" class="app-proc-na">
          {{ t('amministrazione.processi.mai_girato') }}
        </span>
        <span v-else>{{ displayTimestamp(data.ultimo_run) }}</span>
      </template>

      <template #cell-ultimo_ok="{ data }">
        <!-- ⚠️ `null` = mai girato, non «fallito». -->
        <Tag
          v-if="data.ultimo_ok === true"
          :value="t('amministrazione.processi.esito_ok')"
          severity="success"
        />
        <Tag
          v-else-if="data.ultimo_ok === false"
          :value="t('amministrazione.processi.esito_ko')"
          severity="danger"
        />
        <span v-else class="app-proc-na">—</span>
      </template>
    </ListaConfigurabile>

    <section class="app-proc-presidi">
      <h3 class="app-proc-presidi-titolo">
        {{ t('amministrazione.processi.presidi_titolo') }}
        <Tag
          :value="String(store.presidiConRighe)"
          :severity="store.presidiConRighe === 0 ? 'success' : 'warn'"
        />
      </h3>
      <p class="app-proc-help">{{ t('amministrazione.processi.presidi_help') }}</p>
      <PresidiProcessiPanel
        :presidi="store.presidi"
        :loading="store.presidiLoading"
        :errore="store.presidiErrore"
      />
    </section>

    <ProcessoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :codice="drawer.state.itemId"
      @identita-creata="onIdentitaCreata"
    />
  </div>
</template>

<style scoped>
.app-proc-na { opacity: 0.55; }
.app-proc-presidi { margin-top: 1.25rem; }
.app-proc-presidi-titolo {
  display: flex; align-items: center; gap: 0.5rem;
  font-size: 1rem; margin: 0 0 0.25rem;
}
.app-proc-help { font-size: 0.85rem; opacity: 0.8; margin: 0 0 0.75rem; }
</style>

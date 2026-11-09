<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
  Doc: Vue
-->
<script setup>
// Scopo: la scheda «Processi» della vista Processi automatici — il registro:
//        quali programmi girano da soli, di che classe sono, con quale
//        identità e quando hanno girato l'ultima volta. Filtri e azioni di
//        lista stanno qui e solo qui: la scheda dei presidi non ne ha.
//
// ⭐ Estratta dalla vista il 2026-10-14 (richiesta di Tid), quando i presidi
//    sono passati in una scheda loro: sotto la lista, a ogni presidio acceso
//    la sezione saliva e le righe visibili calavano. Due contenuti che si
//    dividono un'altezza sola si rubano spazio a vicenda, qualunque tetto si
//    scelga.
// ⚠️ Montata dentro un `<Tabs lazy>`: ogni attivazione della scheda è un
//    mount, quindi il caricamento sta in `onMounted` (§Pattern Tab-View). Il
//    drawer di dettaglio resta nella vista, fuori dai `Tabs`: qui si emette
//    solo la riga cliccata.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import { useProcessiAutomaticiStore } from '../stores/processiAutomatici'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import { displayTimestamp } from '../../core/utils/date'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { getProcessiVocabolari } from '../api/amministrazione'

const emit = defineEmits(['apri'])

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

// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: classeFilter, onChange: onClasseChange } = bindSelect('classe')
const { value: canaleFilter, onChange: onCanaleChange } = bindSelect('canale')
const { value: vivoFilter, onChange: onVivoChange } = bindSelect('vivo')

// ⛔ Classi e canali NON si scrivono qui: arrivano dal backend
//    (`GET processi/vocabolari/`), che li legge dalle stesse costanti con cui
//    rifiuta un filtro — e quelle hanno il loro guardrail sui CHECK di
//    `dbops.processi`. Fino al 2026-11-09 c'era una copia a mano senza
//    presidio, e le mancava `CODA_AUTOMATICA` (nel CHECK dal 05-09): i
//    processi svegliati da una macchina non si potevano filtrare, senza errore.
const vocabolari = useGlobalLookup('amm.processi.vocabolari', getProcessiVocabolari, {
  immediate: true, transform: (r) => r.data.data,
})
const opzioni = (tutti, codici) => [
  { label: tutti, value: null },
  ...(codici ?? []).map((c) => ({ label: c, value: c })),
]
const classeOptions = computed(() => opzioni(
  t('amministrazione.processi.classe_tutte'), vocabolari.items.value.classi,
))
const canaleOptions = computed(() => opzioni(
  t('amministrazione.processi.canale_tutti'), vocabolari.items.value.canali,
))
// «Vivo» lo decide il DB sulla data del ritiro (`obsoleto_dal`), non `attivo`.
const vivoOptions = computed(() => [
  { label: t('amministrazione.processi.vivo_tutti'), value: null },
  { label: t('amministrazione.processi.vivo_si'), value: true },
  { label: t('amministrazione.processi.vivo_no'), value: false },
])

// La LISTA al mount: il rientro lo rinfresca gia' lo scaffolding
// (`useListaConfigurabilePage` → `useSearchTable`).
onMounted(() => {
  store.fetchList()
})
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <FiltriLista :store="store">
        <template #sempre>
          <InputText
            v-model="searchText"
            class="app-filter-w-lg"
            :placeholder="t('amministrazione.processi.search_placeholder')"
          />
        </template>
        <Select
          v-model="classeFilter"
          class="app-filter-w-sm"
          :options="classeOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.processi.classe_tutte')"
          @change="onClasseChange"
        />
        <Select
          v-model="canaleFilter"
          class="app-filter-w-sm"
          :options="canaleOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.processi.canale_tutti')"
          @change="onCanaleChange"
        />
        <Select
          v-model="vivoFilter"
          class="app-filter-w-sm"
          :options="vivoOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('amministrazione.processi.vivo_tutti')"
          @change="onVivoChange"
        />
      </FiltriLista>
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
      @row-click="(row) => emit('apri', row)"
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
        <!-- ⚠️ `null` non è «fallito»: nessuna corsa vera conclusa (mai
             girato, solo corse saltate, o l'ultima ancora in corso). -->
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
  </div>
</template>

<style scoped>
.app-proc-na { opacity: 0.55; }
</style>

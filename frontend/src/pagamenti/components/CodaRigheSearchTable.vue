<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: LA CODA DEL RICONCILIATORE — le righe contabili da lavorare viste
//        attraverso le distinte (`<ListaConfigurabile codice="pagamenti.righe">`).
//
// ⭐ UNA LISTA, DUE PORTE (Q-4 -> c): «da abbinare» e «sospese» sono la stessa
//    lista col filtro `coda` gia' impostato dalla voce di menu. A catalogo il
//    seed e' UNO, perche' il filtro vive nella toolbar e non nella definizione.
// ⚠️ La colonna «Distinta» non e' decorazione: qui le righe arrivano da
//    distinte DIVERSE, e una riga senza il documento da cui viene non si
//    lavora.
//
// ⭐ DALLA CODA SI LAVORA (FE-4, D20 — 2026-09-19): il kebab di riga porta
//    Abbina · Sospendi · Scarta · Riporta da abbinare, e sulle sospese di una
//    distinta gia' REGISTRATA «Abbina e registra» — la tardiva (D20-b), l'unica
//    strada del denaro rimasto indietro. Le voci vengono dalla MATRICE e dal
//    catalogo, che arrivano accanto alle righe (`stati_riga`,
//    `transizioni_riga`), e le costruisce il composable di dominio
//    `useAzioniRigaContabile` — la stessa sede del drawer. ⛔ Niente «Elimina»
//    qui: il contenuto si lavora nel drawer della distinta, e la coda mostra
//    solo righe da lavorare.
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Select from 'primevue/select'

import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useInjectBlocked, useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { statoRigaContabileSeverity } from '../../core/utils/severity'
import { MODO_ABBINA, useAzioniRigaContabile } from '../composables/useAzioniRigaContabile'
import { useEtichettePagamenti } from '../etichette'
import { useCodaRigheStore } from '../stores/codaRighe'
import { STATUS_ICONS } from '../../core/constants'
import { CODE, ROTTA_PER_CODA } from '../vocabolari'
import AbbinaRigaDialog from './AbbinaRigaDialog.vue'
import FiltroPeriodo from '../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'

const props = defineProps({
  // La coda che questa porta apre. ⚠️ Arriva dalla ROTTA, non da uno stato
  // interno: e' cio' che rende le due voci di menu deep-linkabili.
  coda: { type: String, default: CODE.DA_ABBINARE },
})
const emit = defineEmits(['row-click'])

const { t } = useI18n()
const router = useRouter()
const store = useCodaRigheStore()
const isBlocked = useInjectBlocked()
const isReadonly = useInjectReadonly()

// Il dialogo di abbinamento, nei suoi due modi.
const abbinaVisible = ref(false)
const rigaDaAbbinare = ref(null)
const modoAbbina = ref(MODO_ABBINA.ABBINA)

const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'data_pagamento', defaultSortOrder: 'desc' },
})

const { bindPeriodo } = useStoreFilterBindings(store, applyFilters)
// Il periodo e' UN filtro con due estremi: un binding, un componente.
const periodo = bindPeriodo()

const { opzioniCoda: costruisciOpzioniCoda } = useEtichettePagamenti()

// ⭐ Il selettore resta a video — chi lavora le sospese deve poter passare
//    all'altra coda senza tornare al menu — ma NAVIGA invece di cambiare uno
//    stato interno.
// ⛔ La prima stesura cambiava lo store: la rotta restava `/righe/sospese`
//    mentre a video comparivano le righe «da abbinare». Ne discendevano tre
//    cose, tutte silenziose: l'etichetta del TAB mentiva, il deep-link non
//    descriveva piu' la pagina, e al rientro nella scheda la sincronizzazione
//    con la rotta avrebbe annullato la scelta fatta a mano. La rotta e' l'unica
//    verita'.
// ⚠️ Le opzioni sono DUE, quante sono le porte: `TUTTE` esiste nel contratto
//    dell'endpoint ma non ha una rotta, e offrirla qui darebbe una voce che
//    porta in una pagina che non esiste.
// ⚠️ `computed` e non una costante: le etichette dipendono dalla lingua, e al
//    cambio lingua un array calcolato una volta sola resterebbe in italiano.
const opzioniCoda = computed(() => costruisciOpzioniCoda())
const codaCorrente = computed({
  get: () => props.coda,
  set: (v) => {
    const rotta = ROTTA_PER_CODA[v]
    if (rotta && v !== props.coda) router.push({ name: rotta })
  },
})

function onRowClick(data) { emit('row-click', data) }

// ── azioni di riga ────────────────────────────────────────────────
// I fatti della testata arrivano SULLA RIGA (BE-4: `contabile_righe_lavorabili`,
// `contabile_registrata`), perche' qui ogni riga viene da una distinta
// diversa e non c'e' un dettaglio da cui leggerli. ⚠️ La coda seleziona gia'
// le sole righe lavorabili: la bandiera si passa lo stesso, perche' la regola
// del kebab non deve dipendere dal filtro da cui la riga e' passata.
const { buildRowActions } = useAzioniRigaContabile({
  statiRiga: () => store.statiRiga,
  transizioniRiga: () => store.transizioniRiga,
  testataDi: (riga) => ({
    righeLavorabili: riga.contabile_righe_lavorabili,
    registrata: riga.contabile_registrata === true,
  }),
  readonly: () => isReadonly.value,
  onAbbina: (riga, modo) => {
    rigaDaAbbinare.value = riga
    modoAbbina.value = modo
    abbinaVisible.value = true
  },
  // Dopo un gesto la riga cambia coda o sparisce dalla coda: si rilegge la
  // pagina corrente (idempotente, come al rientro nella scheda).
  ricarica: () => store.fetchList(),
})

// Scopo: allinea lo store alla coda della ROTTA, e ricarica.
// Note: ⚠️ Idempotente di proposito. Se la coda e' gia' quella giusta NON si
//       chiama `apriCoda`: azzererebbe l'offset, cioe' rientrare nella scheda
//       dopo aver cambiato tab riavvolgerebbe la lista a pagina 1 senza che
//       nessuno l'abbia chiesto.
//       ⛔ E in quel ramo non si ricarica nemmeno: al rientro nella scheda ci
//       pensa gia' `useSearchTable` (refetch idempotente della pagina
//       corrente). Farlo anche qui manderebbe DUE richieste identiche, con le
//       risposte che possono tornare in ordine inverso. `ricaricaSempre` serve
//       ai due casi in cui nessun altro ricarica: il primo mount e il cambio di
//       rotta a coda invariata — che non esiste oggi, ma il giorno che nascesse
//       una terza porta sulla stessa coda il silenzio sarebbe una lista ferma.
function sincronizzaConLaRotta({ ricaricaSempre = false } = {}) {
  if (store.filters.coda !== props.coda) store.apriCoda(props.coda)
  else if (ricaricaSempre) store.fetchList()
}

// ⚠️ `onActivated` E NON SOLO `onMounted`: le viste vivono sotto KeepAlive, e
//    al rientro nella scheda `onMounted` non scatta piu' — la CODA resterebbe
//    quella di prima (memoria feedback_keepalive_onactivated). E' il cambio di
//    coda che va rifatto qui, non il caricamento dei dati.
watch(() => props.coda, () => sincronizzaConLaRotta({ ricaricaSempre: true }))
onMounted(() => sincronizzaConLaRotta({ ricaricaSempre: true }))
onActivated(() => sincronizzaConLaRotta())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <FiltriLista :store="store" :inert="perimetroBloccato">
          <!-- La ricerca: colonne dal catalogo (`ricerca_full`: senza colonne
               accese la casella non si rende), sotto 3 caratteri il termine
               non filtra. -->
          <template #sempre>
            <InputText
              v-model="searchText"
              class="app-filter-w-lg"
              :placeholder="t('common.search')"
            />
          </template>
          <Select
            v-model="codaCorrente"
            class="app-filter-w-md"
            :options="opzioniCoda"
            option-label="label"
            option-value="value"
          />
          <FiltroPeriodo :periodo="periodo" />
        </FiltriLista>
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ListaConfigStatusTag :dirty="dirty" />
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <ListaConfigurabile
        ref="listaRef"
        codice="pagamenti.righe"
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
        <template #cell-stato="{ data }">
          <Tag
            :value="data.stato_descrizione || data.stato_codice"
            :severity="statoRigaContabileSeverity(data.stato_codice)"
          />
        </template>

        <!-- ⭐ La forzatura e' un FATTO scritto sulla riga, non un'opinione: e'
             quello che l'elenco delle rate fuori capienza legge per esistere.
             Il motivo sta nella sua colonna, che il catalogo porta gia'. -->
        <template #cell-forzata="{ data }">
          <Tag
            v-if="data.forzata"
            :value="t('pagamenti.righe.forzata')"
            severity="warn"
          />
          <span v-else class="app-text-muted">—</span>
        </template>

        <!-- La rata abbinata, quando c'e'. ⚠️ Una riga puo' essere abbinata
             alla FATTURA senza rata: il vuoto e' uno stato legittimo, non un
             dato mancante. -->
        <template #cell-scadenza_numero_rata="{ data }">
          <span v-if="data.scadenza_numero_rata == null" class="app-text-muted">—</span>
          <span v-else>{{ data.scadenza_numero_rata }}</span>
        </template>

        <!-- ⚠️ Lo slot si chiama `#actions` e la colonna deve essere a catalogo
             (`tipo_colonna = azione`): col nome sbagliato, o senza la colonna,
             il kebab non si rende e non da' nessun errore. -->
        <template #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>

        <template #empty>
          <div class="app-empty-state">
            <i :class="STATUS_ICONS.TUTTO_OK" />
            <p>{{ t('pagamenti.righe.coda_vuota') }}</p>
          </div>
        </template>
      </ListaConfigurabile>

      <!-- ⭐ Un dialogo, due modi: «abbina» sotto una distinta aperta, «abbina e
           registra» (la tardiva) sotto una registrata. -->
      <AbbinaRigaDialog
        v-model:visible="abbinaVisible"
        :riga="rigaDaAbbinare"
        :modo="modoAbbina"
        @abbinata="store.fetchList()"
      />
    </template>
  </div>
</template>

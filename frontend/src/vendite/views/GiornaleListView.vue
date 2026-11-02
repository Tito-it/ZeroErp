<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il GIORNALE TRASVERSALE degli eventi (pezzo G del piano BE/FE
//        dell'osservabilita'): «cosa e' andato storto, su tutto, nell'ultimo
//        periodo» — la Storia di tutte le entita' insieme, filtrata per
//        gravita'. `<ListaConfigurabile codice="vendite.giornale">` con i
//        filtri della whitelist del backend (interruttore «solo errori»,
//        registro, tipo di entita', filo, date), export, e il kebab di riga
//        con «Apri …» via `core/bersagli.js` (LOTTO e FATTURA raggiungibili;
//        TASK_RUN e gli altri no ⇒ nessun pulsante, per la regola scritta).
//
// ⛔ Niente `context`/`payload` qui: la lista e' una vetrina, la Storia
//    dell'entita' (nel drawer che «Apri» raggiunge) e' il pezzo forense.
// ⚠️ Niente casella di ricerca: il backend non ha ricerca testuale.
// ⚠️ «Storia» come azione separata NON c'e' (scostamento dal piano §3.2,
//    dichiarato nel registro): nessun drawer sa aprirsi su una scheda, e
//    «Apri» porta al drawer dove la Storia e' una scheda — un pulsante che
//    facesse la stessa cosa con un altro nome sarebbe una promessa vuota.
import { onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useDebouncedAction } from '../../core/composables/useDebouncedAction'
import { useLookupEtichettato } from '../../core/composables/useLookupEtichettato'
import { useAuthStore } from '../../stores/auth'
import { azioniDaBersagli } from '../../core/bersaglioGesto'
import { useGiornaleStore, GRAVITA_SOLO_ERRORI, GRAVITA_CON_AVVISI } from '../stores/giornale'
import { exportGiornale } from '../api/giornale'
import GiornaleCella from '../_shared/giornale/GiornaleCella.vue'
import {
  CAMPO_CODICE_REGISTRO,
  GIORNALE_CELLE,
  SORGENTE_REGISTRI,
  SORGENTE_TIPI_ENTITA,
} from '../_shared/giornale/giornaleCelle'
import { READONLY_DOMAINS } from '../../core/constants'
import FiltroPeriodo from '../../core/components/FiltroPeriodo.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.VENDITE)
const store = useGiornaleStore()
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

// ⭐ I due vocabolari delle tendine si LEGGONO dal catalogo, e portano ciascuno
//    l'`etichetta_key` che il DB dichiara riga per riga — resa dal BB
//    `useLookupEtichettato` (ripiego fail-visible sul codice), che da' anche
//    l'etichetta di un codice gia' in riga per le colonne:
//    · i tipi di entita' da `config.tipi_entita` (lookup dedicato — la tabella
//      non ha `id`/`descrizione`): fino al 19-09 erano sette codici ricopiati a
//      mano, e il catalogo ne aveva gia' nove;
//    · i registri da `config.registri_giornale` (lookup generico, specializzato
//      con `etichetta_key`): fino al 19-09 erano un array qui, una costante nel
//      backend e quattro letterali nella vista — tre sedi che non si
//      conoscevano — e la tendina mostrava `EVENT_LOG` grezzo. Il quinto
//      registro e' una riga di CSV (+ il suo ramo nella vista): qui non cambia
//      niente. Brief: `work-done/brief-db-registri-giornale-catalogo.md`.
//    ⚠️ Registri: solo i VIVI (`includi_obsoleti: false`, come `obsoleto_dal IS
//       NULL` del lookup gemello) — un registro ritirato non ha piu' ramo nella
//       vista (il pgTAP del catalogo lo pretende), e in tendina sarebbe una
//       scelta vuota. La cache e' la stessa entry di un `<LookupSelect rel>`
//       sullo stesso insieme, per costruzione (`useLookupCodici`). Il valore
//       e' `codice_interno`, la chiave stabile che il backend valida.
// ⭐ Dal 2026-09-27 le due SORGENTI e le celle stanno in `_shared/giornale`
//    (`giornaleCelle`, `GiornaleCella`): la stessa lista si monta anche nella
//    Storia di fattura e lotto, e tendine e celle devono leggere la stessa
//    entry di cache. Qui restano le sole tendine.
const { opzioni: entitaOptions } = useLookupEtichettato(
  SORGENTE_TIPI_ENTITA,
  { tutti: () => t('vendite.giornale.filtro_entita_tutte') },
)
const { opzioni: registroOptions } = useLookupEtichettato(
  SORGENTE_REGISTRI,
  { campoCodice: CAMPO_CODICE_REGISTRO, tutti: () => t('vendite.giornale.filtro_registro_tutti') },
)

const {
  onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm,
} = useListaConfigurabilePage(store, {
  exportFn: exportGiornale,
  // Il file E' la lista: filtri e ordine dalla SEDE UNICA dello store
  // (`paramsFiltro`), non ricostruiti qui — la forma con cui l'export
  // perdeva filtri per strada (catalogo BB, `useListaStoreCore`).
  getExportParams: (fmt) => ({ formato: fmt, ...store.paramsFiltro() }),
  searchTableOptions: {
    defaultSortField: 'quando',
    defaultSortOrder: 'desc',
  },
})

const { bindSelect, bindToggle, bindPeriodo } = useStoreFilterBindings(store, applyFilters)
// Acceso = i soli ERROR (col NULL, che il backend include); spento = anche
// gli avvisi. Un interruttore che RESTRINGE: niente conteggio.
const { value: soloErrori, onChange: onSoloErroriChange } = bindToggle('gravita', {
  on: GRAVITA_SOLO_ERRORI, off: GRAVITA_CON_AVVISI,
})
const { value: registroFilter, onChange: onRegistroChange } = bindSelect('registro')
const { value: entitaFilter, onChange: onEntitaChange } = bindSelect('entity_type')
// Il periodo e' UN filtro con due estremi: un binding, un componente.
const periodo = bindPeriodo()

// Il filo (tx_id o correlation_id): testo con debounce, `Enter` applica subito.
const applicaFilo = useDebouncedAction(applyFilters, { detailed: true })
function onFiloInput(valore) {
  const pulito = (valore ?? '').trim()
  store.filters.filo = pulito === '' ? null : pulito
  applicaFilo.run()
}

// Scopo: le azioni di riga: «Apri …» dal resolver dei bersagli — l'UNICO
//        posto che sa quali entita' una schermata raggiunge. Un tipo senza
//        destinazione (TASK_RUN) non da' nessun pulsante, per la regola
//        scritta la'. La commessa e' gia' in `DESTINAZIONI`.
function buildRowActions(data) {
  if (!data.entity_type || data.entity_id == null) return []
  return azioniDaBersagli([{ tipo: data.entity_type, id: data.entity_id }], auth).map((a, i) => ({
    key: `apri-${i}`,
    label: a.label,
    icon: a.icon,
    command: a.esegui,
  }))
}

// Scopo: il deep-link `?tx_id=` (dal registro degli errori tecnici): scrive
//        il filo e ricarica. In `onActivated`, non in `onMounted`: sotto
//        KeepAlive il secondo arrivo non rimonta
//        (`feedback_keepalive_onactivated`). Senza query e' un rinfresco.
// ⚠️ La query si PULISCE dopo l'uso (`router.replace`, come `?open=` dei
//    lotti): lasciata li', ri-forzerebbe il filo a ogni ritorno sulla scheda
//    anche dopo che l'operatore l'ha tolto a mano — `?tx_id=` e' un ingresso,
//    non lo specchio dello stato (stessa regola di `useTabDaQuery`).
function applicaDeepLink() {
  const txId = typeof route.query.tx_id === 'string' ? route.query.tx_id.trim() : ''
  if (!txId) {
    store.fetchList()
    return
  }
  const query = { ...route.query }
  delete query.tx_id
  router.replace({ query })
  store.filters.filo = txId
  // Un filo attraversa qualunque data e qualunque gravita': si allarga.
  store.filters.data_da = null
  store.filters.gravita = GRAVITA_CON_AVVISI
  applyFilters()
}

onActivated(applicaDeepLink)
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <FiltroToggle
          v-model="soloErrori"
          :label="t('vendite.giornale.filtro_solo_errori')"
          :hint="t('vendite.giornale.filtro_solo_errori_hint')"
          @change="onSoloErroriChange"
        />
        <Select
          v-model="registroFilter"
          class="app-filter-w-md"
          :options="registroOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('vendite.giornale.col_registro')"
          @change="onRegistroChange"
        />
        <Select
          v-model="entitaFilter"
          class="app-filter-w-md"
          :options="entitaOptions"
          option-label="label"
          option-value="value"
          :placeholder="t('vendite.giornale.col_entita')"
          @change="onEntitaChange"
        />
        <InputText
          class="app-filter-w-lg"
          :model-value="store.filters.filo ?? ''"
          :placeholder="t('vendite.giornale.filtro_filo')"
          @update:model-value="onFiloInput"
          @keyup.enter="applicaFilo.flush()"
        />
        <FiltroPeriodo :periodo="periodo" />
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <!-- Il conto di cio' che il filtro toglie: senza, «nessun errore» e «tre
         errori, tutti ritirati» si leggono uguali. -->
    <p v-if="store.ritirateCount > 0" class="app-drawer-header-muted">
      {{ t('vendite.giornale.ritirate_nascoste', { n: store.ritirateCount }) }}
    </p>

    <ListaConfigurabile
      ref="listaRef"
      codice="vendite.giornale"
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
      <!-- ⭐ Le celle con una resa propria vengono dal componente CONDIVISO con la
           Storia di fattura e lotto (`GiornaleCella`, regola del 2): la stessa
           riga si legge uguale nelle due schermate. `quando` non ha slot: il
           seed dichiara `datetime_short`. -->
      <template v-for="codice in GIORNALE_CELLE" :key="codice" #[`cell-${codice}`]="{ data }">
        <GiornaleCella :codice="codice" :riga="data" />
      </template>
      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </ListaConfigurabile>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />
  </div>
</template>

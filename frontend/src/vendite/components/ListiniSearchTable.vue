<script setup>
// Scopo: Lista listini configurabile
//        (`<ListaConfigurabile codice="vendite.listini">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente.
// Row expansion: mostra le versioni del listino sotto la riga (default aperto).
//        E' un master-detail, quindi la pagina PILOTA l'espansione
//        (`v-model:expanded-rows`) invece di lasciarla alla lista: serve
//        "espandi tutte", il toggle da azione di riga e il fetch lazy delle
//        versioni. Il dettaglio sta nello slot `row-expansion`.
// Pulsanti riga listino: toggle versioni (chiude/apre expansion), test resolver.
// Mini-tabella versioni nell'expansion: + nuova versione, transizioni stato,
// gestione righe prezzo (apre VersioneDrawer dal parent).
import { ref, onMounted, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useListiniStore } from '../stores/listini'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { MANAGE_ICONS, TAB_ENTITIES, STATUS_ICONS } from '../../core/constants'
import { PASSAGGI_VERSIONE_LISTINO, PRICING_ACTIONS } from '../constants'
import { passaggioPermesso } from '../../core/utils/azioniPermesse'
import { statoVersioneListinoSeverity } from '../../core/utils/severity'
import { displayDate } from '../../core/utils/date'
import { deleteVersione, deleteListino } from '../api/listini'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useAzioneRiga } from '../../core/composables/useAzioneRiga'
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'
import Button from 'primevue/button'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import UtilityPerRuoloSelect from '../../core/components/UtilityPerRuoloSelect.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useInjectBlocked } from '../../core/composables/useReadonlyMode'
import { useAuthStore } from '../../stores/auth'
import AlertScadenzeWidget from './AlertScadenzeWidget.vue'
import AttivaVersioneDialog from './AttivaVersioneDialog.vue'
import ChiudiVersioneDialog from './ChiudiVersioneDialog.vue'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { buildAttivoOptions } from '../../core/utils/options'
import { useLookupCodici } from '../../core/composables/useLookupCodici'

const emit = defineEmits([
  'new',
  'row-click',
  'open-righe',
  'open-nuova-versione',
  'open-clona-versione',
  'test-resolver'
])

const { t } = useI18n()
const store = useListiniStore()
const { execute } = useApiHandler()
const isBlocked = useInjectBlocked()
const { confirmDelete } = useConfirmAction()

// ⭐ «Attiva» dal modello del documento (giro 12, FE-L1 di
//    brief-modello-documento-vendita §16.5):
//    - PERMESSO ⇒ nascondi: la voce c'è solo se il passaggio è tra quelli che
//      l'operatore può fare dallo stato della versione (`azioni_permesse`, dal
//      lettore del DB che applica l'azione `attiva_listino`; BB
//      `passaggioPermesso`, fail-closed: un campo assente non apre niente).
//    - STATO ⇒ spegni col motivo: il motivo è il primo della stessa `fn_check`
//      con cui il verbo rifiuta, nelle colonne che il registro delle azioni di
//      riga dichiara per `ATTIVA_VERSIONE_LISTINO` (BB `useAzioneRiga`).
//    ⛔ Prima la voce si spegneva qui sul conteggio delle righe (`righe_count`):
//    una copia della regola, che non sapeva della versione spenta.
const AZIONE_RIGA_ATTIVA_VERSIONE = 'ATTIVA_VERSIONE_LISTINO'
const attivazione = useAzioneRiga(AZIONE_RIGA_ATTIVA_VERSIONE)
// ⭐ «Elimina» e «Chiudi» allo stesso modo (§16.13 FE-E1, §16.16 FE-C1): spenti
//    col motivo dal registro, non più dal codice dello stato (R-L4 del §16.9).
//    Il motivo è il primo della `fn_check` con cui il verbo rifiuta (non in
//    bozza, usata da un documento; non attiva). «Clona» non ha motivo: si
//    clona da qualunque stato (C-1 = a), e la voce è sempre accesa.
const AZIONE_RIGA_ELIMINA_VERSIONE = 'ELIMINA_VERSIONE_LISTINO'
const AZIONE_RIGA_CHIUDI_VERSIONE = 'CHIUDI_VERSIONE_LISTINO'
const eliminazione = useAzioneRiga(AZIONE_RIGA_ELIMINA_VERSIONE)
const chiusura = useAzioneRiga(AZIONE_RIGA_CHIUDI_VERSIONE)
// Fase 5.F2: TestResolverDialog e' uno strumento DIAGNOSTICO (sviluppatori
// + admin). Non e' azione operativa: gate rigido su SUPER_ADMIN per non
// confondere gli operatori. Future: estendere a un'azione processo dedicata
// se servono ruoli intermedi (es. "supporto pricing").
const auth = useAuthStore()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions: pageActionsBase,
  perimetroBloccato,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'vendite.listini.nuovo_listino',
  onNew: () => emit('new'),
  // Allineato al preset del seed (`codice asc`).
  searchTableOptions: { defaultSortField: 'codice' },
  extraActions: () => extraPageActions.value,
})

// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
const { value: tipologiaFilter, onChange: onTipologiaChange } = bindSelect('tipologia_id')
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')

// Lookup tipologie listino per il filtro (non filtrato per utility: lista
// completa delle tipologie attive). Cache globale condivisa: ogni re-mount
// del componente (cambio tab, split-view) riusa la stessa fetch.
const tipologiaLookup = useLookupCodici('config.listini_tipologie', { immediate: true })

// ⭐ Dal BB (regola del 2, ok Tid 2026-09-23): la terna era scritta a mano qui
//    con le chiavi di `amministrazione`, cioe' un componente di `vendite` che
//    leggeva il vocabolario di un altro dominio. ⛔ E la tendina diceva
//    «Inattivo» mentre la colonna qui sotto, resa da `AttivoTag`, diceva «Non
//    attivo»: due parole per lo stesso stato nella stessa schermata.
const attivoOptions = buildAttivoOptions(t)

// Stato espansione righe (usato come v-model:expandedRows di PrimeVue).
// Ogni volta che la lista listini viene ricaricata, espandiamo tutte le righe
// e pre-carichiamo le versioni in parallelo.
// ⭐ Il pulsante «Espandi/Comprimi tutte» NON e' piu' qui (2026-09-18): e'
//    l'azione standard di `useListaAzioni`, che passa dal `v-model` di
//    `<ListaConfigurabile>` e quindi dallo stesso watch qui sotto. Questa era
//    la prima copia; ritirata alla seconda (regola del 2).
const expandedRows = ref({})

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

// Espande tutte le righe correntemente in lista. Il preload delle versioni
// viene gia' fatto dallo store dentro fetchList; qui ci limitiamo a mappare
// gli id correnti come "espansi" per il v-model:expandedRows di PrimeVue.
function expandAllRows() {
  const map = {}
  store.items.forEach(it => { map[it.id] = true })
  expandedRows.value = map
}

// Scopo: carica le versioni delle righe appena aperte che non le hanno in
// cache. Il preload dello store dentro `fetchList` copre il caso normale;
// questo e' la rete per quando fallisce — senza, il pannello resterebbe con lo
// spinner all'infinito, perche' nessun altro andrebbe a caricarle.
//
// Sta su un watch e non dentro un handler perche' i modi di aprire una riga
// sono piu' d'uno (chevron della lista, "espandi tutte", ripristino di stato):
// legarlo a un pulsante solo e' esattamente il difetto che aveva la versione
// precedente, dove il chevron apriva senza caricare nulla.
watch(expandedRows, (aperte) => {
  Object.keys(aperte || {})
    .filter(id => aperte[id] && !store.versioniByListino[id])
    .forEach(id => store.fetchVersioniListino(Number(id)))
})

// Stato dialog conferma attivazione (D3) — dichiarato prima delle funzioni
// che lo referenziano per evitare TDZ in caso di chiamata sincrona durante setup.
const attivaDialogVisible = ref(false)
const attivaDialogVersione = ref(null)
const attivaDialogListinoId = ref(null)

// Stato dialog programma chiusura (PATCH valido_al su ATTIVA)
const chiusuraDialogVisible = ref(false)
const chiusuraDialogVersione = ref(null)
const chiusuraDialogListinoId = ref(null)

function onChiudiVersione(versione, listinoId) {
  chiusuraDialogVersione.value = versione
  chiusuraDialogListinoId.value = listinoId
  chiusuraDialogVisible.value = true
}

async function onChiusuraSaved({ listinoId }) {
  await store.invalidateVersioniListino(listinoId)
}

// Transizione BOZZA -> ATTIVA: passa per dialog di conferma con preview
// auto-close (D3). Il dialog chiama dry_run prima della conferma reale.
function onAttivaVersione(versione, listinoId) {
  attivaDialogVersione.value = versione
  attivaDialogListinoId.value = listinoId
  attivaDialogVisible.value = true
}

async function onAttivaConfirmed({ listinoId }) {
  await store.invalidateVersioniListino(listinoId)
}

// O2: elimina una versione in stato BOZZA con conferma utente (il verbo del DB
// cancella anche righe e componenti, e rifiuta col suo codice).
function onEliminaVersione(versione, listino) {
  confirmDelete(versione.codice_versione, async () => {
    const result = await execute(
      () => deleteVersione(listino.id, versione.id),
      { successMessage: t('vendite.listini.versione_eliminata') },
    )
    if (result !== null) {
      await store.invalidateVersioniListino(listino.id)
      await store.fetchList()
    }
  })
}

// O3: elimina un listino mai usato (zero versioni).
// Il pulsante e' visibile solo se versioni_count=0; il guard backend
// e' la fonte di verita' (un check FE serve solo a ridurre i click sbagliati).
function onEliminaListino(listino) {
  confirmDelete(listino.codice, async () => {
    const result = await execute(
      () => deleteListino(listino.id),
      { successMessage: t('vendite.listini.listino_eliminato') },
    )
    if (result !== null) {
      await store.fetchList()
    }
  })
}

// Scopo: azioni utility SPECIFICHE di questa pagina, inserite dallo scaffolding
// prima di "Nuovo". Reload/personalizza/new arrivano da
// `useListaConfigurabilePage`, che le tiene una volta sola per tutte le liste.
const extraPageActions = computed(() => [
  {
    key: 'test-prezzo',
    kind: 'utility',
    label: t('vendite.listini.test_prezzo'),
    icon: MANAGE_ICONS.TEST_PREZZO,
    severity: 'info',
    // Strumento diagnostico: oltre al SUPER_ADMIN (bypass) lo apriamo a chi
    // puo' fare override manuale del prezzo (azione `prezzo_override_manuale`).
    // Razionale: chi puo' overridere il prezzo deve poter testare cosa propone
    // il listino prima di decidere — gli operatori "puri" senza override non
    // ne hanno bisogno e il pulsante resta nascosto.
    visible: auth.isSuperAdmin || auth.isActionAllowed(PRICING_ACTIONS.OVERRIDE),
    command: () => emit('test-resolver'),
  },
])

const pageActions = pageActionsBase

// Scopo: azioni di riga del listino. Niente toggle versioni: ad aprire e
// chiudere la riga ci pensa il chevron di `<ListaConfigurabile>`, a sinistra.
// Prima della conversione quel chevron non c'era e il toggle stava qui; averli
// entrambi non era solo ridondante — i due comandi si disallineavano a video e,
// peggio, solo questo caricava le versioni mancanti.
function buildListinoActions(data) {
  return [
    {
      key: 'elimina-listino',
      label: t('vendite.listini.elimina_listino'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: !data.versioni_count,
      command: () => onEliminaListino(data),
    },
  ]
}

// Scopo: azioni di riga della versione listino nell'expansion, secondo lo stato
//        del DATABASE (giro 12, FE-L2): fra la fine e il passaggio del job una
//        versione è ATTIVA con la chiusura programmata, e si mostra così.
//        ⛔ Ritirato lo «stato visibile» (`statoVersioneVisibile`), che la
//        dichiarava CHIUSA dalla data: una seconda regola della chiusura.
function buildVersioneActions(ver, listino) {
  return [
    {
      key: 'attiva',
      label: t('vendite.listini.attiva'),
      icon: MANAGE_ICONS.PUBLISH,
      severity: 'primary',
      visible: passaggioPermesso(ver, PASSAGGI_VERSIONE_LISTINO.ATTIVA),
      disabled: attivazione.bloccata(ver),
      tooltip: attivazione.motivo(ver),
      command: () => onAttivaVersione(ver, listino.id),
    },
    {
      key: 'chiudi',
      label: t('vendite.listini.chiudi'),
      icon: MANAGE_ICONS.CLOSE,
      severity: 'warn',
      disabled: chiusura.bloccata(ver),
      tooltip: chiusura.motivo(ver),
      command: () => onChiudiVersione(ver, listino.id),
    },
    {
      key: 'clona',
      label: t('vendite.listini.clona_versione'),
      icon: MANAGE_ICONS.CLONE,
      command: () => emit('open-clona-versione', ver, listino),
    },
    {
      key: 'gestisci-righe',
      label: t('vendite.listini.gestisci_righe'),
      icon: MANAGE_ICONS.RIGHE,
      command: () => emit('open-righe', ver, listino),
    },
    {
      key: 'elimina-versione',
      label: t('vendite.listini.elimina_versione'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      disabled: eliminazione.bloccata(ver),
      tooltip: eliminazione.motivo(ver),
      command: () => onEliminaVersione(ver, listino),
    },
  ]
}

useTabFreshness(store, TAB_ENTITIES.LISTINO)

// Dopo ogni assegnazione di items (fetchList completato e preload versioni
// gia' fatto dal store), aggiorna la mappa expandedRows per espandere tutto.
watch(() => store.items, expandAllRows, { flush: 'post' })

onMounted(() => store.fetchList())
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText class="app-filter-w-lg" v-model="searchText" :placeholder="t('vendite.listini.search_placeholder')" />
        </template>
        <UtilityPerRuoloSelect v-model="utilityFilter"
          class="app-filter-w-md"
          :placeholder="t('vendite.listini.filtro_utility')" :show-clear="true"
          apply-default
          @change="onUtilityChange" />
        <Select v-model="tipologiaFilter" :options="tipologiaLookup.items.value"
          option-label="descrizione" option-value="id"
          :placeholder="t('vendite.listini.filtro_tipologia')" :show-clear="true"
          :loading="tipologiaLookup.loading.value"
          @change="onTipologiaChange" class="app-filter-select app-filter-w-md" />
        <Select v-model="attivoFilter" :options="attivoOptions" option-label="label" option-value="value"
          class="app-filter-w-sm"
          :placeholder="t('vendite.listini.col_attivo')" @change="onAttivoChange" />
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #prefix>
          <AlertScadenzeWidget />
        </template>
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
          <ReadonlyBadge />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="vendite.listini"
      v-model:expanded-rows="expandedRows"
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
      <template #cell-utility_descrizione="{ data }">
        <span>{{ data.utility_descrizione || t('vendite.listini.commercio') }}</span>
      </template>
      <template #cell-tipologia_descrizione="{ data }">
        <span>{{ data.tipologia_descrizione || '—' }}</span>
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>

      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildListinoActions(data)" />
      </template>

      <template #row-expansion="{ data: listino }">
        <div class="app-row-expansion">
          <div class="app-row-expansion__header">
            <span class="app-row-expansion__title">
              <i :class="MANAGE_ICONS.VERSIONI"></i>
              {{ t('vendite.listini.tab_versioni') }} ({{ store.versioniByListino[listino.id]?.length ?? 0 }})
            </span>
            <Button :icon="MANAGE_ICONS.ADD" :label="t('vendite.listini.nuova_versione')"
              text size="small" class="app-action-btn"
              @click.stop="emit('open-nuova-versione', listino)" />
          </div>

          <div v-if="!store.versioniByListino[listino.id]" class="app-loading">
            <i :class="STATUS_ICONS.CARICAMENTO" />
          </div>
          <div v-else-if="store.versioniByListino[listino.id].length === 0" class="app-empty-state">
            <i :class="MANAGE_ICONS.VERSIONI" />
            <p>{{ t('vendite.listini.nessuna_versione_inline') }}</p>
          </div>
          <DataTable v-else
            :value="store.versioniByListino[listino.id]"
            class="app-datatable app-datatable--inner"
            striped-rows data-key="id"
          >
            <Column field="codice_versione" :header="t('vendite.listini.col_codice_versione')" style="width: 140px;" />
            <Column :header="t('vendite.listini.field_valido_dal')" style="width: 110px;">
              <template #body="{ data: ver }">{{ displayDate(ver.valido_dal) }}</template>
            </Column>
            <Column :header="t('vendite.listini.field_valido_al')" style="width: 110px;">
              <template #body="{ data: ver }">{{ displayDate(ver.valido_al) || '—' }}</template>
            </Column>
            <Column field="righe_count" :header="t('vendite.listini.col_righe')" style="width: 80px;" />
            <Column :header="t('vendite.listini.col_stato')" style="width: 110px;">
              <template #body="{ data: ver }">
                <Tag :value="ver.stato" :severity="statoVersioneListinoSeverity(ver.stato)" />
                <!-- La chiusura programmata la dice il backend (ATTIVA con la
                     fine scritta): il job la chiude quando la fine passa. -->
                <i v-if="ver.chiusura_programmata" :class="MANAGE_ICONS.CLOSE" class="ml-05 app-text-muted"
                  v-tooltip.top="t('vendite.listini.chiusura_programmata_al', { data: displayDate(ver.valido_al) })" />
              </template>
            </Column>
            <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false" frozen alignFrozen="right">
              <template #body="{ data: ver }">
                <RowActionsMenu :row="ver" :actions="buildVersioneActions(ver, listino)" />
              </template>
            </Column>
          </DataTable>
        </div>
      </template>
    </ListaConfigurabile>

    <AttivaVersioneDialog
      :visible="attivaDialogVisible"
      @update:visible="v => attivaDialogVisible = v"
      :listino-id="attivaDialogListinoId"
      :versione="attivaDialogVersione"
      @confirmed="onAttivaConfirmed"
    />

    <ChiudiVersioneDialog
      :visible="chiusuraDialogVisible"
      @update:visible="v => chiusuraDialogVisible = v"
      :listino-id="chiusuraDialogListinoId"
      :versione="chiusuraDialogVersione"
      @saved="onChiusuraSaved"
    />
    </template>
  </div>
</template>

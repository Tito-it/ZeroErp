<script setup>
// Scopo: Lista listini configurabile
//        (`<ListaConfigurabile codice="vendite.listini">`): colonne, ordine e
//        visibilita' dal catalogo `ui.lista_colonna`, con ritiro dinamico e
//        personalizzazione per utente.
// ⛔ Niente piu' riga espansa con le versioni (ritirata il 2026-10-31,
//    brief-db-liste-datatable-grezze-secondo-giro riga 5): era una `DataTable`
//    per listino, con la collezione intera delle versioni di ogni listino
//    della pagina. Le versioni e il loro ciclo di vita sono il tab «Versioni»
//    del drawer listino (`ListinoVersioniTab`).
// ⭐ «In scadenza senza successore» e' la regola del DB: la colonna
//    `giorni_alla_scadenza` e il filtro `in_scadenza`, che il badge
//    (`AlertScadenzeWidget`) accende al clic (D-1).
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useListiniStore } from '../stores/listini'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useTabFreshness } from '../../core/composables/useTabFreshness'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { MANAGE_ICONS, TAB_ENTITIES } from '../../core/constants'
import { PRICING_ACTIONS } from '../constants'
import { deleteListino } from '../api/listini'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import InputText from 'primevue/inputtext'
import Select from 'primevue/select'
import AttivoTag from '../../core/components/AttivoTag.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
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
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { buildAttivoOptions } from '../../core/utils/options'
import { useLookupCodici } from '../../core/composables/useLookupCodici'

const emit = defineEmits(['new', 'row-click', 'test-resolver'])

const { t } = useI18n()
const store = useListiniStore()
const { execute } = useApiHandler()
const isBlocked = useInjectBlocked()
const { confirmDelete } = useConfirmAction()

// Fase 5.F2: TestResolverDialog e' uno strumento DIAGNOSTICO (sviluppatori
// + admin). Non e' azione operativa: gate rigido su SUPER_ADMIN per non
// confondere gli operatori. Future: estendere a un'azione processo dedicata
// se servono ruoli intermedi (es. "supporto pricing").
const auth = useAuthStore()
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions: pageActionsBase,
  perimetroBloccato, reload,
} = useListaConfigurabilePage(store, {
  newTooltipKey: 'vendite.listini.nuovo_listino',
  onNew: () => emit('new'),
  // Allineato al preset del seed (`codice asc`).
  searchTableOptions: { defaultSortField: 'codice' },
  extraActions: () => extraPageActions.value,
  // «Ricarica» riallinea anche il badge: lista e conteggio sono la stessa
  // fotografia. ⚠️ Arrow lazy: `reload` e `ricaricaBadge` si risolvono al clic.
  onReload: () => { reload(); ricaricaBadge() },
})

// ⭐ I FILTRI PASSANO DAI BINDER, e non e' una preferenza di stile: `bindSelect`
//    porta con se' il `watch` store → widget, cioe' l'unico modo perche' la
//    casella dica la verita' quando il filtro viene cambiato da FUORI —
//    «Pulisci filtri» del drawer, un deep-link, un reset. Scritti a mano (un
//    `ref` che spinge nello store e basta) il filtro si pulisce e la combo
//    continua a mostrare il valore di prima, senza nessun errore.
const { bindSelect, bindToggle } = useStoreFilterBindings(store, applyFilters)
const { value: utilityFilter, onChange: onUtilityChange } = bindSelect('utility_id')
const { value: tipologiaFilter, onChange: onTipologiaChange } = bindSelect('tipologia_id')
const { value: attivoFilter, onChange: onAttivoChange } = bindSelect('attivo')
const { value: soloInScadenza, onChange: onSoloInScadenzaChange } = bindToggle('in_scadenza')

// Il badge accende il filtro: la casella lo mostra (binder store → widget) e
// lo si spegne da li' o da «Pulisci filtri».
function onFiltraScadenze() {
  soloInScadenza.value = true
  onSoloInScadenzaChange()
}
// ⭐ Il badge conta con GLI STESSI filtri della lista (il clic accende
//    `in_scadenza` sopra di loro): la stessa forma della fetch
//    (`paramsFiltro`), senza ordinamento — non cambia il numero — e senza
//    `in_scadenza`, che il widget mette da se'. La paginazione `paramsFiltro`
//    non la porta. Cambiano i filtri → il widget si rilegge da solo.
// ⛔ Fino al 2026-10-31 si rileggeva a ogni `store.items` (ogni pagina, ogni
//    ordinamento, due volte al montaggio) e contava col solo `in_scadenza`.
const FUORI_DAL_BADGE = ['order_by', 'order_dir', 'in_scadenza']
const filtriBadge = computed(() => Object.fromEntries(
  Object.entries(store.paramsFiltro()).filter(([k]) => !FUORI_DAL_BADGE.includes(k)),
))
const alertRef = ref(null)
// Scopo: a filtri fermi il conteggio cambia con le versioni (un successore
//        toglie un listino) o con un listino salvato: lo chiede la vista.
function ricaricaBadge() {
  alertRef.value?.load()
}
// Un listino cambiato da un'altra scheda: la lista si rilegge
// (`useTabFreshness`, sotto), e il badge con lei.
const { onDataChanged } = useTabEvents()
const smettiDiAscoltare = onDataChanged((e) => {
  if (e.entityType === TAB_ENTITIES.LISTINO) ricaricaBadge()
})
onUnmounted(smettiDiAscoltare)
defineExpose({ ricaricaBadge })

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

// `<ListaConfigurabile>` emette `data` direttamente (non l'evento PrimeVue).
function onRowClick(data) { emit('row-click', data) }

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

useTabFreshness(store, TAB_ENTITIES.LISTINO)

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
        <FiltroToggle v-model="soloInScadenza"
          :label="t('vendite.listini.filtro_in_scadenza')"
          @change="onSoloInScadenzaChange" />
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #prefix>
          <AlertScadenzeWidget ref="alertRef" :filtri="filtriBadge" @filtra="onFiltraScadenze" />
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
    </ListaConfigurabile>

    </template>
  </div>
</template>

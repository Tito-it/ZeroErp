<script setup>
// Scopo: Sub-drawer per gestione distinta base (BoM) articolo.
// Layout: la distinta come LISTA CONFIGURABILE `catalogo.articolo_componenti`
// (lista 101: colonne dal catalogo, ritiro nella riga espandibile,
// personalizzazione, ricerca, export) + form inline sotto la lista.
//
// ⭐ DAL 2026-09-28 E' UNA LISTA STANDARD (brief-db-liste-righe-documento,
//    lotto C). Prima era una `DataTable` grezza con filtri LOCALI sulle righe
//    gia' caricate: su tablet le colonne uscivano in uno scroll orizzontale,
//    e con la paginazione il filtro avrebbe filtrato la sola pagina. Ora
//    ricerca e «in vigore al» sono parametri dell'endpoint
//    (`…/componenti/lista/`), e la macchina del form e' il BB `useFormInline`
//    (sede unica): il cambio di articolo chiude il form, «Nuovo» sparisce a
//    form aperto.
//
// Pattern immutabilità (sviluppo-listini-v5 §14.4 / DEC-4):
//   - i campi struttura (componente, coeff_qta, esposizione_in_fattura, ecc.)
//     non sono modificabili in place: trigger DB E_BOM_MODIFICA_VIETATA li
//     blocca. Per cambiare valori si usa "chiudi riga" + nuovo "Aggiungi
//     componente" con i nuovi parametri (operazioni esplicite, intenzionali).
//     Per questo il click su una riga apre il form in SOLA LETTURA (il modo
//     `edit` del BB e' qui la consultazione).
//   - "Duplica versione" (workflow 2 step, dal 2026-05-10): step 1 chiude la
//     sorgente con PATCH valido_al (stessa via di "Chiudi riga"), step 2
//     apre il form add pre-compilato dai valori della sorgente con
//     valido_dal = chiudi_al + 1. L'utente puo' modificare i campi prima
//     di salvare. Niente DB function dedicata: tutto su endpoint esistenti
//     (PATCH valido_al + POST create), con perdita di atomicita' DB-side
//     accettata (eventuale annullo dello step 2 lascia la sorgente chiusa
//     senza nuova versione, recuperabile manualmente con "+").
//   - delete BoM bloccato dal trigger: il pattern di "rimozione" è chiusura
//     con valido_al = oggi (chiusura immediata) o data futura (programmata),
//     unica via via dialog dedicato dal kebab "Chiudi riga" (pattern
//     simmetrico a ChiudiVersioneDialog dei listini, vedi
//     feedback_stato_terminale_con_data).

import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { useFormInline } from '../../core/composables/useFormInline'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { paramBool, paramNumber, paramString } from '../../core/utils/parameterCast'
import {
  createArticoloComponente,
  updateArticoloComponente,
  exportArticoloComponentiLista,
  makeComponenteNotesApi,
} from '../api/catalogo'
import { useArticoloComponentiStore } from '../stores/articoloComponenti'
import { useEsposizioniComponente, ESPOSIZIONE_NASCOSTO } from '../composables/useEsposizioniComponente'
import { DRAWER_WIDTH, DATE_FORMAT, MANAGE_ICONS } from '../../core/constants'
import { addDaysToToday, displayDate, parseIsoDate, toDateString, giornoDi, oggiAziendale } from '../../core/utils/date'
import ArticoloLookup from './ArticoloLookup.vue'
import NoteDrawer from '../../core/components/NoteDrawer.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import FiltroToggle from '../../core/components/FiltroToggle.vue'
import AppDialog from '../../core/components/AppDialog.vue'
import Message from 'primevue/message'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import Select from 'primevue/select'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading, campiErrati } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null }
})

const emit = defineEmits(['update:visible', 'saved'])

const store = useArticoloComponentiStore()

// Defaults BoM via config.parameters (override per emittente).
// Pre-fetch al setup; la watch su `props.visible` await-a comunque per
// evitare race "drawer aperto con fallback hardcoded mentre la fetch e' in volo".
// Fallback hardcoded coincide col comportamento pre-refactor: se i parametri
// non sono ancora seedati nel DB, nessuna regressione.
const { defaults: paramDefaults, load: loadDefaults } = useParameterDefaults([
  'CATALOGO_BOM_DEFAULT_COEFF_QTA',
  'CATALOGO_BOM_DEFAULT_OBBLIGATORIO',
  'CATALOGO_BOM_DEFAULT_ESPOSIZIONE_IN_FATTURA',
])
loadDefaults()

// I tre modi di esporre il componente in fattura, con l'etichetta dal DB.
const { opzioni: esposizioniOptions, etichetta: etichettaEsposizione } = useEsposizioniComponente()

// La macchina del form (BB `useFormInline`): `create` = nuovo componente (anche
// la nuova versione del Duplica), `edit` = la riga aperta in SOLA LETTURA.
// ⭐ Il padre porta anche la visibilita': chiudere il drawer, o aprire un
//    altro articolo, chiude il form.
const {
  formMode, rigaInModifica, formAperto,
  nuovaRiga, apriRiga, chiudiForm, ancoraForm, azioneNuovaRiga,
} = useFormInline({
  padre: () => (props.visible ? props.articoloId : null),
  puoModificare: () => !isReadonly.value,
  // D-8: cambiare riga col form modificato chiede (il getter e' letto al clic).
  confermaCambio: (p) => chiudiConConferma(p),
})
const isFormReadonly = computed(() => formMode.value === 'edit')

// Form inserimento nuovo componente
const form = ref({})
const componenteObj = ref(null)
// Modifiche non salvate del form inline «nuovo componente» (anche la nuova
// versione del Duplica). Il dettaglio in sola lettura non ha niente da
// salvare: resta fuori.
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, {
  visibile: () => props.visible && formMode.value === 'create',
})

// ⚠️ `parentId` porta l'id SOLO a drawer aperto: il `null` alla chiusura
//    chiama `store.reset()`, o la distinta dell'articolo precedente
//    lampeggerebbe sotto la prossima.
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm, reloadAll,
} = useDrawerTabLista(store, {
  parentId: () => (props.visible ? props.articoloId : null),
  parentField: 'articoloId',
  // L'export segue la lista a video: filtro di validita', ricerca, ordinamento.
  exportFn: (params) => exportArticoloComponentiLista(props.articoloId, params),
  getExportParams: (formato) => ({ formato, ...store.paramsExport() }),
  // «Nuovo» fra le azioni della lista: sparisce a form aperto (BB).
  // ⚠️ Arrow lazy: la legge il computed delle azioni, non il setup.
  extraActions: () => [
    azioneNuovaRiga({
      key: 'new',
      label: t('common.new'),
      tooltip: t('catalogo.aggiungi_componente'),
      command: startAdd,
    }),
  ],
})

// ⭐ IL FILTRO «IN VIGORE AL» E' UNO, con il suo interruttore: la data e
//    «tutte le versioni» sono lo stesso filtro `valido_al` dello store (null =
//    tutte). Scrivere una data spegne l'interruttore; svuotarla torna a oggi,
//    perche' «nessuna data» e' l'interruttore, non la casella.
const oggi = () => addDaysToToday(0)
const { bindDate } = useStoreFilterBindings(store, applyFilters)
const { value: dataValida, onChange: onDataValidaChange } = bindDate('valido_al', { clearTo: oggi })
const tutteLeVersioni = computed({
  get: () => store.filters.valido_al == null,
  set: (acceso) => { store.filters.valido_al = acceso ? null : toDateString(oggi()) },
})

// Dialog chiusura riga (pattern simmetrico a ChiudiVersioneDialog).
// L'admin sceglie data di chiusura (oggi = immediata, futura = programmata).
// Min-date e default-date arrivano DAL BE come capability di riga
// (`data_min_chiusura`, `data_default_chiusura` su vw_articoli_componenti_dettaglio,
// sede unica dal 2026-09-28). Niente ricalcolo lato FE.
const chiudiDialogVisible = ref(false)
const chiudiDialogRow = ref(null)
const chiudiDialogData = ref(null)
const chiudiDialogMinDate = computed(() => parseIsoDate(chiudiDialogRow.value?.data_min_chiusura))
const chiudiDialogIsImmediata = computed(() => isOggi(chiudiDialogData.value))

// Dialog "Duplica versione": l'admin sceglie chiudi_al, alla conferma il
// BE chiude SOLO la sorgente (PATCH valido_al, stessa path di "Chiudi
// riga", trigger BoM lo permette). Subito dopo il drawer apre il form
// "Aggiungi componente" pre-compilato dai valori della sorgente, con
// `valido_dal = chiudi_al + 1`. L'utente puo' modificare i campi prima
// di salvare, e il save fa l'INSERT della nuova versione.
// Min-date dialog: BE espone `data_min_chiusura` (= valido_dal della sorgente).
const duplicaDialogVisible = ref(false)
const duplicaDialogRow = ref(null)
const duplicaDialogChiudiAl = ref(null)
// Stato del flow duplica post-chiusura: se != null, il form add e' stato
// aperto pre-compilato dalla sorgente (titolo + banner dedicato).
const duplicaFlowSource = ref(null)
const duplicaDialogMinDate = computed(() => parseIsoDate(duplicaDialogRow.value?.data_min_chiusura))
const duplicaDialogIsImmediata = computed(() => isOggi(duplicaDialogChiudiAl.value))

// Sub-drawer note per componente (BB partizionato NoteDrawer +
// makeComponenteNotesApi). apiClient reattivo a `noteCompId`: il padre della
// lista del drawer e' il suo `basePath`, che cambia col componente.
const noteDrawerVisible = ref(false)
const noteCompId = ref(null)

const noteApiClient = computed(() => {
  if (!props.articoloId || !noteCompId.value) return null
  return makeComponenteNotesApi(props.articoloId, noteCompId.value)
})

function openNoteDrawer(row) {
  noteCompId.value = row.id
  noteDrawerVisible.value = true
}

function defaultForm() {
  const p = paramDefaults.value
  return {
    componente_id: null,
    coeff_qta: paramNumber(p.CATALOGO_BOM_DEFAULT_COEFF_QTA, 1),
    obbligatorio: paramBool(p.CATALOGO_BOM_DEFAULT_OBBLIGATORIO, true),
    // Un CODICE di `config.esposizioni_componente` (dal 2026-10-01 non e' piu'
    // un booleano): il parametro lo valida il registro FK surrogata.
    esposizione_in_fattura: paramString(p.CATALOGO_BOM_DEFAULT_ESPOSIZIONE_IN_FATTURA, ESPOSIZIONE_NASCOSTO),
    // valido_dal: null (Fase 4 BE-only). Se l'admin non sceglie una data,
    // il service applica today come default. Il DatePicker resta vuoto
    // finche' l'utente non interagisce: piu' onesto rispetto al pre-fill che
    // mascherava la responsabilita' del default.
    valido_dal: null,
    valido_al: null,
  }
}

// I flag booleani della riga, nell'ordine del form. ⚠️ `labelKey` LETTERALE e
// completa: e' la forma che `scripts/check_i18n_keys.py` sa verificare.
// `partecipa_qta` e `determina_qta_padre` ritirati il 2026-10-02: nessuna
// logica li leggeva (brief-db-bom-flag-quantita-e-kit-in-fattura, D-1).
const FLAG_COMPONENTE = [
  { campo: 'obbligatorio', labelKey: 'catalogo.field_obbligatorio' },
]

// Scopo: i valori di una riga nel form (dettaglio in sola lettura e
//        precompilazione del Duplica). Una sede per la mappatura riga → form.
function formDaRiga(row, { validoDal, validoAl }) {
  form.value = {
    componente_id: row.componente_id,
    coeff_qta: row.coeff_qta,
    obbligatorio: row.obbligatorio,
    esposizione_in_fattura: row.esposizione_in_fattura,
    valido_dal: validoDal,
    valido_al: validoAl,
  }
  componenteObj.value = {
    id: row.componente_id,
    codice: row.componente_codice,
    descrizione: row.componente_descrizione,
  }
}

// Scopo: la data scelta e' oggi? (chiusura immediata contro programmata)
function isOggi(val) {
  if (!val) return false
  const sel = giornoDi(val)
  return sel !== null && sel.getTime() === oggi().getTime()
}

watch(() => props.visible, async (val) => {
  if (!val) return
  // Attendi i parameters prima di resettare il form (race-fix simmetrico
  // a ArticoloUomDrawer): evita form costruito con fallback hardcoded
  // mentre la fetch dei defaults e' ancora in volo.
  await loadDefaults()
  form.value = defaultForm()
  componenteObj.value = null
  duplicaFlowSource.value = null
})

// La riga aperta in sola lettura: il form la mostra com'e'.
watch(rigaInModifica, (row) => {
  if (!row) return
  duplicaFlowSource.value = null
  formDaRiga(row, { validoDal: parseIsoDate(row.valido_dal), validoAl: parseIsoDate(row.valido_al) })
})

// Scopo: Callback quando l'utente seleziona un articolo dal lookup.
function onComponenteSelect(item) {
  componenteObj.value = item
  form.value.componente_id = item?.id || null
}

// Scopo: «Nuovo»: il form vuoto coi default dei parametri. E' il `command` di
//        `azioneNuovaRiga`: fa di piu' (azzera, fotografa), e per aprire chiama
//        il verbo del BB.
function startAdd() {
  form.value = defaultForm()
  componenteObj.value = null
  duplicaFlowSource.value = null
  nuovaRiga()
  fissa()
}

// Annulla del form inline: con modifiche chiede conferma.
const annullaAdd = () => chiudiConConferma(chiudiForm)

// Clic su una riga col form aperto: il dettaglio prende il posto del form, e
// con modifiche chiede conferma come l'Annulla — lo fa il BB (`confermaCambio`
// di useFormInline, D-8), che prima qui era scritto a mano.
const onRowClick = (row) => apriRiga(row)

// Scopo: apre il dialog "Duplica versione". Default `chiudi_al = oggi` ->
// chiusura immediata, nuova riga apre domani.
function onDuplicaVersione(row) {
  duplicaDialogRow.value = row
  duplicaDialogChiudiAl.value = oggiAziendale()
  duplicaDialogVisible.value = true
}

function annullaDuplicaVersione() {
  duplicaDialogVisible.value = false
  duplicaDialogRow.value = null
  duplicaDialogChiudiAl.value = null
}

// Scopo: step 1 del flow duplica-versione. Chiude SOLO la sorgente con
// PATCH valido_al (endpoint esistente updateArticoloComponente, stesso
// path di "Chiudi riga"). Su successo apre il form add pre-compilato
// dai valori della sorgente, con valido_dal = chiudi_al + 1. L'utente
// modifica i campi se serve e su Save l'endpoint create inserisce la
// nuova versione (step 2).
async function confermaDuplicaVersione() {
  if (!duplicaDialogRow.value || !duplicaDialogChiudiAl.value) return
  const chiudiAlDate = giornoDi(duplicaDialogChiudiAl.value)
  const chiudiAlIso = toDateString(chiudiAlDate)
  // Snapshot della sorgente prima di chiudere il dialog: serve a
  // pre-compilare il form quando duplicaDialogRow viene azzerata.
  const sourceRow = { ...duplicaDialogRow.value }

  const result = await execute(
    () => updateArticoloComponente(props.articoloId, sourceRow.id, {
      valido_al: chiudiAlIso,
    }),
    { successMessage: t('catalogo.componente_chiuso') },
  )
  if (result === null) return
  annullaDuplicaVersione()
  reloadAll()
  emit('saved')

  // Apre il form add pre-compilato. valido_dal default = chiudi_al + 1
  // (la nuova versione apre il giorno successivo alla chiusura, evita
  // overlap col range chiuso). Tutti i campi sono editabili.
  const nextDay = new Date(chiudiAlDate.getTime())
  nextDay.setDate(nextDay.getDate() + 1)

  nuovaRiga()
  formDaRiga(sourceRow, { validoDal: nextDay, validoAl: null })
  duplicaFlowSource.value = {
    chiudi_al: chiudiAlIso,
    componente_codice: sourceRow.componente_codice,
  }
  fissa()
}

const canSaveForm = computed(() => {
  return form.value.componente_id != null && form.value.coeff_qta > 0
})

// Scopo: Inserisce nuovo componente. Ricarica lista e notifica il parent.
async function onSaveNew() {
  const payload = {
    componente_id: form.value.componente_id,
    coeff_qta: form.value.coeff_qta,
    obbligatorio: form.value.obbligatorio,
    esposizione_in_fattura: form.value.esposizione_in_fattura,
    valido_dal: toDateString(form.value.valido_dal),
    valido_al: toDateString(form.value.valido_al),
  }
  const result = await execute(
    () => createArticoloComponente(props.articoloId, payload),
    { successMessage: t('catalogo.componente_aggiunto') }
  )
  if (result === null) return
  chiudiForm()
  duplicaFlowSource.value = null
  reloadAll()
  emit('saved')
}

// Scopo: apre il dialog di chiusura riga BoM con DatePicker. Default oggi
// (chiusura immediata), futura ammessa (chiusura programmata). Min-date e
// default-date dalla capability di riga della vista.
// Il delete BoM resta bloccato dal trigger DB E_BOM_MODIFICA_VIETATA.
function onChiudiRiga(row) {
  chiudiDialogRow.value = row
  chiudiDialogData.value = parseIsoDate(row.data_default_chiusura) || oggiAziendale()
  chiudiDialogVisible.value = true
}

function annullaChiusura() {
  chiudiDialogVisible.value = false
  chiudiDialogRow.value = null
  chiudiDialogData.value = null
}

async function confermaChiusura() {
  if (!chiudiDialogRow.value || !chiudiDialogData.value) return
  const result = await execute(
    () => updateArticoloComponente(props.articoloId, chiudiDialogRow.value.id, {
      valido_al: toDateString(chiudiDialogData.value),
    }),
    { successMessage: t('catalogo.componente_chiuso') }
  )
  if (result !== null) {
    annullaChiusura()
    reloadAll()
    emit('saved')
  }
}

// Scopo: azioni di riga del componente BoM (note + duplica + chiudi).
// Nascoste in readonly. La voce "elimina" non esiste: la BoM è immutabile
// (DEC-4), il pattern è "chiudi+inserisci nuova versione".
// `duplica` e `chiudi` seguono la capability della vista (`puo_chiudersi`:
// riga ancora aperta, `valido_al IS NULL`).
function buildRigaActions(row) {
  return [
    {
      key: 'gestisci-note',
      label: t('catalogo.gestisci_note'),
      icon: MANAGE_ICONS.NOTE,
      command: () => openNoteDrawer(row),
    },
    {
      key: 'duplica-versione',
      label: t('catalogo.duplica_come_nuova_versione'),
      icon: MANAGE_ICONS.CLONE,
      // Solo righe aperte si possono duplicare (BE solleva
      // E_BOM_SORGENTE_GIA_CHIUSA su righe chiuse).
      visible: !!row.puo_chiudersi,
      // Il Duplica riscrive il form «nuovo componente»: se e' aperto e
      // modificato, prima si chiede (e prima della PATCH di chiusura).
      command: () => chiudiConConferma(() => onDuplicaVersione(row)),
    },
    {
      key: 'chiudi-riga',
      label: t('catalogo.chiudi_riga'),
      icon: MANAGE_ICONS.CLOSE_DATE,
      severity: 'danger',
      visible: !!row.puo_chiudersi,
      command: () => onChiudiRiga(row),
    },
  ]
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotoChiudiRiga = useFotografiaDialog(() => ({ data: chiudiDialogData.value }), { visibile: () => chiudiDialogVisible.value })

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotoDuplica = useFotografiaDialog(() => ({ chiudiAl: duplicaDialogChiudiAl.value }), { visibile: () => duplicaDialogVisible.value })
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :proteggi-corpo="false"
    :title="t('catalogo.tab_bom')"
    :icon="MANAGE_ICONS.BOM"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.WIDE"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="formAperto ? 'nessuno' : 'chiudi'"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <!-- Hint immutabilità (defense-in-depth UX): spiega il pattern
         chiudi+inserisci che sostituisce l'edit in place. -->
    <Message
      v-if="!isReadonly && store.totalRecords > 0"
      severity="info"
      :closable="false"
      class="mt-025"
    >
      {{ t('catalogo.bom_immutabile_hint') }}
    </Message>

    <!-- ⛔ «Non sono riuscito a leggere» non e' «non ce ne sono». -->
    <Message v-if="store.erroreCaricamento" severity="warn" :closable="false" size="small">
      {{ t('common.righe_non_lette') }}
    </Message>

    <DrawerTabLista
      ref="listaRef"
      codice="catalogo.articolo_componenti"
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
      :riga-attiva="rigaInModifica?.id ?? null"
      :righe-cliccabili="!isReadonly"
      @page="onPage"
      @sort="onSort"
      @row-click="onRowClick"
      @config-loaded="onConfigLoaded"
    >
      <!-- La ricerca: colonne dal catalogo (codice e descrizione del
           componente). L'export porta la stessa `search`. -->
      <template #filtri-sempre>
        <InputText v-model="searchText" class="app-filter-w-lg"
          :placeholder="t('catalogo.filtro_componente_placeholder')" />
      </template>
      <template #filtri>
        <DatePicker
          :model-value="dataValida"
          class="app-filter-w-sm"
          :date-format="DATE_FORMAT"
          show-icon
          show-button-bar
          :disabled="tutteLeVersioni"
          :placeholder="t('catalogo.filtro_bom_validi_al')"
          @update:model-value="(v) => { dataValida = v; onDataValidaChange() }"
        />
        <FiltroToggle
          v-model="tutteLeVersioni"
          :label="t('catalogo.filtro_bom_tutto')"
          @change="applyFilters"
        />
      </template>
      <template #empty>
        <span v-if="!store.erroreCaricamento">{{ t('catalogo.nessun_componente') }}</span>
      </template>
      <template v-if="!isReadonly" #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRigaActions(data)" />
      </template>
    </DrawerTabLista>

    <!-- Form sotto la lista: nuovo componente (anche la nuova versione del
         Duplica, con titolo e banner suoi) o la riga in sola lettura. -->
    <template v-if="!isReadonly && formAperto">
      <div :ref="ancoraForm" class="app-drawer-section">
        <h4>
          {{
            isFormReadonly
              ? t('catalogo.dettaglio_componente')
              : (duplicaFlowSource ? t('catalogo.nuova_versione_componente') : t('catalogo.nuovo_componente'))
          }}
        </h4>
      </div>
      <Message
        v-if="duplicaFlowSource"
        severity="warn"
        :closable="false"
        class="mt-025"
      >
        {{ t('catalogo.nuova_versione_hint', {
          codice: duplicaFlowSource.componente_codice,
          data: displayDate(duplicaFlowSource.chiudi_al),
        }) }}
      </Message>
      <div class="form-grid" :class="{ 'app-readonly': isFormReadonly }">
        <div class="form-field">
          <label>{{ t('catalogo.field_componente') }} *</label>
          <ArticoloLookup
            :model-value="componenteObj"
            :placeholder="t('catalogo.search_componente')"
            :disabled="isFormReadonly"
            documento="ARTICOLO"
            :articolo-padre-id="articoloId"
            @select="onComponenteSelect"
          />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_coeff_qta') }} *</label>
          <InputNumber v-model="form.coeff_qta" :min="0" :min-fraction-digits="2"
            :max-fraction-digits="6" :disabled="isFormReadonly"
            :invalid="campiErrati.includes('coeff_qta')"
          />
        </div>
      </div>
      <div class="form-grid-2col mt-05" :class="{ 'app-readonly': isFormReadonly }">
        <div class="form-field">
          <label>{{ t('catalogo.field_valido_dal') }}</label>
          <DatePicker v-model="form.valido_dal" :date-format="DATE_FORMAT"
            show-icon show-button-bar :disabled="isFormReadonly"
            :invalid="campiErrati.includes('valido_dal')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_valido_al') }}</label>
          <DatePicker v-model="form.valido_al" :date-format="DATE_FORMAT"
            show-icon show-button-bar :disabled="isFormReadonly"
            :invalid="campiErrati.includes('valido_al')"
          />
        </div>
      </div>
      <!-- I tre flag della riga: in sola lettura uno switch disegnato
           (il ToggleSwitch disabilitato non si legge), altrimenti il widget. -->
      <div class="form-grid-2col mt-05" :class="{ 'app-readonly': isFormReadonly }">
        <div v-for="flag in FLAG_COMPONENTE" :key="flag.campo" class="form-field">
          <label>{{ t(flag.labelKey) }}</label>
          <span
            v-if="isFormReadonly"
            class="bom-readonly-switch"
            :class="{ 'bom-readonly-switch--on': form[flag.campo] }"
          >
            <span class="bom-readonly-switch__knob" />
            <span>{{ form[flag.campo] ? t('common.yes') : t('common.no') }}</span>
          </span>
          <ToggleSwitch v-else v-model="form[flag.campo]"
            :invalid="campiErrati.includes(flag.campo)"
          />
        </div>
        <!-- Come compare il componente in fattura: una scelta fra tre, non un
             sì/no (NASCOSTO nel totale del kit, DESCRITTIVO riga senza
             prezzo, VALORIZZATO riga con prezzo e importo suoi). -->
        <div class="form-field">
          <label>{{ t('catalogo.field_esposizione_fattura') }}</label>
          <span v-if="isFormReadonly">{{ etichettaEsposizione(form.esposizione_in_fattura) }}</span>
          <Select v-else v-model="form.esposizione_in_fattura"
            :options="esposizioniOptions" option-label="label" option-value="value"
            :invalid="campiErrati.includes('esposizione_in_fattura')"
          />
        </div>
      </div>
      <FormFooter
        v-if="isFormReadonly"
        close-only
        @cancel="chiudiForm"
      />
      <FormFooter
        v-else
        :loading="loading"
        :disabled="!canSaveForm"
        @save="onSaveNew"
        @cancel="annullaAdd"
      />
    </template>
  </AppDrawer>

  <ExportDialog
    v-model:visible="exportDialogVisible"
    :loading="exportLoading"
    @export="onExportConfirm"
  />

  <NoteDrawer
    v-if="noteApiClient"
    :visible="noteDrawerVisible"
    @update:visible="v => noteDrawerVisible = v"
    :api-client="noteApiClient"
    codice="catalogo.note"
    :title="t('catalogo.tab_note')"
    @saved="reloadAll"
  />

  <!-- Dialog chiusura riga BoM. Pattern simmetrico a ChiudiVersioneDialog
       dei listini-versioni: DatePicker default oggi, min-date = valido_dal
       della riga, conferma esplicita per evitare PATCH involontario. -->
  <AppDialog
    :conferma-uscita="fotoChiudiRiga.chiudiConConferma"
    :visible="chiudiDialogVisible"
    @update:visible="v => { if (!v) annullaChiusura() }"
    :header="t('catalogo.chiudi_riga_dialog_titolo')"
    width="sm"
    :loading="loading"
    :save-disabled="!chiudiDialogData || loading"
    :save-label="t('catalogo.chiudi_riga_conferma')"
    save-severity="warn"
    @save="confermaChiusura"
  >
    <Message
      v-if="chiudiDialogIsImmediata"
      severity="warn"
      :closable="false"
    >
      {{ t('catalogo.chiudi_riga_warn_immediata') }}
    </Message>
    <Message
      v-else-if="chiudiDialogData"
      severity="info"
      :closable="false"
    >
      {{ t('catalogo.chiudi_riga_info_programmata', {
        data: displayDate(chiudiDialogData)
      }) }}
    </Message>

    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('catalogo.chiudi_riga_data') }}</label>
        <DatePicker v-model="chiudiDialogData" :date-format="DATE_FORMAT"
          show-icon show-button-bar :min-date="chiudiDialogMinDate" />
      </div>
    </div>
  </AppDialog>

  <!-- Dialog "Duplica versione": step 1 del flow (chiusura sorgente).
       Sceglie chiudi_al e su conferma fa PATCH valido_al sulla sorgente.
       Subito dopo il drawer apre il form add pre-compilato con
       valido_dal = chiudi_al + 1 (step 2 in confermaDuplicaVersione).
       min-date = valido_dal sorgente (dal BE come data_min_chiusura). -->
  <AppDialog
    :conferma-uscita="fotoDuplica.chiudiConConferma"
    :visible="duplicaDialogVisible"
    @update:visible="v => { if (!v) annullaDuplicaVersione() }"
    :header="t('catalogo.duplica_versione_dialog_titolo')"
    width="sm"
    :loading="loading"
    :save-disabled="!duplicaDialogChiudiAl || loading"
    :save-label="t('catalogo.duplica_versione_conferma')"
    @save="confermaDuplicaVersione"
  >
    <Message severity="info" :closable="false">
      {{ t('catalogo.duplica_versione_info') }}
    </Message>
    <Message
      v-if="duplicaDialogIsImmediata"
      severity="warn"
      :closable="false"
    >
      {{ t('catalogo.duplica_versione_warn_immediata') }}
    </Message>
    <Message
      v-else-if="duplicaDialogChiudiAl"
      severity="info"
      :closable="false"
    >
      {{ t('catalogo.duplica_versione_info_programmata', {
        data: displayDate(duplicaDialogChiudiAl)
      }) }}
    </Message>

    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('catalogo.duplica_versione_chiudi_al') }}</label>
        <DatePicker v-model="duplicaDialogChiudiAl" :date-format="DATE_FORMAT"
          show-icon show-button-bar :min-date="duplicaDialogMinDate" />
      </div>
    </div>
  </AppDialog>
</template>

<style scoped>
.bom-readonly-switch {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--app-text-muted);
  font-size: 0.9rem;
}

.bom-readonly-switch::before {
  content: '';
  display: inline-block;
  width: 2.5rem;
  height: 1.25rem;
  border-radius: 999px;
  border: 1px solid var(--p-surface-400);
  background: var(--p-surface-200);
}

.bom-readonly-switch__knob {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 0.875rem;
  height: 0.875rem;
  margin-left: 0.1875rem;
  border-radius: 999px;
  background: var(--p-surface-0);
  box-shadow: 0 1px 2px rgb(0 0 0 / 18%);
}

.bom-readonly-switch--on {
  color: var(--app-accent-color);
  font-weight: 600;
}

.bom-readonly-switch--on::before {
  border-color: var(--app-accent-color);
  background: var(--app-accent-color);
}

.bom-readonly-switch--on .bom-readonly-switch__knob {
  margin-left: 1.4375rem;
}
</style>

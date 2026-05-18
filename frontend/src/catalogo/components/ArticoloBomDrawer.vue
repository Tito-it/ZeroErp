<script setup>
// Scopo: Sub-drawer per gestione distinta base (BoM) articolo.
// Layout: toolbar (filtro+reload) + lista paginata 10 righe + form inserimento.
// Pattern immutabilità (sviluppo-listini-v5 §14.4 / DEC-4):
//   - i campi struttura (componente, coeff_qta, esposto_in_fattura, ecc.)
//     non sono modificabili in place: trigger DB E_BOM_MODIFICA_VIETATA li
//     blocca. Per cambiare valori si usa "chiudi riga" + nuovo "Aggiungi
//     componente" con i nuovi parametri (operazioni esplicite, intenzionali).
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
// Standard sub-drawer: paginazione 10 righe, PageActionsBar + F5, filtro
// client-side articolo, sort default articolo_descrizione.

import { ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { paramBool, paramNumber } from '../../core/utils/parameterCast'
import {
  listArticoloComponenti, createArticoloComponente,
  updateArticoloComponente,
  listComponenteNote, createComponenteNota,
} from '../api/catalogo'
import { DRAWER_WIDTH, DATE_FORMAT, MANAGE_ICONS } from '../../core/constants'
import { displayDate, toDateString } from '../../core/utils/date'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import CatalogoNoteDrawer from '../../core/components/CatalogoNoteDrawer.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import Drawer from 'primevue/drawer'
import Dialog from 'primevue/dialog'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Message from 'primevue/message'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import Checkbox from 'primevue/checkbox'

const { t } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const componentiList = ref([])
const listLoading = ref(false)

// Defaults BoM via config.parameters (override per emittente).
// Pre-fetch al setup; la watch su `props.visible` await-a comunque per
// evitare race "drawer aperto con fallback hardcoded mentre la fetch e' in volo".
// Fallback hardcoded coincide col comportamento pre-refactor: se i parametri
// non sono ancora seedati nel DB, nessuna regressione.
const { defaults: paramDefaults, load: loadDefaults } = useParameterDefaults([
  'CATALOGO_BOM_DEFAULT_COEFF_QTA',
  'CATALOGO_BOM_DEFAULT_PARTECIPA_QTA',
  'CATALOGO_BOM_DEFAULT_OBBLIGATORIO',
  'CATALOGO_BOM_DEFAULT_DETERMINA_QTA_PADRE',
  'CATALOGO_BOM_DEFAULT_ESPOSTO_IN_FATTURA',
])
loadDefaults()

// Filtro client-side articolo (codice + descrizione, case-insensitive).
// Coerente con il pattern ContrattoRigheDrawer: la lista BoM è tipicamente
// sotto le 50-100 righe per articolo, niente bisogno di filtro server-side.
const filtroArticolo = ref('')
const filtroValiditaTutto = ref(false)
const filtroValiditaData = ref(new Date())

const componentiView = computed(() => {
  const filtro = (filtroArticolo.value || '').trim().toLowerCase()
  const dataFiltro = filtroValiditaData.value ? toDateString(filtroValiditaData.value) : null

  return componentiList.value.filter(r => {
    if (!filtroValiditaTutto.value && dataFiltro) {
      const validoAl = r.valido_al || null
      if (validoAl && validoAl < dataFiltro) return false
    }
    if (!filtro) return true
    const codice = (r.componente_codice || '').toLowerCase()
    const desc = (r.componente_descrizione || '').toLowerCase()
    return codice.includes(filtro) || desc.includes(filtro)
  })
})

// Form inserimento nuovo componente
const form = ref({})
const componenteObj = ref(null)
const adding = ref(false)
const viewing = ref(false)
const isFormOpen = computed(() => adding.value || viewing.value)
const isFormReadonly = computed(() => viewing.value)
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: loadComponenti,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('catalogo.aggiungi_componente'),
    icon: MANAGE_ICONS.ADD,
    disabled: isFormOpen.value,
    command: startAdd,
  },
])

// Dialog chiusura riga (pattern simmetrico a ChiudiVersioneDialog).
// L'admin sceglie data di chiusura (oggi = immediata, futura = programmata).
// Min-date e default-date arrivano DAL BE come capability di riga
// (`data_min_chiusura`, `data_default_chiusura` su vw_articoli_componenti_dettaglio,
// Fase 2 refactor catalogo). Niente ricalcolo lato FE: single source of truth DB.
const chiudiDialogVisible = ref(false)
const chiudiDialogRow = ref(null)
const chiudiDialogData = ref(null)
const chiudiDialogMinDate = computed(() => parseDate(chiudiDialogRow.value?.data_min_chiusura))
const chiudiDialogIsImmediata = computed(() => {
  if (!chiudiDialogData.value) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const sel = new Date(chiudiDialogData.value)
  sel.setHours(0, 0, 0, 0)
  return sel.getTime() === today.getTime()
})

// Dialog "Duplica versione": l'admin sceglie chiudi_al, alla conferma il
// BE chiude SOLO la sorgente (PATCH valido_al, stessa path di "Chiudi
// riga", trigger BoM lo permette). Subito dopo il drawer apre il form
// "Aggiungi componente" pre-compilato dai valori della sorgente, con
// `valido_dal = chiudi_al + 1`. L'utente puo' modificare i campi prima
// di salvare, e il save fa l'INSERT della nuova versione.
// Vantaggio: niente DB function dedicata, tutto su endpoint esistenti
// (PATCH valido_al + POST create), e l'utente puo' personalizzare i
// valori della nuova versione senza scontrarsi col trigger
// E_BOM_MODIFICA_VIETATA (l'INSERT porta gia' i valori finali).
// Min-date dialog: BE espone `data_min_chiusura` su vw_articoli_componenti_dettaglio
// (= valido_dal della sorgente).
const duplicaDialogVisible = ref(false)
const duplicaDialogRow = ref(null)
const duplicaDialogChiudiAl = ref(null)
// Stato del flow duplica post-chiusura: se != null, il form add e' stato
// aperto pre-compilato dalla sorgente (titolo + banner dedicato).
const duplicaFlowSource = ref(null)
const duplicaDialogMinDate = computed(() => parseDate(duplicaDialogRow.value?.data_min_chiusura))
const duplicaDialogIsImmediata = computed(() => {
  if (!duplicaDialogChiudiAl.value) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const sel = new Date(duplicaDialogChiudiAl.value)
  sel.setHours(0, 0, 0, 0)
  return sel.getTime() === today.getTime()
})

// Sub-drawer note per componente
const noteDrawerVisible = ref(false)
const noteCompId = ref(null)

const noteListFn = computed(() => () => listComponenteNote(props.articoloId, noteCompId.value))
const noteCreateFn = computed(() => (payload) => createComponenteNota(props.articoloId, noteCompId.value, payload))

function openNoteDrawer(row) {
  noteCompId.value = row.id
  noteDrawerVisible.value = true
}

function defaultForm() {
  const p = paramDefaults.value
  return {
    componente_id: null,
    coeff_qta: paramNumber(p.CATALOGO_BOM_DEFAULT_COEFF_QTA, 1),
    partecipa_qta: paramBool(p.CATALOGO_BOM_DEFAULT_PARTECIPA_QTA, true),
    obbligatorio: paramBool(p.CATALOGO_BOM_DEFAULT_OBBLIGATORIO, true),
    determina_qta_padre: paramBool(p.CATALOGO_BOM_DEFAULT_DETERMINA_QTA_PADRE, false),
    esposto_in_fattura: paramBool(p.CATALOGO_BOM_DEFAULT_ESPOSTO_IN_FATTURA, false),
    // valido_dal: null (Fase 4 BE-only). Se l'admin non sceglie una data,
    // il service applica today come default. Il DatePicker resta vuoto
    // finche' l'utente non interagisce: piu' onesto rispetto al pre-fill che
    // mascherava la responsabilita' del default.
    valido_dal: null,
    valido_al: null,
  }
}

// Scopo: reset stato del form add. Comune a cancel, save-success
// e apertura drawer: evita duplicazione delle reassegnazioni.
// Resetta anche lo stato del flow duplica: se l'utente annulla il form
// pre-compilato, il banner/title torna allo stato "Aggiungi componente".
function resetFormState() {
  adding.value = false
  viewing.value = false
  form.value = defaultForm()
  componenteObj.value = null
  duplicaFlowSource.value = null
}

// Scopo: Converte stringa ISO date in Date object per DatePicker.
function parseDate(val) {
  if (!val) return null
  if (val instanceof Date) return val
  const d = new Date(val)
  return isNaN(d.getTime()) ? null : d
}

// Scopo: Carica lista componenti dell'articolo.
async function loadComponenti() {
  if (!props.articoloId) return
  listLoading.value = true
  try {
    const res = await listArticoloComponenti(props.articoloId)
    const payload = res.data?.data
    componentiList.value = payload?.results || payload || []
  } catch {
    componentiList.value = []
  } finally {
    listLoading.value = false
  }
}

watch(() => props.visible, async (val) => {
  if (!val) return
  // Attendi i parameters prima di resettare il form (race-fix simmetrico
  // a ArticoloUomDrawer): evita form costruito con fallback hardcoded
  // mentre la fetch dei defaults e' ancora in volo.
  await loadDefaults()
  resetFormState()
  filtroArticolo.value = ''
  filtroValiditaTutto.value = false
  filtroValiditaData.value = new Date()
  loadComponenti()
})

// Shortcut F5: ricarica la lista senza reload del browser. Coerente con il
// pattern useSearchTable e con gli altri sub-drawer (ContrattoRigheDrawer).
// Attivo solo quando il drawer è visibile (il drawer è persistente: register
// in onMounted, deregister in onUnmounted, no leak su mount/unmount parent).
function onKeydown(e) {
  if (e.key === 'F5' && props.visible) {
    e.preventDefault()
    loadComponenti()
  }
}
onMounted(() => { window.addEventListener('keydown', onKeydown) })
onUnmounted(() => { window.removeEventListener('keydown', onKeydown) })

// Scopo: Callback quando l'utente seleziona un articolo dal lookup.
function onComponenteSelect(item) {
  componenteObj.value = item
  form.value.componente_id = item?.id || null
}

function startAdd() {
  resetFormState()
  adding.value = true
}

function cancelAdd() {
  resetFormState()
}

// Scopo: apre la riga BoM nello stesso form, ma in sola lettura.
// Le righe sono immutabili: il click riga serve solo a consultare i campi
// non presenti nella lista compatta.
function openReadonlyDetail(row) {
  adding.value = false
  viewing.value = true
  duplicaFlowSource.value = null
  form.value = {
    componente_id: row.componente_id,
    coeff_qta: row.coeff_qta,
    partecipa_qta: row.partecipa_qta,
    obbligatorio: row.obbligatorio,
    determina_qta_padre: row.determina_qta_padre,
    esposto_in_fattura: row.esposto_in_fattura,
    valido_dal: parseDate(row.valido_dal),
    valido_al: parseDate(row.valido_al),
  }
  componenteObj.value = {
    id: row.componente_id,
    codice: row.componente_codice,
    descrizione: row.componente_descrizione,
  }
}

function closeReadonlyDetail() {
  resetFormState()
}

// Scopo: chiusura drawer dal pulsante Chiudi del footer (modalita' lista).
// Nasconde il footer in modalita' adding per non duplicarlo con Annulla/Salva
// del form e non spingere il form sotto al fold.
const onClose = useDrawerClose(emit)

// Scopo: apre il dialog "Duplica versione". L'operazione di chiusura+apertura
// e' atomica lato DB (Fase 3, fn_duplica_componente_versione): il FE non
// ricompone il flusso, manda solo `chiudi_al` e ricarica.
// Default `chiudi_al = oggi` -> chiusura immediata, nuova riga apre domani.
function onDuplicaVersione(row) {
  duplicaDialogRow.value = row
  duplicaDialogChiudiAl.value = new Date()
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
  const chiudiAlDate = new Date(duplicaDialogChiudiAl.value)
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
  await loadComponenti()
  emit('saved')

  // Apre il form add pre-compilato. valido_dal default = chiudi_al + 1
  // (la nuova versione apre il giorno successivo alla chiusura, evita
  // overlap col range chiuso). Tutti i campi sono editabili.
  const nextDay = new Date(chiudiAlDate)
  nextDay.setDate(nextDay.getDate() + 1)

  duplicaFlowSource.value = {
    chiudi_al: chiudiAlIso,
    componente_codice: sourceRow.componente_codice,
  }
  adding.value = true
  form.value = {
    componente_id: sourceRow.componente_id,
    coeff_qta: sourceRow.coeff_qta,
    partecipa_qta: sourceRow.partecipa_qta,
    obbligatorio: sourceRow.obbligatorio,
    determina_qta_padre: sourceRow.determina_qta_padre,
    esposto_in_fattura: sourceRow.esposto_in_fattura,
    valido_dal: nextDay,
    valido_al: null,
  }
  componenteObj.value = {
    id: sourceRow.componente_id,
    codice: sourceRow.componente_codice,
    descrizione: sourceRow.componente_descrizione,
  }
}

const canSaveForm = computed(() => {
  return form.value.componente_id != null && form.value.coeff_qta > 0
})

// Scopo: Inserisce nuovo componente. Ricarica lista e notifica il parent.
async function onSaveNew() {
  const payload = {
    componente_id: form.value.componente_id,
    coeff_qta: form.value.coeff_qta,
    partecipa_qta: form.value.partecipa_qta,
    obbligatorio: form.value.obbligatorio,
    determina_qta_padre: form.value.determina_qta_padre,
    esposto_in_fattura: form.value.esposto_in_fattura,
    valido_dal: toDateString(form.value.valido_dal),
    valido_al: toDateString(form.value.valido_al),
  }
  const result = await execute(
    () => createArticoloComponente(props.articoloId, payload),
    { successMessage: t('catalogo.componente_aggiunto') }
  )
  if (result === null) return
  resetFormState()
  await loadComponenti()
  emit('saved')
}

// Scopo: apre il dialog di chiusura riga BoM con DatePicker. Pattern
// simmetrico a ChiudiVersioneDialog (listini-versioni): l'admin sceglie la
// data, default oggi (chiusura immediata), futura ammessa (chiusura
// programmata). Min-date e default-date arrivano dal BE come capability di
// riga (`data_min_chiusura`, `data_default_chiusura` da
// `vw_articoli_componenti_dettaglio` Fase 2): niente ricalcolo client-side.
// Il delete BoM resta bloccato dal trigger DB E_BOM_MODIFICA_VIETATA.
function onChiudiRiga(row) {
  chiudiDialogRow.value = row
  chiudiDialogData.value = parseDate(row.data_default_chiusura) || new Date()
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
    await loadComponenti()
    emit('saved')
  }
}

// Scopo: azioni di riga del componente BoM (note + duplica + chiudi).
// Nascoste in readonly. La voce "elimina" non esiste più: la BoM è
// immutabile (DEC-4), il pattern è "chiudi+inserisci nuova versione".
// `chiudi-riga` e' visibile solo se la capability del BE lo permette
// (`puo_chiudersi=true`, ovvero riga ancora aperta — `valido_al IS NULL`).
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
      // E_BOM_SORGENTE_GIA_CHIUSA su righe chiuse). Stesso check truthy
      // di chiudi-riga e dell'inline edit valido_al.
      visible: !!row.puo_chiudersi,
      command: () => onDuplicaVersione(row),
    },
    {
      key: 'chiudi-riga',
      label: t('catalogo.chiudi_riga'),
      icon: MANAGE_ICONS.CLOSE_DATE,
      severity: 'danger',
      // Truthy check: coerente con il template inline edit `data.puo_chiudersi`
      // e col pattern progetto (es. `is_base`, `attivo`). Se la migration BE
      // non e' applicata e il campo manca, l'azione sparisce — comportamento
      // corretto (riga non chiudibile per default in assenza di info).
      visible: !!row.puo_chiudersi,
      command: () => onChiudiRiga(row),
    },
  ]
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
  >
    <template #header>
      <DrawerTitle :action="t('common.edit')" :title="t('catalogo.tab_bom')" icon="pi pi-sitemap" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div v-if="listLoading" class="app-loading">
        <i class="pi pi-spin pi-spinner" />
      </div>

      <template v-if="!listLoading">
        <!-- Hint immutabilità (defense-in-depth UX): spiega il pattern
             chiudi+inserisci che sostituisce l'edit in place. -->
        <Message
          v-if="!isReadonly && componentiList.length > 0"
          severity="info"
          :closable="false"
          class="mt-025"
        >
          {{ t('catalogo.bom_immutabile_hint') }}
        </Message>

        <!-- Toolbar standard sub-drawer: filtro + reload + nuovo. Visibile
             sempre (anche con lista vuota) per esporre il pulsante "Aggiungi
             componente" come azione primaria — pattern allineato a
             ContrattoRigheDrawer. Filtro nascosto se non c'e' nulla da filtrare. -->
        <div v-if="!isReadonly" class="app-page-toolbar">
          <div class="app-page-filters">
            <InputText v-if="componentiList.length > 0"
              v-model="filtroArticolo"
              :placeholder="t('catalogo.filtro_componente_placeholder')"
              style="min-width: 240px;" />
            <DatePicker
              v-if="componentiList.length > 0"
              v-model="filtroValiditaData"
              :date-format="DATE_FORMAT"
              show-icon
              show-button-bar
              :disabled="filtroValiditaTutto"
              :placeholder="t('catalogo.filtro_bom_validi_al')"
              style="width: 160px;"
            />
            <div v-if="componentiList.length > 0" class="flex align-items-center gap-2">
              <Checkbox v-model="filtroValiditaTutto" input-id="bom-filter-all" binary />
              <label for="bom-filter-all">{{ t('catalogo.filtro_bom_tutto') }}</label>
            </div>
          </div>
          <PageActionsBar :actions="pageActions" />
        </div>

        <!-- Lista componenti (sempre visibile) -->
        <div v-if="componentiList.length === 0 && !adding" class="app-empty-state">
          <i class="pi pi-sitemap" />
          <p>{{ t('catalogo.nessun_componente') }}</p>
        </div>

        <DataTable
          v-if="componentiList.length > 0"
          :value="componentiView"
          class="app-datatable"
          striped-rows
          paginator
          :rows="10"
          :rows-per-page-options="[10, 25, 50]"
          paginator-position="top"
          sort-field="componente_descrizione"
          :sort-order="1"
          removable-sort
          data-key="id"
          @row-click="event => openReadonlyDetail(event.data)"
        >
          <Column field="componente_codice" :header="t('catalogo.col_codice')" sortable style="width: 110px;">
            <template #body="{ data }">
              <span class="bom-codice-truncate" :title="data.componente_codice">{{ data.componente_codice }}</span>
            </template>
          </Column>
          <Column field="componente_descrizione" :header="t('catalogo.col_descrizione')" sortable style="width: 220px;" />
          <Column field="coeff_qta" :header="t('catalogo.col_coeff_qta')" style="width: 70px;" sortable />
          <Column field="esposto_in_fattura" :header="t('catalogo.col_esposto_fattura')" style="width: 80px;">
            <template #body="{ data }">
              <i :class="data.esposto_in_fattura ? 'pi pi-check text-green-500' : 'pi pi-minus text-color-secondary'" />
            </template>
          </Column>
          <Column field="valido_al" :header="t('catalogo.field_valido_al')" style="width: 130px;" sortable>
            <template #body="{ data }">
              {{ displayDate(data.valido_al) || '—' }}
            </template>
          </Column>
          <Column v-if="!isReadonly" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
            <template #body="{ data }">
              <span @click.stop>
                <RowActionsMenu :row="data" :actions="buildRigaActions(data)" />
              </span>
            </template>
          </Column>
        </DataTable>

        <!-- Form inserimento nuovo componente. Pulsante di apertura ora
             nella toolbar in alto (PageActionsBar); qui solo il form quando
             adding=true. Quando `duplicaFlowSource` e' valorizzato il form
             arriva pre-compilato dai valori della sorgente chiusa: titolo +
             banner cambiano per chiarire all'utente che sta inserendo la
             nuova versione successiva alla riga appena chiusa. -->
        <template v-if="!isReadonly">
          <template v-if="isFormOpen">
            <div class="app-drawer-section">
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
                  :filtri="{ compositi: 'escludi' }"
                  @select="onComponenteSelect"
                />
              </div>
              <div class="form-field">
                <label>{{ t('catalogo.field_coeff_qta') }} *</label>
                <InputNumber v-model="form.coeff_qta" :min="0" :min-fraction-digits="2"
                  :max-fraction-digits="6" class="w-full" :disabled="isFormReadonly" />
              </div>
            </div>
            <div class="form-grid-2col mt-05" :class="{ 'app-readonly': isFormReadonly }">
              <div class="form-field">
                <label>{{ t('catalogo.field_valido_dal') }}</label>
                <DatePicker v-model="form.valido_dal" :date-format="DATE_FORMAT"
                  show-icon show-button-bar class="w-full" :disabled="isFormReadonly" />
              </div>
              <div class="form-field">
                <label>{{ t('catalogo.field_valido_al') }}</label>
                <DatePicker v-model="form.valido_al" :date-format="DATE_FORMAT"
                  show-icon show-button-bar class="w-full" :disabled="isFormReadonly" />
              </div>
            </div>
            <div class="form-grid-2col mt-05" :class="{ 'app-readonly': isFormReadonly }">
              <div class="form-field">
                <label>{{ t('catalogo.field_obbligatorio') }}</label>
                <span
                  v-if="isFormReadonly"
                  class="bom-readonly-switch"
                  :class="{ 'bom-readonly-switch--on': form.obbligatorio }"
                >
                  <span class="bom-readonly-switch__knob" />
                  <span class="bom-readonly-switch__label">{{ form.obbligatorio ? t('common.yes') : t('common.no') }}</span>
                </span>
                <ToggleSwitch v-else v-model="form.obbligatorio" />
              </div>
              <div class="form-field">
                <label>{{ t('catalogo.field_partecipa_qta') }}</label>
                <span
                  v-if="isFormReadonly"
                  class="bom-readonly-switch"
                  :class="{ 'bom-readonly-switch--on': form.partecipa_qta }"
                >
                  <span class="bom-readonly-switch__knob" />
                  <span class="bom-readonly-switch__label">{{ form.partecipa_qta ? t('common.yes') : t('common.no') }}</span>
                </span>
                <ToggleSwitch v-else v-model="form.partecipa_qta" />
              </div>
            </div>
            <div class="form-grid-2col mt-05" :class="{ 'app-readonly': isFormReadonly }">
              <div class="form-field">
                <label>{{ t('catalogo.field_determina_qta_padre') }}</label>
                <span
                  v-if="isFormReadonly"
                  class="bom-readonly-switch"
                  :class="{ 'bom-readonly-switch--on': form.determina_qta_padre }"
                >
                  <span class="bom-readonly-switch__knob" />
                  <span class="bom-readonly-switch__label">{{ form.determina_qta_padre ? t('common.yes') : t('common.no') }}</span>
                </span>
                <ToggleSwitch v-else v-model="form.determina_qta_padre" />
              </div>
              <div class="form-field">
                <label>{{ t('catalogo.field_esposto_fattura') }}</label>
                <span
                  v-if="isFormReadonly"
                  class="bom-readonly-switch"
                  :class="{ 'bom-readonly-switch--on': form.esposto_in_fattura }"
                >
                  <span class="bom-readonly-switch__knob" />
                  <span class="bom-readonly-switch__label">{{ form.esposto_in_fattura ? t('common.yes') : t('common.no') }}</span>
                </span>
                <ToggleSwitch v-else v-model="form.esposto_in_fattura" />
              </div>
            </div>
            <template v-if="isFormReadonly">
              <DrawerFooter close-only @cancel="closeReadonlyDetail" />
            </template>
            <div v-else class="flex justify-end gap-2 mt-05">
                <Button :label="t('common.cancel')" text @click="cancelAdd" />
                <Button :label="t('common.save')" :loading="loading" :disabled="!canSaveForm" @click="onSaveNew" />
            </div>
          </template>
        </template>
      </template>

      <DrawerFooter v-if="!isFormOpen" close-only @cancel="onClose" />
    </div>
  </Drawer>

  <CatalogoNoteDrawer
    :visible="noteDrawerVisible"
    @update:visible="v => noteDrawerVisible = v"
    :list-fn="noteListFn"
    :create-fn="noteCreateFn"
    :title="t('catalogo.tab_note')"
    @saved="loadComponenti"
  />

  <!-- Dialog chiusura riga BoM. Pattern simmetrico a ChiudiVersioneDialog
       dei listini-versioni: DatePicker default oggi, min-date = valido_dal
       della riga, conferma esplicita per evitare PATCH involontario. -->
  <Dialog
    :visible="chiudiDialogVisible"
    @update:visible="v => { if (!v) annullaChiusura() }"
    modal
    :header="t('catalogo.chiudi_riga_dialog_titolo')"
    :style="{ width: '480px' }"
  >
    <Message
      v-if="chiudiDialogIsImmediata"
      severity="warn"
      :closable="false"
      class="mb-1"
    >
      {{ t('catalogo.chiudi_riga_warn_immediata') }}
    </Message>
    <Message
      v-else-if="chiudiDialogData"
      severity="info"
      :closable="false"
      class="mb-1"
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

    <div class="flex justify-end gap-2 mt-1">
      <Button :label="t('common.cancel')" text @click="annullaChiusura" />
      <Button :label="t('catalogo.chiudi_riga_conferma')"
        :icon="MANAGE_ICONS.CLOSE_DATE" severity="warn"
        :disabled="!chiudiDialogData || loading" :loading="loading"
        @click="confermaChiusura" />
    </div>
  </Dialog>

  <!-- Dialog "Duplica versione": step 1 del flow (chiusura sorgente).
       Sceglie chiudi_al e su conferma fa PATCH valido_al sulla sorgente.
       Subito dopo il drawer apre il form add pre-compilato con
       valido_dal = chiudi_al + 1 (step 2 in confermaDuplicaVersione).
       min-date = valido_dal sorgente (dal BE come data_min_chiusura). -->
  <Dialog
    :visible="duplicaDialogVisible"
    @update:visible="v => { if (!v) annullaDuplicaVersione() }"
    modal
    :header="t('catalogo.duplica_versione_dialog_titolo')"
    :style="{ width: '480px' }"
  >
    <Message severity="info" :closable="false" class="mb-1">
      {{ t('catalogo.duplica_versione_info') }}
    </Message>
    <Message
      v-if="duplicaDialogIsImmediata"
      severity="warn"
      :closable="false"
      class="mb-1"
    >
      {{ t('catalogo.duplica_versione_warn_immediata') }}
    </Message>
    <Message
      v-else-if="duplicaDialogChiudiAl"
      severity="info"
      :closable="false"
      class="mb-1"
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

    <div class="flex justify-end gap-2 mt-1">
      <Button :label="t('common.cancel')" text @click="annullaDuplicaVersione" />
      <Button :label="t('catalogo.duplica_versione_conferma')"
        :icon="MANAGE_ICONS.CLONE"
        :disabled="!duplicaDialogChiudiAl || loading" :loading="loading"
        @click="confermaDuplicaVersione" />
    </div>
  </Dialog>
</template>

<style scoped>
/* Solo il codice componente (identificatore) tronca con ellipsis. La
   descrizione wrappa per parole in modo naturale: su drawer stretto
   la cella cresce in altezza invece di sovrapporsi. */
.bom-codice-truncate {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

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
  color: var(--p-primary-color);
  font-weight: 600;
}

.bom-readonly-switch--on::before {
  border-color: var(--p-primary-color);
  background: var(--p-primary-color);
}

.bom-readonly-switch--on .bom-readonly-switch__knob {
  margin-left: 1.4375rem;
}
</style>

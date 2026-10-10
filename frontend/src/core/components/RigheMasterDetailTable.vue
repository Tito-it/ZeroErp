<script setup>
// Scopo: shell master-detail inline delle RIGHE di un documento (B10
//        2026-06-05, regola del 2): la lista sopra, il form di riga sotto,
//        nello stesso drawer (frontend-standards §Master-detail inline).
//        Possiede cio' che e' identico fra i documenti di vendita: la lista
//        configurabile (`useDrawerTabLista` + `<DrawerTabLista>`), la ricerca,
//        l'export, «Nuova riga», l'eliminazione, il salvataggio e i
//        componenti BoM. Le celle speciali e il form di riga sono slot.
//
// ⭐ DAL 2026-09-28 LE RIGHE SONO UNA LISTA STANDARD (brief-db-liste-righe-
//    documento, lotto B; decisione di Tid). Fino a quel giorno qui c'era una
//    `DataTable` grezza con le colonne scritte dal chiamante: su tablet e
//    smartphone 9-10 colonne a larghezza piena uscivano in uno scroll
//    orizzontale che col touch non si usa. Ora le colonne vengono dal
//    catalogo (`ui.lista_colonna`, liste 97-100): quelle che non entrano si
//    ritirano nella riga espandibile, per priorita', e l'operatore puo'
//    personalizzarle ed esportarle.
//
// ⭐ La macchina del form e' il BB `useFormInline` (sede unica).
//
// ⭐ IL PADRE E' COMPOSTO: il documento (path) e il suo emittente (query,
//    `emittente_fiscale_id`). L'emittente scioglie il cancello di perimetro
//    per chi vede piu' emittenti; finche' non arriva — col dettaglio — la
//    lista e' in attesa, non vuota (`useListaStoreCore`, «il padre composto»).
//
// Azioni di riga: «elimina» e' del BB; il chiamante ne aggiunge di proprie con
// `extraRowActions(riga) => actions[]`, che vivono anche a documento non
// modificabile (l'annullo di un accredito su un reso confermato).
//
// Slot:
//   #form="{ riga, onSaved, onComponentiChanged, onCancel, registra }" → il form di riga
//     (`registra` va su `:ref` del form: D-13, la sua fotografia)
//   #cell-<codice>="{ data, value }"  → una cella che il catalogo non sa
//                                       rendere da sola; ⚠️ il nome e' il
//                                       `codice` della colonna, non il campo
//   ogni altro slot (`empty`, …)      → inoltrato alla lista, per nome
//
// Uso:
//   const righe = useOrdineRigheStore()
//   <RigheMasterDetailTable
//     codice="vendite.ordine_righe" :store="righe"
//     :parent-id="ordineId" :emittente-fiscale-id="emittenteId"
//     :export-fn="exportRigheLista"
//     :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
//     :is-modificabile="isModificabile" title-key="..." new-tooltip-key="..."
//     confirm-delete-key="..." deleted-message-key="..."
//     new-label-key="..." edit-label-key="..."
//     @changed="..." @form-aperto="...">
//     <template #cell-prezzo_unitario="{ data }"> ... </template>
//     <template #form="{ riga, onSaved, onComponentiChanged, onCancel, registra }">
//       <RigaForm :ref="registra" :riga="riga" @saved="onSaved" @componenti-changed="onComponentiChanged" @cancel="onCancel" />
//     </template>
//   </RigheMasterDetailTable>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import { useApiHandler } from '../composables/useApiHandler'
import { useConfirmAction } from '../composables/useConfirmAction'
import { useDrawerTabLista } from '../composables/useDrawerTabLista'
import { useFormInline } from '../composables/useFormInline'
import { unisciFotografie } from '../composables/useDrawerFormPreserve'
import { MANAGE_ICONS } from '../constants'
import DrawerTabLista from './DrawerTabLista.vue'
import ExportDialog from './ExportDialog.vue'
import RowActionsMenu from './RowActionsMenu.vue'

const { t } = useI18n()
const { execute } = useApiHandler()
const { confirmAction } = useConfirmAction()

// Gli slot che il BB tiene per se': gli altri si inoltrano alla lista.
// ⚠️ Anche quelli che il BB riempie sulla lista (`actions`, `filtri-sempre`):
//    inoltrati, due template sullo stesso slot si scavalcherebbero in silenzio.
const SLOT_PROPRI = ['form', 'actions', 'filtri-sempre']

const props = defineProps({
  // La lista a catalogo (`vendite.ordine_righe`).
  codice: { type: String, required: true },
  // Lo store-lista delle righe, uno per istanza (`createRigheListaStore`).
  store: { type: Object, required: true },
  parentId: { type: Number, default: null },
  // L'emittente del documento (PK): lasciapassare del cancello di perimetro.
  emittenteFiscaleId: { type: Number, default: null },
  // (documentoId, params) => Promise<blob>: l'export della lista.
  exportFn: { type: Function, required: true },
  // (parentId, rigaId) => Promise — store.eliminaRiga.
  deleteAction: { type: Function, required: true },
  isModificabile: { type: Boolean, default: true },
  titleKey: { type: String, required: true },
  newTooltipKey: { type: String, required: true },
  confirmDeleteKey: { type: String, required: true },
  deletedMessageKey: { type: String, required: true },
  newLabelKey: { type: String, required: true },
  editLabelKey: { type: String, required: true },
  // (riga) => bool: disabilita elimina su righe specifiche (es. approvazione PENDING).
  deleteDisabled: { type: Function, default: () => false },
  // (riga) => actions[]: azioni di DOMINIO sulla riga, oltre a «elimina».
  // ⚠️ Vivono anche quando la riga NON e' piu' modificabile — e' il caso che
  // le ha rese necessarie: l'annullo dell'accredito su un reso CONFERMATO,
  // dove le righe non si toccano piu' ma un atto registrato su di esse si puo'
  // ancora disfare. Per questo la colonna azioni non dipende dal solo
  // `isModificabile`.
  extraRowActions: { type: Function, default: () => [] },
})

// Eventi:
//  - `changed`: dopo create/update/delete riga (parent ricarica detail/totali).
//  - `form-aperto`: il drawer parent nasconde il proprio FormFooter testata
//    durante l'edit-riga.
const emit = defineEmits(['changed', 'form-aperto'])

// ⭐ LA FOTOGRAFIA DEL FORM DI RIGA (2026-10-03, D-13 di
//    work-done/analisi-fe-chrome-drawer.md, ok Tid). Il form lo monta il
//    contenitore nello slot `#form`, e qui si registra con `:ref="registra"`
//    (dallo scope dello slot): cosi' questo BB sa che cosa c'e' aperto. Serve a
//    due cose — chiedere prima di cambiare riga (D-8, `confermaCambio`) e dire
//    al drawer, via `defineExpose`, se la riga ha modifiche da non perdere
//    all'uscita. Un form che non espone la sua fotografia vale «non modificato».
const formRiga = ref(null)
function registraFormRiga(el) {
  formRiga.value = el
}
const fotografiaRiga = unisciFotografie(() => formRiga.value)

const {
  formMode, rigaInModifica, formAperto,
  apriRiga, chiudiForm, ancoraForm, risincronizza, azioneNuovaRiga,
} = useFormInline({
  padre: () => props.parentId,
  puoModificare: () => props.isModificabile,
  confermaCambio: (procedi) => fotografiaRiga.chiudiConConferma(procedi),
})
watch(formAperto, (aperto) => emit('form-aperto', aperto))
// ⚠️ Smontata a form aperto (drawer chiuso: AppDrawer smonta il corpo) il watch
//    non scatta piu', e il drawer resterebbe con `formRigaAperto` vero: alla
//    riapertura `useFooterDocumento` darebbe 'nessuno', testata senza Salva.
onBeforeUnmount(() => {
  if (formAperto.value) emit('form-aperto', false)
})

const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm, reloadAll,
} = useDrawerTabLista(props.store, {
  parentId: {
    documentoId: () => props.parentId,
    emittenteId: () => props.emittenteFiscaleId,
  },
  // L'export segue la lista a video — ricerca e ordinamento compresi — e
  // porta l'emittente del documento, che il cancello di perimetro chiede anche
  // all'export (`paramsExport`: filtri + emittente, sede unica dello store).
  exportFn: (params) => props.exportFn(props.parentId, params),
  getExportParams: (formato) => ({ formato, ...props.store.paramsExport() }),
  // «Nuova riga» fra le azioni della lista: sparisce a form aperto (BB).
  // ⚠️ Arrow lazy: la legge il computed delle azioni, non il setup.
  extraActions: () => [
    azioneNuovaRiga({
      key: 'new',
      label: t('common.new'),
      tooltip: t(props.newTooltipKey),
      visible: () => props.isModificabile,
    }),
  ],
})

// Scopo: rilegge la pagina corrente e aspetta che arrivi (per chi deve
//        leggere le righe fresche subito dopo).
async function rileggi() {
  await props.store.fetchList()
}

async function onRigaSaved() {
  chiudiForm()
  await rileggi()
  emit('changed')
}

// Mutation su un componente BoM CASO A (PATCH prezzo o DELETE): ricarica le
// righe per riflettere il nuovo prezzo padre (SUM componenti via trigger DB),
// MA NON chiude il form. Risincronizza la riga in modifica sull'oggetto fresco
// così il watcher del form ri-popola il prezzo corrente.
async function onComponentiChanged() {
  await rileggi()
  risincronizza(props.store.items)
  emit('changed')
}

function onDeleteRiga(riga) {
  confirmAction({
    header: t('confirm.delete_title'),
    message: t(props.confirmDeleteKey),
    onAccept: async () => {
      const result = await execute(
        () => props.deleteAction(props.parentId, riga.id),
        { successMessage: t(props.deletedMessageKey) },
      )
      if (rigaInModifica.value?.id === riga.id) chiudiForm()
      await rileggi()
      if (result !== null) emit('changed')
    },
  })
}

function buildRowActions(riga) {
  return [
    // Le azioni di dominio PRIMA della distruttiva: «elimina» resta l'ultima
    // voce del menu, dove l'operatore si aspetta di trovarla.
    ...props.extraRowActions(riga),
    {
      key: 'elimina',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: props.isModificabile,
      disabled: props.deleteDisabled(riga),
      command: () => onDeleteRiga(riga),
    },
  ]
}

// La colonna azioni compare se c'e' qualcosa da fare: righe modificabili
// (elimina) OPPURE almeno una riga a video con un'azione di dominio. ⚠️ Senza
// il secondo ramo un'azione dichiarata su un documento non piu' modificabile
// non si vedrebbe MAI, e il chiamante non avrebbe modo di accorgersene.
const haColonnaAzioni = computed(
  () => props.isModificabile
    || (props.store.items || []).some((r) => props.extraRowActions(r).length > 0),
)

// ⛔ Una funzione e non una `computed`, come in `DrawerTabLista`: l'oggetto
//    degli slot non e' reattivo, e una `computed` lo congelerebbe al primo
//    render.
function slotInoltrati(slots) {
  return Object.keys(slots).filter((n) => !SLOT_PROPRI.includes(n))
}

// I drawer padre chiamano `loadRighe` sul ref dopo un gesto sul documento:
// ricarica la lista (e cio' che `useDrawerTabLista` ricarica con lei).
defineExpose({
  loadRighe: () => reloadAll(),
  // D-13: le modifiche della riga aperta, per l'uscita dal drawer.
  modificato: fotografiaRiga.modificato,
  chiudiConConferma: fotografiaRiga.chiudiConConferma,
})
</script>

<template>
  <div>
    <!-- Senza la linea del titolo: nei quattro drawer la sezione righe segue il
         `<Divider>` che chiude la testata, e le due linee si leggevano come
         una doppia riga (rilievo di Tid, 2026-09-28). -->
    <div class="app-drawer-section app-drawer-section--senza-bordo">
      <h4>{{ t(titleKey) }}</h4>
    </div>

    <!-- ⛔ «Non sono riuscito a leggere le righe» non e' «non ce ne sono»: a
         lista vuota la tabella mostrerebbe lo stesso stato vuoto per entrambi. -->
    <Message v-if="store.erroreCaricamento" severity="warn" :closable="false" size="small">
      {{ t('common.righe_non_lette') }}
    </Message>

    <DrawerTabLista
      ref="listaRef"
      :codice="codice"
      :store="store"
      :emittente-esplicito="emittenteFiscaleId"
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
      :righe-cliccabili="isModificabile"
      @page="onPage"
      @sort="onSort"
      @row-click="apriRiga"
      @config-loaded="onConfigLoaded"
    >
      <!-- La ricerca: le colonne le decide il catalogo (`ricerca_full`: codice
           articolo e descrizione), sotto la soglia della lista il termine non
           filtra. L'export porta la stessa `search`. -->
      <template #filtri-sempre>
        <InputText v-model="searchText" class="app-filter-w-lg" :placeholder="t('common.search')" />
      </template>

      <template v-for="nome in slotInoltrati($slots)" #[nome]="scope" :key="nome">
        <slot :name="nome" v-bind="scope ?? {}" />
      </template>

      <!-- ⭐ `app-escape` sulle azioni. Le azioni di DOMINIO (`extraRowActions`)
           esistono proprio per i documenti NON piu' modificabili — un
           accredito da disfare vive su un reso CONFERMATO — e quel drawer e' in
           `.app-readonly` (`pointer-events: none`). Senza questa classe
           l'azione si vede e non si preme.
           ⚠️ Qui NON si riapre nulla di distruttivo: «elimina» ha gia'
           `visible: props.isModificabile`, quindi su un documento in protect e'
           filtrata via da `RowActionsMenu` prima di arrivare a video. -->
      <template v-if="haColonnaAzioni" #actions="{ data }">
        <span class="app-escape">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </span>
      </template>
    </DrawerTabLista>

    <!-- Form master-detail inline: visibile SOLO quando attivo. Il form di riga
         espone già Salva/Annulla interni (no FormFooter: è una sezione). -->
    <div v-if="formAperto" :ref="ancoraForm" class="app-drawer-section" style="margin-top: 1rem;">
      <h4>{{ formMode === 'edit' ? t(editLabelKey) : t(newLabelKey) }}</h4>
      <slot
        name="form"
        :riga="rigaInModifica"
        :on-saved="onRigaSaved"
        :on-componenti-changed="onComponentiChanged"
        :on-cancel="chiudiForm"
        :registra="registraFormRiga"
      />
    </div>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />
  </div>
</template>

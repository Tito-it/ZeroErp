<script setup>
// Scopo: La sezione delle versioni di un template documentale (Tranche L):
//        la lista, i comandi di riga, e il drawer AUTONOMO della versione
//        (`TemplateVersioneDrawer`) per crearla, modificarla o consultarla.
//
// ⭐ DAL 2026-09-27 LA LISTA E' `documenti.template_versioni` (88), montata con
//    lo scaffolding dei tab-lista (`useDrawerTabLista` + `<DrawerTabLista>`):
//    pagine, ordinamento, ricerca sul titolo, «Personalizza colonne». Era una
//    `DataTable` grezza senza paginazione.
// ✅ DAL 2026-10-03 LA VERSIONE HA IL SUO DRAWER (chiuso il debito di
//    brief-db-liste-datatable-grezze §4 riga 6). Era un form inline sotto la
//    lista: col footer del padre spento, e l'HTML del template lungo centinaia
//    di righe, il Salva finiva fuori vista. Nel drawer suo il footer e' fisso.
//
//        Comandi versione (RowActionsMenu):
//         - Pubblica  (solo BOZZA, dialog DatePicker valido_dal/al)
//         - Clona     (qualunque stato, crea nuova BOZZA)
//         - Elimina   (solo BOZZA, confirm dialog)
//
//        Clic su una riga: il drawer della versione — in modifica se BOZZA,
//        in consultazione altrimenti.
//
// ⭐ LA FORMA DEI DATI (2026-09-30, brief-db-documenti-versione-contesto-
//    template): la forma che il sistema produce oggi la dice il backend nel
//    dettaglio del template (`versione_contesto_builder`): il drawer la MOSTRA
//    e la precompila, e il dialog di pubblicazione la mette accanto a quella
//    della versione — chi rifiuta pubblicazione e stampa e' il database.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateVersioniStore } from '../stores/templateVersioni'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { PADRE_SENZA_EMITTENTE } from '../../core/composables/useListaStoreCore'
// `useConfirmAction` espone `confirmAction` (signature object con
// `onAccept` callback). Memoria feedback_useconfirmaction_destructuring:
// usare destructured + nome callback `onAccept` (non `accept`) per
// evitare dialog silente.
import { MANAGE_ICONS, DATE_FORMAT } from '../../core/constants'
import { parseIsoDate, toDateString, oggiAziendale } from '../../core/utils/date'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import InputText from 'primevue/inputtext'
import DatePicker from 'primevue/datepicker'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'
import AppDialog from '../../core/components/AppDialog.vue'
import Message from 'primevue/message'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import TemplateVersioneDrawer from './TemplateVersioneDrawer.vue'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

const props = defineProps({
  templateId: { type: Number, required: true },
  // L'emittente del template (PK `emittenti_fiscali`): la lista lo gira al
  // cancello di perimetro, perche' il super admin su «Tutti» non debba
  // scegliere l'emittente del template che ha gia' aperto.
  emittenteFiscaleId: { type: [Number, null], default: null },
  // Il template e' uno STANDARD (senza emittente): `true`/`false` dal
  // dettaglio, `null` finche' non e' letto. Vedi il padre, sotto.
  standard: { type: [Boolean, null], default: null },
  // La forma dei dati che il builder del template produce oggi
  // (`versione_contesto_builder` del dettaglio). `null` = builder non
  // registrato, o dettaglio non ancora letto.
  versioneContestoBuilder: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})
// ⭐ `pubblicata`: pubblicare la prima versione cambia la RISOLUZIONE (la
//    copia dell'emittente prende il posto dello standard): chi mostra lo
//    scarto e il pannello della risoluzione deve rileggersi.
const emit = defineEmits(['pubblicata'])

const { t } = useI18n()
const store = useTemplateVersioniStore()
const { execute, loading, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()

// Il drawer della versione: `versioneAperta` null = nuova versione. Sopra il
// drawer del template, che sotto un figlio aperto non esce (`AppDrawer`, pila
// `useDrawerInCima`): niente da segnalargli.
const drawerVersione = ref(false)
const versioneAperta = ref(null)

// Pubblica dialog state.
const pubblicaDialog = ref(false)
const pubblicaTargetId = ref(null)
const pubblicaForm = ref({ valido_dal: null, valido_al: null })
// La forma letta dalla versione che si sta pubblicando, per mostrarla accanto
// a quella del sistema nel dialog.
const pubblicaFormaVersione = ref(null)

// Il padre e' il template: al cambio, lo scaffolding scrive l'id nello store,
// azzera pagina e ricerca e ricarica. Il «Nuovo» sta nella barra della lista,
// spento in sola lettura.
const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato, reloadAll,
} = useDrawerTabLista(store, {
  // Il padre composto: il template e il suo emittente (vedi lo store).
  // ⭐ Lo STANDARD non ha emittente (brief-db-modelli-documento-standard §11
  //    B-6/F-4): la parte dell'emittente e' `PADRE_SENZA_EMITTENTE`, la lista
  //    legge senza il parametro, e il cancello decide come per una lista senza
  //    emittente suo. ⛔ Fino al 2026-10-21 aspettava un emittente che non
  //    arriva: drawer dello standard senza versioni, in caricamento per sempre.
  parentId: {
    templateId: () => props.templateId,
    emittenteId: () => (props.standard === true ? PADRE_SENZA_EMITTENTE : props.emittenteFiscaleId),
  },
  searchTableOptions: { defaultSortField: 'versione', defaultSortOrder: 'desc' },
  extraActions: () => [{
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('config.modelli_documenti.versioni.new'),
    icon: MANAGE_ICONS.ADD,
    visible: !props.readonly,
    command: openCreate,
  }],
})

// Al cambio template il drawer aperto sulla versione del precedente si chiude.
watch(() => props.templateId, () => { drawerVersione.value = false })

async function reload() {
  await reloadAll()
}

function statoSeverity(stato) {
  if (stato === 'PUBBLICATA') return 'success'
  if (stato === 'OBSOLETA') return 'secondary'
  return 'info'  // BOZZA
}

function buildRowActions(row) {
  if (props.readonly) return []
  const actions = []
  if (row.stato === 'BOZZA') {
    actions.push({
      key: 'pubblica',
      label: t('config.modelli_documenti.versioni.action_pubblica'),
      icon: MANAGE_ICONS.PUBLISH,
      severity: 'primary',
      command: () => openPubblicaDialog(row),
    })
  }
  actions.push({
    key: 'clona',
    label: t('config.modelli_documenti.versioni.action_clona'),
    icon: MANAGE_ICONS.CLONE,
    severity: 'info',
    command: () => clonaVersione(row),
  })
  if (row.stato === 'BOZZA') {
    actions.push({
      key: 'delete',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      command: () => confirmDeleteVersione(row),
    })
  }
  return actions
}

function openCreate() {
  versioneAperta.value = null
  drawerVersione.value = true
}

// Scopo: apre la versione: in modifica se BOZZA, in consultazione altrimenti
//        (lo decide il drawer dallo stato letto). Prima una versione
//        pubblicata non si apriva affatto.
function openEdit(row) {
  versioneAperta.value = row.id
  drawerVersione.value = true
}

async function clonaVersione(row) {
  const result = await execute(
    () => store.clona(props.templateId, row.id, {}),
    { successMessage: t('config.modelli_documenti.versioni.cloned') },
  )
  if (result !== null) {
    await reload()
  }
}

function confirmDeleteVersione(row) {
  confirmAction({
    header: t('common.delete'),
    message: t('config.modelli_documenti.versioni.confirm_delete', {
      versione: row.versione,
    }),
    danger: true,
    onAccept: async () => {
      await execute(
        () => store.destroy(props.templateId, row.id),
        { successMessage: t('config.modelli_documenti.versioni.deleted') },
      )
      await reload()
    },
  })
}

function openPubblicaDialog(row) {
  pubblicaTargetId.value = row.id
  pubblicaFormaVersione.value = row.versione_contesto ?? null
  pubblicaForm.value = {
    valido_dal: parseIsoDate(row.valido_dal) || oggiAziendale(),
    valido_al: parseIsoDate(row.valido_al),
  }
  pubblicaDialog.value = true
}

async function confirmPubblica() {
  if (!pubblicaForm.value.valido_dal) return
  const payload = {
    valido_dal: toDateString(pubblicaForm.value.valido_dal),
    valido_al: toDateString(pubblicaForm.value.valido_al),
  }
  const result = await execute(
    () => store.pubblica(props.templateId, pubblicaTargetId.value, payload),
    { successMessage: t('config.modelli_documenti.versioni.published') },
  )
  if (result !== null) {
    pubblicaDialog.value = false
    await reload()
    emit('pubblicata')
  }
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotoPubblica = useFotografiaDialog(() => ({ ...pubblicaForm.value }), { visibile: () => pubblicaDialog.value })
</script>

<template>
  <div class="template-versioni-section">
    <div class="section-header">
      <h3>{{ t('config.modelli_documenti.versioni.title') }}</h3>
    </div>

    <DrawerTabLista
      ref="listaRef"
      codice="documenti.template_versioni"
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
      @row-click="openEdit"
      @config-loaded="onConfigLoaded"
    >
      <template #filtri-sempre>
        <InputText
          v-model="searchText"
          class="app-filter-w-lg"
          :placeholder="t('config.modelli_documenti.versioni.search_placeholder')"
        />
      </template>
      <template #cell-stato="{ data }">
        <Tag :value="data.stato" :severity="statoSeverity(data.stato)" />
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
      <template v-if="!props.readonly" #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </DrawerTabLista>

    <TemplateVersioneDrawer
      v-model:visible="drawerVersione"
      :template-id="props.templateId"
      :versione-id="versioneAperta"
      :emittente-fiscale-id="props.emittenteFiscaleId"
      :versione-contesto-builder="props.versioneContestoBuilder"
      :readonly="props.readonly"
      @saved="reload"
    />

    <AppDialog
      :conferma-uscita="fotoPubblica.chiudiConConferma"
      v-model:visible="pubblicaDialog"
      :header="t('config.modelli_documenti.versioni.publish_title')"
      width="sm"
      :loading="loading"
      :save-disabled="!pubblicaForm.valido_dal"
      :save-label="t('config.modelli_documenti.versioni.action_pubblica')"
      @save="confirmPubblica"
    >
      <div class="form-grid">
        <Message severity="warn" :closable="false">
          {{ t('config.modelli_documenti.versioni.publish_hint') }}
        </Message>
        <Message v-if="pubblicaFormaVersione && props.versioneContestoBuilder"
          severity="info" :closable="false">
          {{ t('config.modelli_documenti.versioni.publish_forma', {
            versione: pubblicaFormaVersione,
            builder: props.versioneContestoBuilder,
          }) }}
        </Message>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_valido_dal') }} *</label>
          <DatePicker v-model="pubblicaForm.valido_dal" :date-format="DATE_FORMAT"
            :invalid="campiErrati.includes('valido_dal')" />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_valido_al') }}</label>
          <DatePicker v-model="pubblicaForm.valido_al" :date-format="DATE_FORMAT" show-icon
            :invalid="campiErrati.includes('valido_al')" />
        </div>
      </div>
    </AppDialog>
  </div>
</template>

<style scoped>
.template-versioni-section .section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
</style>

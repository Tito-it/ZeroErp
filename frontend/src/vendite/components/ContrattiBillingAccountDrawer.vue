<script setup>
// Scopo: Sub-drawer lista contratti di un cliente specifico (billing_account_id).
//        Accessibile dalla lista Clienti. Permette nuovo contratto con BA
//        pre-compilato, apertura dettaglio in edit, e gestione righe diretta.
//
// ⭐ PORTATO SULLO STANDARD IL 2026-09-26 (piano PrimeVue 5, Gruppo A: era
//    fermo per «decisione 4», ma l'endpoint dei contratti e' gia' paginato e
//    filtra gia' per cliente). E' la lista `vendite.contratti` filtrata sul
//    conto di fatturazione: `useDrawerTabLista` + `<DrawerTabLista>`, col suo
//    store (`contrattiCliente`). Prima era una `DataTable` grezza su `limit: 50`
//    con il filtro di stato fatto sul client: oltre il 50° contratto le righe
//    sparivano senza avviso, e il filtro guardava solo quelle 50.
// ⚠️ Stesso `codice` della schermata Contratti: stesse colonne e stesse
//    preferenze dell'operatore. Le celle speciali (stato, lineage) sono il BB
//    `ContrattoCella`, condiviso con `ContrattiSearchTable`.
import { ref, computed } from 'vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useI18n } from 'vue-i18n'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
import { gestoreVisibile } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
import { useContrattiStore } from '../stores/contratti'
import { useContrattiClienteStore } from '../stores/contrattiCliente'
import { exportContratti } from '../api/contratti'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import ExportDialog from '../../core/components/ExportDialog.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ContrattoCella, { CELLE_CONTRATTO } from './ContrattoCella.vue'
import ContrattoDrawer from './ContrattoDrawer.vue'
import ContrattoRigheDrawer from './ContrattoRigheDrawer.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

const { t } = useI18n()
// Lo store della schermata Contratti serve solo al dettaglio (righe): la
// LISTA del drawer ha il suo store.
const storeContratti = useContrattiStore()
const store = useContrattiClienteStore()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  billingAccountId: { type: Number, default: null },
  billingAccountLabel: { type: String, default: '' },
  billingAccountUtility: { type: String, default: '' },
  canCreate: { type: Boolean, default: true },
  disabledCreateReason: { type: String, default: '' },
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const emit = defineEmits(['update:visible'])

// ⚠️ `parentId` porta l'id SOLO a drawer aperto: il `null` alla chiusura
//    chiama `store.reset()`, o i contratti del cliente precedente
//    lampeggerebbero sotto il prossimo.
// ⚠️ Il «Nuovo» entra da `extraActions` e non da `onNew`: ha una CONDIZIONE
//    (conto cessato o chiuso → spento col motivo), che `onNew` non sa dire.
const {
  onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
  exportDialogVisible, exportLoading, onExportConfirm, reloadAll,
} = useDrawerTabLista(store, {
  parentId: () => (props.visible ? props.billingAccountId : null),
  parentField: 'billingAccountId',
  exportFn: (params) => exportContratti({ ...params, billing_account_id: props.billingAccountId }),
  getExportParams: (formato) => ({ formato, ...store.paramsFiltro() }),
  // Nessun `searchTableOptions`: l'ordinamento di partenza (`valido_dal`
  // DESC) lo dichiara lo store, e una seconda copia qui divergerebbe in
  // silenzio — quella di prima diceva `valido_dal` senza verso, cioe' ASC.
  extraActions: () => [{
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: props.canCreate ? t('vendite.contratti.nuovo_contratto') : props.disabledCreateReason,
    icon: MANAGE_ICONS.ADD,
    disabled: !props.canCreate,
    hideWhenReadonly: true,
    command: onNew,
  }],
})

// Filtro di stato: va al SERVER (`stato_doc_contratto_id`), come nella lista
// Contratti — non piu' sulle sole righe della pagina.
const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: statoFilter, onChange: onStatoChange } = bindSelect('stato_doc_contratto_id')

const nestedDrawer = useDrawerState()

// Drawer righe
const righeDrawer = ref({
  visible: false,
  contrattoId: null,
  modalita: 'B',
  righe: [],
  numero: '',
  cliente: '',
  validoDal: '',
  validoAl: null,
  statoCodice: '',
  statoDescrizione: '',
})

// ⚠️ Il BB emette la RIGA, non l'evento PrimeVue (guard liste-configurabili).
function onRowClick(riga) {
  nestedDrawer.editRow(riga, 'id')
}

function onNew() {
  if (!props.canCreate) return
  nestedDrawer.openCreate()
}

function onNestedSaved() {
  nestedDrawer.close()
  reloadAll()
}

// Scopo: azioni di riga nel drawer contratti del BA (solo "gestisci righe").
function buildRowActions(data) {
  return [
    {
      key: 'gestisci-righe',
      label: t('vendite.contratti.gestisci_righe'),
      icon: MANAGE_ICONS.RIGHE,
      command: () => onOpenRighe(data),
    },
  ]
}

// Gestione righe — carica dettaglio per avere righe + contesto
async function onOpenRighe(data) {
  const detail = await storeContratti.fetchDetail(data.id)
  if (!detail) return
  const modalita = !detail.listino_id ? 'C' : detail.tipo_variazione_globale ? 'A' : 'B'
  righeDrawer.value = {
    visible: true,
    contrattoId: detail.id,
    modalita,
    righe: detail.righe || [],
    numero: detail.numero,
    cliente: props.billingAccountLabel,
    validoDal: detail.valido_dal,
    validoAl: detail.valido_al,
    statoCodice: detail.stato_codice_interno,
    statoDescrizione: detail.stato_descrizione,
  }
}

async function onRigheChanged() {
  if (!righeDrawer.value.contrattoId) return
  const detail = await storeContratti.fetchDetail(righeDrawer.value.contrattoId)
  if (detail) righeDrawer.value.righe = detail.righe || []
}

const billingAccountPrefill = computed(() => (
  props.billingAccountId
    ? { id: props.billingAccountId, ragione_sociale: props.billingAccountLabel }
    : null
))

const onClose = useDrawerClose(emit)
const suVisibile = gestoreVisibile(emit, onClose)
</script>

<template>
  <Drawer
    :visible="props.visible"
    @update:visible="suVisibile"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :dismissable="true"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :title="t('vendite.contratti.contratti_cliente')"
        :icon="NAV_ICONS.CONTRATTI"
      />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- Badge ragione sociale + utility -->
      <div>
        <span class="font-bold">{{ billingAccountLabel }}</span>
        <Tag v-if="billingAccountUtility" :value="billingAccountUtility" severity="info" class="ml-05" />
      </div>

      <Message v-if="!canCreate && disabledCreateReason" severity="warn" :closable="false" size="small">
        {{ disabledCreateReason }}
      </Message>

      <DrawerTabLista
        ref="listaRef"
        codice="vendite.contratti"
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
        @row-click="onRowClick"
        @config-loaded="onConfigLoaded"
      >
        <template #filtri>
          <LookupSelect
            v-model="statoFilter"
            class="app-filter-w-md"
            rel="config.stati_doc_contratti"
            :placeholder="t('vendite.contratti.filtro_stato')"
            show-clear
            @change="onStatoChange"
          />
        </template>
        <!-- La frase del dominio al posto dell'empty-state generico, e solo se
             la lettura e' riuscita: con `erroreCaricamento` la lista e' vuota
             per un'altra ragione. -->
        <template #empty>
          <span v-if="!store.erroreCaricamento">{{ t('vendite.contratti.nessun_contratto_ba') }}</span>
        </template>
        <template v-for="c in CELLE_CONTRATTO" :key="c" #[`cell-${c}`]="{ data }">
          <ContrattoCella :colonna="c" :data="data" />
        </template>
        <template #actions="{ data, compact }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" :force-compact="compact" />
        </template>
      </DrawerTabLista>

      <FormFooter close-only @cancel="onClose" />
    </div>

    <ExportDialog
      v-model:visible="exportDialogVisible"
      :loading="exportLoading"
      @export="onExportConfirm"
    />

    <!-- Drawer contratto annidato -->
    <ContrattoDrawer
      :visible="nestedDrawer.state.visible"
      @update:visible="v => nestedDrawer.state.visible = v"
      :mode="nestedDrawer.state.mode"
      :contratto-id="nestedDrawer.state.itemId"
      :initial-billing-account="billingAccountPrefill"
      @saved="onNestedSaved"
      @cancelled="nestedDrawer.close"
    />

    <!-- Drawer righe contratto -->
    <ContrattoRigheDrawer
      v-if="righeDrawer.contrattoId"
      :visible="righeDrawer.visible"
      @update:visible="v => righeDrawer.visible = v"
      :contratto-id="righeDrawer.contrattoId"
      :contratto-modalita="righeDrawer.modalita"
      :righe-iniziali="righeDrawer.righe"
      :contratto-numero="righeDrawer.numero"
      :contratto-cliente="righeDrawer.cliente"
      :contratto-valido-dal="righeDrawer.validoDal"
      :contratto-valido-al="righeDrawer.validoAl"
      :contratto-stato-codice="righeDrawer.statoCodice"
      :contratto-stato-descrizione="righeDrawer.statoDescrizione"
      @changed="onRigheChanged"
    />
  </Drawer>
</template>

<script setup>
// Scopo: Sub-drawer lista contratti di un cliente specifico (billing_account_id).
//        Accessibile dalla lista Clienti. Permette nuovo contratto con BA
//        pre-compilato, apertura dettaglio in edit, e gestione righe diretta.
import { ref, computed, watch } from 'vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useI18n } from 'vue-i18n'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { useContrattiStore } from '../stores/contratti'
import { listContratti } from '../api/contratti'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate } from '../../core/utils/date'
import { statoContrattoSeverity } from '../../core/utils/severity'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ContrattoDrawer from './ContrattoDrawer.vue'
import ContrattoRigheDrawer from './ContrattoRigheDrawer.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useContrattiStore()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  billingAccountId: { type: Number, default: null },
  billingAccountLabel: { type: String, default: '' },
  billingAccountUtility: { type: String, default: '' },
  canCreate: { type: Boolean, default: true },
  disabledCreateReason: { type: String, default: '' },
})
const emit = defineEmits(['update:visible'])

const items = ref([])
const loading = ref(false)
const statoFilter = ref(null)

const filteredItems = computed(() => {
  if (!statoFilter.value) return items.value
  return items.value.filter(i => i.stato_doc_contratto_id === statoFilter.value)
})
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: fetchList,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: props.canCreate ? t('vendite.contratti.nuovo_contratto') : props.disabledCreateReason,
    icon: MANAGE_ICONS.ADD,
    disabled: !props.canCreate,
    hideWhenReadonly: true,
    command: onNew,
  },
])

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

const fv = useFetchVersion()

async function fetchList() {
  if (!props.billingAccountId) return
  const v = fv.tag()
  loading.value = true
  try {
    const res = await listContratti({
      billing_account_id: props.billingAccountId,
      limit: 50,
      order_by: 'valido_dal',
      order_dir: 'desc',
    })
    if (!fv.isCurrent(v)) return
    items.value = res.data?.data?.results || []
  } catch {
    if (fv.isCurrent(v)) items.value = []
  } finally {
    if (fv.isCurrent(v)) loading.value = false
  }
}

watch(() => props.visible, (val) => {
  if (!val) { fv.invalidate(); items.value = []; statoFilter.value = null; return }
  fetchList()
})

function onRowClick(event) {
  nestedDrawer.editRow(event.data, 'id')
}

function onNew() {
  if (!props.canCreate) return
  nestedDrawer.openCreate()
}

async function onNestedSaved() {
  nestedDrawer.close()
  await fetchList()
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
  const detail = await store.fetchDetail(data.id)
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
  const detail = await store.fetchDetail(righeDrawer.value.contrattoId)
  if (detail) righeDrawer.value.righe = detail.righe || []
}

const billingAccountPrefill = computed(() => (
  props.billingAccountId
    ? { id: props.billingAccountId, ragione_sociale: props.billingAccountLabel }
    : null
))

const onClose = useDrawerClose(emit)
</script>

<template>
  <Drawer
    :visible="props.visible"
    @update:visible="val => emit('update:visible', val)"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle
        :title="t('vendite.contratti.contratti_cliente')"
        :icon="NAV_ICONS.CONTRATTI"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- Badge ragione sociale + utility -->
      <div class="mb-2">
        <span class="font-bold">{{ billingAccountLabel }}</span>
        <Tag v-if="billingAccountUtility" :value="billingAccountUtility" severity="info" class="ml-2" />
      </div>

      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <LookupSelect
            v-model="statoFilter"
            rel="config.stati_doc_contratti"
            :placeholder="t('vendite.contratti.filtro_stato')"
            show-clear
          />
        </div>
        <PageActionsBar :actions="pageActions" />
      </div>

      <Message v-if="!canCreate && disabledCreateReason" severity="warn" :closable="false" size="small">
        {{ disabledCreateReason }}
      </Message>

      <DataTable
        :value="filteredItems"
        :loading="loading"
        striped-rows
        class="app-datatable"
        data-key="id"
        paginator
        :rows="10"
        :rows-per-page-options="[10, 25]"
        paginator-position="top"
        sort-field="valido_dal"
        :sort-order="-1"
        @row-click="onRowClick"
        selection-mode="single"
      >
        <template #empty>
          <div class="app-empty-state">
            <i class="pi pi-file" style="font-size: 2rem;"></i>
            <div>{{ t('vendite.contratti.nessun_contratto_ba') }}</div>
          </div>
        </template>
        <Column field="numero" :header="t('vendite.contratti.col_numero')" sortable style="width: 130px;" />
        <Column field="ambito" :header="t('vendite.contratti.col_ambito')" sortable style="width: 110px;" />
        <Column field="categoria_cliente_snapshot_codice" :header="t('vendite.contratti.col_categoria_cliente')" sortable style="width: 100px;">
          <template #body="{ data }">{{ data.categoria_cliente_snapshot_codice || '—' }}</template>
        </Column>
        <Column field="listino_codice" :header="t('vendite.contratti.col_listino')" sortable style="width: 150px;">
          <template #body="{ data }">{{ data.listino_codice || '—' }}</template>
        </Column>
        <Column field="valido_dal" :header="t('vendite.contratti.col_valido_dal')" sortable style="width: 100px;">
          <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
        </Column>
        <Column field="valido_al" :header="t('vendite.contratti.col_valido_al')" sortable style="width: 100px;">
          <template #body="{ data }">{{ displayDate(data.valido_al) }}</template>
        </Column>
        <Column field="stato_descrizione" :header="t('vendite.contratti.col_stato')" sortable style="width: 100px;">
          <template #body="{ data }">
            <Tag :value="data.stato_descrizione" :severity="statoContrattoSeverity(data.stato_codice_interno)" />
          </template>
        </Column>
        <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
          <template #body="{ data }">
            <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
          </template>
        </Column>
      </DataTable>

      <FormFooter close-only @cancel="onClose" />
    </div>

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

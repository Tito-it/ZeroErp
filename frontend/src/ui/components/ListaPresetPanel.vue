<script setup>
// Scopo: Pannello tab "Preset" della pagina admin Personalizzazioni Liste.
//        Lista preset filtrata per `listaCorrenteId`. Click riga apre il
//        drawer in edit. Pulsante kebab per gestire la composizione (sub-drawer).
//        Pattern lista standard: PageActionsBar + DataTable + drawer.
//        Empty state "seleziona prima una lista" se nessuna selezione.
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'
import Message from 'primevue/message'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectBlocked, useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS } from '../../core/constants'
import { useUiAdminStore } from '../stores/uiAdmin'
import { useUiPresetAdminStore } from '../stores/uiPresetAdmin'
import ListaPresetDrawer from './ListaPresetDrawer.vue'
import ListaPresetColonneDrawer from './ListaPresetColonneDrawer.vue'

const { t } = useI18n()
const uiAdmin = useUiAdminStore()
const presetStore = useUiPresetAdminStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()

const isReadonly = useInjectReadonly()
const isBlocked = useInjectBlocked()

const drawerTestata = useDrawerState()
const drawerComposizione = useDrawerState()

const listaId = computed(() => uiAdmin.listaCorrenteId)
const listaSelezionata = computed(() => listaId.value != null)

watch(listaId, async (id) => {
  if (id != null) {
    await presetStore.fetchByLista(id)
  } else {
    await presetStore.fetchByLista(null)
  }
}, { immediate: true })

async function reload() {
  if (listaId.value != null) {
    await execute(() => presetStore.fetchByLista(listaId.value), { silent: true })
  }
}

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    disabled: !listaSelezionata.value,
    command: reload,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('ui.admin.preset_nuovo'),
    icon: 'pi pi-plus',
    hideWhenReadonly: true,
    disabled: !listaSelezionata.value,
    command: drawerTestata.openCreate,
  },
])

function buildRowActions(data) {
  return [
    {
      key: 'colonne',
      label: t('ui.admin.preset_gestisci_colonne'),
      icon: 'pi pi-table',
      command: () => openComposizione(data),
    },
    {
      key: 'elimina',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      visible: !isReadonly.value,
      command: () => onDelete(data),
    },
  ]
}

function openComposizione(data) {
  drawerComposizione.editRow(data, 'id')
}

function onDelete(data) {
  confirmAction({
    title: t('ui.admin.preset_delete_titolo'),
    message: t('ui.admin.preset_delete_messaggio', { codice: data.codice }),
    danger: true,
    onAccept: async () => {
      const result = await execute(
        () => presetStore.destroy(data.id),
        { successMessage: t('notifications.delete_success') },
      )
      if (result !== null) {
        await reload()
      }
    },
  })
}

async function onDrawerSaved() {
  drawerTestata.close()
  await reload()
}

async function onComposizioneSaved() {
  await reload()
}

function severityForAmbito(ambito) {
  if (ambito === 'sistema') return 'info'
  if (ambito === 'ruolo') return 'success'
  if (ambito === 'emittente_fiscale') return 'warn'
  return 'secondary'
}
</script>

<template>
  <div class="app-tab-content">
    <AccessoBloccatoPanel v-if="isBlocked" />

    <template v-else>
      <div class="app-page-toolbar">
        <div class="app-page-filters" />
        <PageActionsBar :actions="pageActions">
          <template #suffix>
            <ReadonlyBadge />
          </template>
        </PageActionsBar>
      </div>

      <Message
        v-if="!listaSelezionata"
        severity="info"
        :closable="false"
        size="small"
        class="mt-1"
      >
        {{ t('ui.admin.lista_corrente_obbligatoria') }}
      </Message>

      <DataTable
        v-else
        :value="presetStore.items"
        data-key="id"
        class="app-datatable"
        :loading="loading || presetStore.loading"
        scrollable
        scroll-height="flex"
        striped-rows
        @row-click="(e) => drawerTestata.editRow(e.data, 'id')"
      >
        <Column field="codice" :header="t('ui.admin.preset_codice')" style="width: 180px" sortable />
        <Column field="descrizione" :header="t('ui.admin.preset_descrizione')" />
        <Column field="ambito" :header="t('ui.admin.preset_ambito')" style="width: 160px">
          <template #body="{ data }">
            <Tag :value="t(`ui.admin.preset_ambito_${data.ambito}`)" :severity="severityForAmbito(data.ambito)" />
          </template>
        </Column>
        <Column :header="t('ui.admin.preset_riferimento')" style="width: 220px">
          <template #body="{ data }">
            <span v-if="data.profilo_accesso_codice">
              {{ data.profilo_accesso_codice }}
            </span>
            <span v-else-if="data.emittente_fiscale_codice">
              {{ data.emittente_fiscale_codice }}
            </span>
            <span v-else class="muted">—</span>
          </template>
        </Column>
        <Column :header="t('ui.admin.preset_colonne_count')" style="width: 100px" class="text-right">
          <template #body="{ data }">{{ data.colonne_count }}</template>
        </Column>
        <Column :header="t('ui.admin.preset_default')" style="width: 90px" class="text-center">
          <template #body="{ data }">
            <i v-if="data.is_default" class="pi pi-check" />
          </template>
        </Column>
        <Column :header="t('common.col_attivo')" style="width: 90px">
          <template #body="{ data }">
            <AttivoTag :active="data.attivo" :active-label="t('common.yes')" :inactive-label="t('common.no')" />
          </template>
        </Column>
        <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
          <template #body="{ data }">
            <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
          </template>
        </Column>
      </DataTable>
    </template>

    <ListaPresetDrawer
      :visible="drawerTestata.state.visible"
      @update:visible="(v) => (drawerTestata.state.visible = v)"
      :mode="drawerTestata.state.mode"
      :record-id="drawerTestata.state.itemId"
      :record-data="drawerTestata.state.itemData"
      :lista-id="listaId"
      :readonly="isReadonly"
      @saved="onDrawerSaved"
      @cancelled="drawerTestata.close"
    />

    <ListaPresetColonneDrawer
      :visible="drawerComposizione.state.visible"
      @update:visible="(v) => (drawerComposizione.state.visible = v)"
      :preset-id="drawerComposizione.state.itemId"
      :preset-codice="drawerComposizione.state.itemData?.codice || ''"
      :lista-id="listaId"
      :readonly="isReadonly"
      @saved="onComposizioneSaved"
    />
  </div>
</template>

<style scoped>
.muted { color: var(--app-text-muted); }
.text-right { text-align: right; }
.text-center { text-align: center; }
</style>

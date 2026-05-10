<script setup>
// Scopo: Pannello tab "Catalogo colonne" della pagina tecnica
//        Personalizzazioni Liste (Blocco F Fase 2 — DEF-5b).
//        Master-detail su `listaCorrenteId` (Select header). Lista
//        colonne (incluse disattivate). Pattern lista standard.
//
//        SUPER_ADMIN-only via BE (`AdminAPIView`).
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { MANAGE_ICONS } from '../../core/constants'
import { useUiAdminStore } from '../stores/uiAdmin'
import { useUiColonnaAdminStore } from '../stores/uiColonnaAdmin'
import ListaColonnaDrawer from './ListaColonnaDrawer.vue'

const { t } = useI18n()
const uiAdmin = useUiAdminStore()
const colonnaStore = useUiColonnaAdminStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()

const drawer = useDrawerState()

const listaId = computed(() => uiAdmin.listaCorrenteId)
const listaSelezionata = computed(() => listaId.value != null)

watch(listaId, async (id) => {
  await colonnaStore.fetchByLista(id ?? null)
}, { immediate: true })

async function reload() {
  if (listaId.value != null) {
    await execute(
      () => colonnaStore.fetchByLista(listaId.value),
      { silent: true },
    )
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
    tooltip: t('ui_admin.colonna_nuova'),
    icon: 'pi pi-plus',
    disabled: !listaSelezionata.value,
    command: drawer.openCreate,
  },
])

function buildRowActions(data) {
  return [
    {
      key: 'edit',
      label: t('common.edit'),
      icon: 'pi pi-pencil',
      allowWhenInactive: true,
      command: () => drawer.editRow(data, 'id'),
    },
    {
      key: 'elimina',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      allowWhenInactive: true,
      command: () => onDelete(data),
    },
  ]
}

function onDelete(data) {
  confirmAction({
    title: t('ui_admin.colonna_delete_titolo'),
    message: t('ui_admin.colonna_delete_messaggio', { codice: data.codice }),
    danger: true,
    onAccept: async () => {
      const result = await execute(
        () => colonnaStore.destroy(data.id),
        { successMessage: t('notifications.delete_success') },
      )
      if (result !== null) {
        await reload()
      }
    },
  })
}

async function onDrawerSaved() {
  drawer.close()
  await reload()
}

function severityForTipoColonna(tipo) {
  if (tipo === 'identificatore') return 'info'
  if (tipo === 'azione') return 'warn'
  return 'secondary'
}
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters" />
      <PageActionsBar :actions="pageActions" />
    </div>

    <Message
      v-if="!listaSelezionata"
      severity="info"
      :closable="false"
      size="small"
      class="mt-1"
    >
      {{ t('ui_admin.lista_corrente_obbligatoria') }}
    </Message>

    <DataTable
      v-else
      :value="colonnaStore.items"
      data-key="id"
      class="app-datatable"
      :loading="loading || colonnaStore.loading"
      scrollable
      scroll-height="flex"
      striped-rows
      @row-click="(e) => drawer.editRow(e.data, 'id')"
    >
      <Column field="ordine_default" :header="t('ui_admin.colonna_ordine')" style="width: 80px" sortable />
      <Column field="codice" :header="t('ui_admin.colonna_codice')" style="width: 200px" sortable />
      <Column field="etichetta" :header="t('ui_admin.colonna_etichetta')" style="width: 220px" sortable />
      <Column field="tipo_colonna" :header="t('ui_admin.colonna_tipo_colonna')" style="width: 150px">
        <template #body="{ data }">
          <Tag :value="data.tipo_colonna" :severity="severityForTipoColonna(data.tipo_colonna)" />
        </template>
      </Column>
      <Column field="tipo_dato" :header="t('ui_admin.colonna_tipo_dato')" style="width: 110px" />
      <Column field="campo_sorgente" :header="t('ui_admin.colonna_campo_sorgente')" style="width: 180px">
        <template #body="{ data }">
          <span v-if="data.campo_sorgente">{{ data.campo_sorgente }}</span>
          <span v-else class="muted">—</span>
        </template>
      </Column>
      <Column field="gruppo" :header="t('ui_admin.colonna_gruppo')" style="width: 140px">
        <template #body="{ data }">
          <span v-if="data.gruppo">{{ data.gruppo }}</span>
          <span v-else class="muted">—</span>
        </template>
      </Column>
      <Column :header="t('common.col_attivo')" style="width: 90px">
        <template #body="{ data }">
          <Tag
            :value="data.attivo ? t('common.yes') : t('common.no')"
            :severity="data.attivo ? 'success' : 'warn'"
          />
        </template>
      </Column>
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>

    <ListaColonnaDrawer
      :visible="drawer.state.visible"
      @update:visible="(v) => (drawer.state.visible = v)"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      :record-data="drawer.state.itemData"
      :lista-id="listaId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>

<style scoped>
.muted { color: var(--app-text-muted); }
</style>

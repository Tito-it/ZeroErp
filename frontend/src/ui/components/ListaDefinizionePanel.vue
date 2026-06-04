<script setup>
// Scopo: Pannello tab "Definizioni" della pagina tecnica
//        Personalizzazioni Liste (Blocco F Fase 2 — DEF-5b).
//        Lista TUTTE le definizioni (incluse disattivate). Click riga
//        apre il drawer in edit. Pattern lista standard:
//        PageActionsBar + DataTable + RowActionsMenu + drawer.
//
//        SUPER_ADMIN-only (BE: AdminAPIView). Niente readonly conditional:
//        chi accede a questa pagina e' SUPER_ADMIN, l'editing e' sempre
//        attivo. Mantengo `useInjectReadonly` per coerenza pattern, ma
//        non e' attivo sulla pagina tecnica.
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import AttivoTag from '../../core/components/AttivoTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { MANAGE_ICONS } from '../../core/constants'
import { useUiDefinizioneAdminStore } from '../stores/uiDefinizioneAdmin'
import ListaDefinizioneDrawer from './ListaDefinizioneDrawer.vue'

const emit = defineEmits(['definizione-changed'])

const { t } = useI18n()
const definizioneStore = useUiDefinizioneAdminStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()

const drawer = useDrawerState()

onMounted(async () => {
  await definizioneStore.fetchAll()
})

async function reload() {
  await execute(() => definizioneStore.fetchAll(), { silent: true })
}

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: reload,
  },
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('ui_admin.definizione_nuova'),
    icon: 'pi pi-plus',
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
    title: t('ui_admin.definizione_delete_titolo'),
    message: t('ui_admin.definizione_delete_messaggio', { codice: data.codice }),
    danger: true,
    onAccept: async () => {
      const result = await execute(
        () => definizioneStore.destroy(data.id),
        { successMessage: t('notifications.delete_success') },
      )
      if (result !== null) {
        await reload()
        emit('definizione-changed')
      }
    },
  })
}

async function onDrawerSaved() {
  drawer.close()
  await reload()
  emit('definizione-changed')
}
</script>

<template>
  <div class="app-tab-content">
    <div class="app-page-toolbar">
      <div class="app-page-filters" />
      <PageActionsBar :actions="pageActions" />
    </div>

    <DataTable
      :value="definizioneStore.items"
      data-key="id"
      class="app-datatable"
      :loading="loading || definizioneStore.loading"
      scrollable
      scroll-height="flex"
      striped-rows
      @row-click="(e) => drawer.editRow(e.data, 'id')"
    >
      <Column field="codice" :header="t('ui_admin.definizione_codice')" sortable />
      <Column field="descrizione" :header="t('ui_admin.definizione_descrizione')" sortable />
      <Column field="schema_dati" :header="t('ui_admin.definizione_schema_dati')" sortable />
      <Column field="vista_sql" :header="t('ui_admin.definizione_vista_sql')">
        <template #body="{ data }">
          <span v-if="data.vista_sql">{{ data.vista_sql }}</span>
          <span v-else class="muted">—</span>
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

    <ListaDefinizioneDrawer
      :visible="drawer.state.visible"
      @update:visible="(v) => (drawer.state.visible = v)"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      :record-data="drawer.state.itemData"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>

<style scoped>
.muted { color: var(--app-text-muted); }
</style>

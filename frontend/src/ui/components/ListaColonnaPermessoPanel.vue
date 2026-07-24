<script setup>
// Scopo: Pannello tab "Permessi colonne". Lista permessi della lista
//        corrente, click apre drawer in edit, "Nuovo" apre drawer create.
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
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
import { useUiPermessoAdminStore } from '../stores/uiPermessoAdmin'
import ListaColonnaPermessoDrawer from './ListaColonnaPermessoDrawer.vue'

const { t } = useI18n()
const uiAdmin = useUiAdminStore()
const permessoStore = useUiPermessoAdminStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()

const isReadonly = useInjectReadonly()
const isBlocked = useInjectBlocked()

const drawer = useDrawerState()

const listaId = computed(() => uiAdmin.listaCorrenteId)
const listaSelezionata = computed(() => listaId.value != null)

watch(listaId, async (id) => {
  if (id != null) {
    await permessoStore.fetchByLista(id)
  } else {
    await permessoStore.fetchByLista(null)
  }
}, { immediate: true })

async function reload() {
  if (listaId.value != null) {
    await execute(() => permessoStore.fetchByLista(listaId.value), { silent: true })
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
    tooltip: t('ui.admin.permesso_nuovo'),
    icon: 'pi pi-plus',
    hideWhenReadonly: true,
    disabled: !listaSelezionata.value,
    command: drawer.openCreate,
  },
])

function buildRowActions(data) {
  return [
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

function onDelete(data) {
  confirmAction({
    title: t('ui.admin.permesso_delete_titolo'),
    message: t('ui.admin.permesso_delete_messaggio', {
      colonna: data.colonna_etichetta,
      profilo: data.profilo_accesso_codice,
    }),
    danger: true,
    onAccept: async () => {
      const result = await execute(
        () => permessoStore.destroy(data.id),
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

function severityForLivello(livello) {
  if (livello === 'TUTTO') return 'success'
  if (livello === 'LETTURA') return 'info'
  if (livello === 'BLOCCATO') return 'danger'
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
        :value="permessoStore.items"
        data-key="id"
        class="app-datatable"
        :loading="loading || permessoStore.loading"
        scrollable
        scroll-height="flex"
        striped-rows
        @row-click="(e) => drawer.editRow(e.data, 'id')"
      >
        <Column field="colonna_etichetta" :header="t('ui.admin.permesso_colonna')" />
        <Column field="colonna_codice" :header="t('ui.admin.permesso_colonna_codice')" style="width: 220px" />
        <Column field="profilo_accesso_codice" :header="t('ui.admin.permesso_profilo')" style="width: 240px" />
        <Column :header="t('ui.admin.permesso_livello_accesso')" style="width: 140px">
          <template #body="{ data }">
            <Tag
              :value="t(`common.livello_${data.livello_accesso.toLowerCase()}`)"
              :severity="severityForLivello(data.livello_accesso)"
            />
          </template>
        </Column>
        <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
          <template #body="{ data }">
            <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
          </template>
        </Column>
      </DataTable>
    </template>

    <ListaColonnaPermessoDrawer
      :visible="drawer.state.visible"
      @update:visible="(v) => (drawer.state.visible = v)"
      :mode="drawer.state.mode"
      :record-data="drawer.state.itemData"
      :lista-id="listaId"
      :readonly="isReadonly"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>

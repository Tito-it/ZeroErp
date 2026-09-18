<script setup>
// Scopo: Pannello tab "Permessi colonne". Lista permessi della lista
//        corrente, click apre drawer in edit, "Nuovo" apre drawer create.
//
// ⭐ Lista NON paginata su `<ListaConfigurabile>` (2026-09-02): i permessi di
//    colonna di UNA lista sono pochi per modello, quindi `:paginata="false"`.
//    ⛔ `total` resta obbligatorio: e' l'asserzione che le righe siano tutte.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import AccessoBloccatoPanel from '../../core/components/AccessoBloccatoPanel.vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
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

const listaRef = ref(null)
// Nessun `exportFn`: la lista non ha endpoint di export.
const { azioniLista, dirty } = useListaAzioni(() => listaRef.value)

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
  ...azioniLista.value,
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
    header: t('ui.admin.permesso_delete_titolo'),
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
            <ListaConfigStatusTag :dirty="dirty" />
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

      <!-- ⚠️ `@row-click` emette `data` direttamente, non l'evento PrimeVue. -->
      <ListaConfigurabile
        v-else
        ref="listaRef"
        codice="ui.lista_colonna_permesso"
        :paginata="false"
        :rows="permessoStore.items"
        :total="permessoStore.totalRecords"
        :loading="loading || permessoStore.loading"
        @row-click="(data) => drawer.editRow(data, 'id')"
      >
        <template #cell-livello_accesso="{ data }">
          <Tag
            :value="t(`common.livello_${data.livello_accesso.toLowerCase()}`)"
            :severity="severityForLivello(data.livello_accesso)"
          />
        </template>
        <template #actions="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </ListaConfigurabile>
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

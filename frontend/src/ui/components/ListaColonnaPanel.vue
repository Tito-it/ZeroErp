<script setup>
// Scopo: Pannello tab "Catalogo colonne" della pagina tecnica
//        Personalizzazioni Liste (Blocco F Fase 2 — DEF-5b).
//        Master-detail su `listaCorrenteId` (Select header). Lista
//        colonne (incluse disattivate). Pattern lista standard.
//
//        SUPER_ADMIN-only via BE (`AdminAPIView`).
//
// ⭐ Lista NON paginata su `<ListaConfigurabile>` (2026-09-02): la popolazione
//    e' limitata per modello — le colonne di UNA lista — quindi
//    `:paginata="false"`. ⛔ `total` resta obbligatorio: e' l'asserzione che le
//    righe siano tutte, e il BB si rifiuta di disegnare la tabella se
//    `rows.length` non coincide.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'
import Message from 'primevue/message'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
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

const listaRef = ref(null)
// Nessun `exportFn`: la lista non ha endpoint di export e il BB rende l'azione
// condizionale — senza handler il pulsante aprirebbe un dialog inerte.
const { azioniLista, dirty } = useListaAzioni(() => listaRef.value)

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
  ...azioniLista.value,
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('ui.admin.colonna_nuova'),
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
    header: t('ui.admin.colonna_delete_titolo'),
    message: t('ui.admin.colonna_delete_messaggio', { codice: data.codice }),
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
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
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
      codice="ui.lista_colonna"
      :paginata="false"
      :rows="colonnaStore.items"
      :total="colonnaStore.totalRecords"
      :loading="loading || colonnaStore.loading"
      @row-click="(data) => drawer.editRow(data, 'id')"
    >
      <template #cell-tipo_colonna="{ data }">
        <Tag :value="data.tipo_colonna" :severity="severityForTipoColonna(data.tipo_colonna)" />
      </template>
      <template #cell-campo_sorgente="{ data }">
        <span v-if="data.campo_sorgente">{{ data.campo_sorgente }}</span>
        <span v-else class="muted">—</span>
      </template>
      <template #cell-gruppo="{ data }">
        <span v-if="data.gruppo">{{ data.gruppo }}</span>
        <span v-else class="muted">—</span>
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" :active-label="t('common.yes')" :inactive-label="t('common.no')" />
      </template>
      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </ListaConfigurabile>

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

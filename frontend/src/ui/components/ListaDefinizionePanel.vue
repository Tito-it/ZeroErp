<script setup>
// Scopo: Pannello tab "Definizioni" della pagina tecnica
//        Personalizzazioni Liste (Blocco F Fase 2 — DEF-5b).
//        Lista TUTTE le definizioni (incluse disattivate). Click riga
//        apre il drawer in edit.
//
//        SUPER_ADMIN-only (BE: AdminAPIView). Niente readonly conditional:
//        chi accede a questa pagina e' SUPER_ADMIN, l'editing e' sempre
//        attivo.
//
// ⭐ PRIMA LISTA NON PAGINATA su `<ListaConfigurabile>` (pilota, 2026-09-02).
//    La popolazione e' limitata PER MODELLO — una riga per lista configurata —
//    quindi `:paginata="false"`: niente paginator, ordinamento locale.
//    ⛔ Cio' NON vuol dire «senza total»: `total` resta obbligatorio ed e'
//    l'asserzione che le righe siano tutte. Il BB confronta `rows.length` con
//    `total` e si rifiuta di disegnare la tabella se divergono — e il `count`
//    arriva da una query SUA nel backend, non da `len(results)`, altrimenti il
//    confronto sarebbe un'eco.
//
// ⚠️ Non usa `useListaConfigurabilePage`: quello scaffolding e' costruito su
//    `useSearchTable` e pretende uno store «ricerca + sort + limit». Qui lo
//    store ha un solo `fetchAll()`. Le due azioni di utility arrivano
//    comunque dal BB condiviso `useListaAzioni`, che nasce esattamente per
//    questo caso.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import AttivoTag from '../../core/components/AttivoTag.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useListaAzioni } from '../../core/composables/useListaAzioni'
import { MANAGE_ICONS } from '../../core/constants'
import { useUiDefinizioneAdminStore } from '../stores/uiDefinizioneAdmin'
import ListaDefinizioneDrawer from './ListaDefinizioneDrawer.vue'

const emit = defineEmits(['definizione-changed'])

const { t } = useI18n()
const definizioneStore = useUiDefinizioneAdminStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()

const drawer = useDrawerState()

// Il ref va sul componente lista: `useListaAzioni` legge di rimbalzo
// `config`/`dirty`/`colonneNuove` e chiama `openModal()`.
const listaRef = ref(null)
// Nessun `exportFn`: questa lista non ha endpoint di export, e il BB rende
// l'azione condizionale — senza handler il pulsante aprirebbe un dialog inerte.
const { azioniLista, dirty } = useListaAzioni(() => listaRef.value)

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
  ...azioniLista.value,
  {
    key: 'new',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('ui.admin.definizione_nuova'),
    icon: MANAGE_ICONS.ADD,
    command: drawer.openCreate,
  },
])

function buildRowActions(data) {
  return [
    {
      key: 'edit',
      label: t('common.edit'),
      icon: MANAGE_ICONS.EDIT,
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
    header: t('ui.admin.definizione_delete_titolo'),
    message: t('ui.admin.definizione_delete_messaggio', { codice: data.codice }),
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
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <!-- ⚠️ `@row-click` emette `data` direttamente, non l'evento PrimeVue:
         la firma cambia rispetto alla `<DataTable>` di prima. -->
    <ListaConfigurabile
      ref="listaRef"
      codice="ui.lista_definizione"
      :paginata="false"
      :rows="definizioneStore.items"
      :total="definizioneStore.totalRecords"
      :loading="loading || definizioneStore.loading"
      @row-click="(data) => drawer.editRow(data, 'id')"
    >
      <template #cell-vista_sql="{ data }">
        <span v-if="data.vista_sql">{{ data.vista_sql }}</span>
        <span v-else class="muted">—</span>
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" :active-label="t('common.yes')" :inactive-label="t('common.no')" />
      </template>
      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </ListaConfigurabile>

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

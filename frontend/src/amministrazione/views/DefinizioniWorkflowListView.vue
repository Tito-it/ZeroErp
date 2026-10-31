<script setup>
// Scopo: Vista admin edizioni di workflow versionate (Amm. Software, Fase 2).
// Lista per tipo/emittente con stato + banner drift; azioni ciclo di vita:
// fork (da PUBBLICATA → BOZZA d'emittente), nuova versione (PUBBLICATA → BOZZA),
// pubblica (BOZZA → PUBBLICATA). Le fn DB restano l'unica sede di validazione.
// Co-requisito lockstep: le 3 fn devono essere SECURITY DEFINER perché la scrittura
// passi col ruolo web (brief-db-accesso-be-definizioni-workflow §P1).
import { computed, onActivated, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
// ⛔ DEBITO, non eccezione: e' una lista vera (rotta e store propri, una riga
// per edizione di workflow) e va su `<ListaConfigurabile>` appena il suo
// codice e' seminato in `ui.lista_definizione`.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import LookupSelect from '../../core/components/LookupSelect.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import AppDialog from '../../core/components/AppDialog.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useLookup } from '../../core/composables/useLookup'
import { READONLY_DOMAINS, MANAGE_ICONS, STATO_DEFINIZIONE } from '../../core/constants'
import { listEmittentiFiscali } from '../../core/apiCore'
import {
  forkDefinizione,
  nuovaVersioneDefinizione,
  pubblicaDefinizione,
} from '../api/definizioniWorkflow'
import { useDefinizioniWorkflowStore } from '../stores/definizioniWorkflow'
import FiltriLista from '../../core/components/FiltriLista.vue'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

const { t } = useI18n()
const router = useRouter()
const store = useDefinizioniWorkflowStore()
const { isReadonly } = useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
const { execute } = useApiHandler()
const { confirmAction } = useConfirmAction()

const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: () => store.load(),
  },
])

// Severity Tag per stato edizione (BOZZA editabile, PUBBLICATA attiva, RITIRATA storica).
function statoSeverity(stato) {
  if (stato === STATO_DEFINIZIONE.PUBBLICATA) return 'success'
  if (stato === STATO_DEFINIZIONE.BOZZA) return 'warn'
  return 'secondary'
}

function onFiltroTipoChange() { store.load() }

// --- Fork: dialog con scelta emittente (emittenti non nel lookup generico) ---
const emittenti = useLookup(listEmittentiFiscali, { immediate: false })
const forkVisible = ref(false)
const forkLoading = ref(false)
const forkDefId = ref(null)
const forkEmittenteId = ref(null)

function openFork(data) {
  forkDefId.value = data.id
  forkEmittenteId.value = null
  forkVisible.value = true
  if (!emittenti.items.value.length) emittenti.reload()
}

async function onForkSave() {
  forkLoading.value = true
  try {
    const res = await execute(
      () => forkDefinizione(forkDefId.value, forkEmittenteId.value),
      { successMessage: t('amministrazione.definizioni_workflow.msg_fork_ok') },
    )
    if (res !== null) { forkVisible.value = false; await store.load() }
  } finally {
    forkLoading.value = false
  }
}

// --- Nuova versione / Pubblica: conferma semplice ---
function onNuovaVersione(data) {
  confirmAction({
    header: t('amministrazione.definizioni_workflow.azione_nuova_versione'),
    message: t('amministrazione.definizioni_workflow.conferma_nuova_versione'),
    onAccept: async () => {
      const res = await execute(
        () => nuovaVersioneDefinizione(data.id),
        { successMessage: t('amministrazione.definizioni_workflow.msg_nuova_versione_ok') },
      )
      if (res !== null) await store.load()
    },
  })
}

function onPubblica(data) {
  confirmAction({
    header: t('amministrazione.definizioni_workflow.azione_pubblica'),
    message: t('amministrazione.definizioni_workflow.conferma_pubblica'),
    onAccept: async () => {
      const res = await execute(
        () => pubblicaDefinizione(data.id),
        { successMessage: t('amministrazione.definizioni_workflow.msg_pubblica_ok') },
      )
      if (res !== null) await store.load()
    },
  })
}

// Apre l'editor/ispettore dell'edizione (rotta dedicata). La sola-lettura è
// derivata nella vista dallo stato (solo BOZZA editabile) + livello area.
function openEditor(data) {
  router.push({ name: 'amm-software-definizione-editor', params: { id: data.id } })
}

// Azioni riga contestualizzate allo stato dell'edizione.
function buildRowActions(data) {
  // Ispezione/modifica sempre disponibile (naviga a un dettaglio; la scrittura
  // è comunque gated dallo stato+area nell'editor). BOZZA editabile → "Modifica
  // struttura"; edizioni emesse o area in sola lettura → "Ispeziona".
  const canEdit = data.stato === STATO_DEFINIZIONE.BOZZA && !isReadonly.value
  const actions = [
    {
      key: 'apri-editor',
      label: canEdit
        ? t('amministrazione.definizioni_workflow.azione_modifica_struttura')
        : t('amministrazione.definizioni_workflow.azione_ispeziona'),
      icon: canEdit ? MANAGE_ICONS.EDIT : MANAGE_ICONS.INSPECT,
      command: () => openEditor(data),
    },
  ]
  if (isReadonly.value) return actions
  return [
    ...actions,
    {
      key: 'fork',
      label: t('amministrazione.definizioni_workflow.azione_fork'),
      icon: MANAGE_ICONS.CLONE,
      visible: data.stato === STATO_DEFINIZIONE.PUBBLICATA,
      command: () => openFork(data),
    },
    {
      key: 'nuova-versione',
      label: t('amministrazione.definizioni_workflow.azione_nuova_versione'),
      icon: MANAGE_ICONS.ADD,
      visible: data.stato === STATO_DEFINIZIONE.PUBBLICATA,
      command: () => onNuovaVersione(data),
    },
    {
      key: 'pubblica',
      label: t('amministrazione.definizioni_workflow.azione_pubblica'),
      icon: MANAGE_ICONS.PUBLISH,
      severity: 'primary',
      visible: data.stato === STATO_DEFINIZIONE.BOZZA,
      command: () => onPubblica(data),
    },
  ]
}

// ⚠️ `onActivated` e non `onMounted`: la view vive sotto `<KeepAlive :max="10">`
//    (AppLayout), quindi al rientro `onMounted` non riscatta e a video resterebbe
//    l'elenco di prima. ⛔ Sostituisce, non si aggiunge: sotto KeepAlive al primo
//    montaggio scattano ENTRAMBI, quindi tenerli tutti e due farebbe due fetch.
onActivated(() => store.load())

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ forkEmittenteId: forkEmittenteId.value }), { visibile: () => forkVisible.value })
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <FiltriLista :store="store">
        <LookupSelect
          v-model="store.filters.tipo_prestazione_id"
          class="app-filter-w-md"
          rel="pratiche.tipi_prestazione"
          :placeholder="t('amministrazione.definizioni_workflow.filtro_tipo')"
          show-clear
          @change="onFiltroTipoChange"
        />
      </FiltriLista>
      <PageActionsBar :actions="pageActions" />
    </div>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      striped-rows
      scrollable
      scroll-height="flex"
      class="app-datatable"
      data-key="id"
    >
      <Column field="tipo_prestazione_descrizione" :header="t('amministrazione.definizioni_workflow.col_tipo')" sortable style="min-width: 220px;" />
      <Column field="emittente_display" :header="t('amministrazione.definizioni_workflow.col_emittente')" sortable style="width: 200px;">
        <template #body="{ data }">
          {{ data.emittente_fiscale_id ? data.emittente_display : t('amministrazione.definizioni_workflow.preset') }}
        </template>
      </Column>
      <Column field="versione" :header="t('amministrazione.definizioni_workflow.col_versione')" sortable style="width: 90px;" />
      <Column field="stato" :header="t('amministrazione.definizioni_workflow.col_stato')" sortable style="width: 130px;">
        <template #body="{ data }">
          <Tag :value="data.stato" :severity="statoSeverity(data.stato)" />
        </template>
      </Column>
      <Column :header="t('amministrazione.definizioni_workflow.col_drift')" style="width: 180px;">
        <template #body="{ data }">
          <Tag
            v-if="data.drift && data.drift.versioni_indietro > 0"
            severity="warn"
            :value="t('amministrazione.definizioni_workflow.drift_badge', { n: data.drift.versioni_indietro })"
          />
        </template>
      </Column>
      <Column field="descrizione" :header="t('amministrazione.definizioni_workflow.col_descrizione')" style="min-width: 220px;" />
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>

    <!-- Fork: scelta emittente per la nuova edizione BOZZA -->
    <AppDialog
      :conferma-uscita="fotografia.chiudiConConferma"
      v-model:visible="forkVisible"
      :header="t('amministrazione.definizioni_workflow.fork_dialog_title')"
      width="sm"
      :loading="forkLoading"
      :save-disabled="!forkEmittenteId"
      :save-label="t('amministrazione.definizioni_workflow.azione_fork')"
      @save="onForkSave"
      @cancel="forkVisible = false"
    >
      <div class="form-field">
        <label>{{ t('amministrazione.definizioni_workflow.fork_emittente_label') }}</label>
        <Select
          v-model="forkEmittenteId"
          :options="emittenti.items.value"
          option-label="ragione_sociale"
          option-value="id"
          :loading="emittenti.loading.value"
          :placeholder="t('amministrazione.definizioni_workflow.fork_emittente_placeholder')"
          filter
          show-clear
        />
      </div>
    </AppDialog>
  </div>
</template>

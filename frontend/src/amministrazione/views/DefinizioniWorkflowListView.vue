<script setup>
// Scopo: Vista admin edizioni di workflow versionate (Amm. Software, Fase 2).
// Lista configurabile `pratiche.definizioni_workflow` (107, dal 2026-10-31:
// prima una `DataTable` grezza sulla collezione intera) per tipo/emittente con
// stato e drift; azioni ciclo di vita nel kebab:
// fork (da PUBBLICATA → BOZZA d'emittente), nuova versione (PUBBLICATA → BOZZA),
// pubblica (BOZZA → PUBBLICATA). Le fn DB restano l'unica sede di validazione.
// Co-requisito lockstep: le 3 fn devono essere SECURITY DEFINER perché la scrittura
// passi col ruolo web (brief-db-accesso-be-definizioni-workflow §P1).
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Select from 'primevue/select'
import LookupSelect from '../../core/components/LookupSelect.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import AppDialog from '../../core/components/AppDialog.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useStoreFilterBindings } from '../../core/composables/useStoreFilterBindings'
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

// Ricarica, personalizza colonne: le azioni standard di ogni lista. Nessun
// «Nuovo»: un'edizione nasce da fork o nuova versione, nel kebab.
const {
  searchText, onPage, onSort, applyFilters, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store)

const { bindSelect } = useStoreFilterBindings(store, applyFilters)
const { value: tipoFilter, onChange: onFiltroTipoChange } = bindSelect('tipo_prestazione_id')

// Severity Tag per stato edizione (BOZZA editabile, PUBBLICATA attiva, RITIRATA storica).
function statoSeverity(stato) {
  if (stato === STATO_DEFINIZIONE.PUBBLICATA) return 'success'
  if (stato === STATO_DEFINIZIONE.BOZZA) return 'warn'
  return 'secondary'
}

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
    if (res !== null) { forkVisible.value = false; await store.fetchList() }
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
      if (res !== null) await store.fetchList()
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
      if (res !== null) await store.fetchList()
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

// ⚠️ `onMounted` e non `onActivated`: dal 2026-10-31 la lista e' su
//    `useListaConfigurabilePage`, il cui `useSearchTable` rilegge gia' la pagina
//    a ogni rientro sotto KeepAlive (salta la prima attivazione, quella del
//    montaggio). Un `onActivated` qui raddoppierebbe la fetch a ogni rientro.
onMounted(() => store.fetchList())

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ forkEmittenteId: forkEmittenteId.value }), { visibile: () => forkVisible.value })
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <FiltriLista :store="store" :inert="perimetroBloccato">
        <template #sempre>
          <InputText v-model="searchText" class="app-filter-w-lg" :placeholder="t('common.search')" />
        </template>
        <LookupSelect
          v-model="tipoFilter"
          class="app-filter-w-md"
          rel="pratiche.tipi_prestazione"
          :placeholder="t('amministrazione.definizioni_workflow.filtro_tipo')"
          show-clear
          @change="onFiltroTipoChange"
        />
      </FiltriLista>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <!-- ⚠️ Lista `multi_emittente`: la colonna emittente e' il biglietto della
         riga, e la lista si apre anche su «Tutti». -->
    <ListaConfigurabile
      ref="listaRef"
      codice="pratiche.definizioni_workflow"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @row-click="openEditor"
      @config-loaded="onConfigLoaded"
    >
      <template #cell-emittente="{ data }">
        {{ data.emittente_fiscale_id ? data.emittente_display : t('amministrazione.definizioni_workflow.preset') }}
      </template>
      <template #cell-stato="{ data }">
        <Tag :value="data.stato" :severity="statoSeverity(data.stato)" />
      </template>
      <template #cell-drift="{ data }">
        <Tag
          v-if="data.versioni_indietro > 0"
          severity="warn"
          :value="t('amministrazione.definizioni_workflow.drift_badge', { n: data.versioni_indietro })"
        />
      </template>
      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </ListaConfigurabile>

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

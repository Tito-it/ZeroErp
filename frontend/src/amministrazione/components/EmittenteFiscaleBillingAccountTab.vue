<script setup>
// Scopo: Tab autonomo riusabile per la gestione del mapping BA -> emittente fiscale.
// Lista paginata con search su ragione_sociale/codice BA/id_fiscale.
// Pattern allineato a UtilitiesTipiRuoloSearchTable (useSearchTable + store dedicato).
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliBAStore } from '../stores/emittentiFiscaliBA'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS } from '../../core/constants'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useEmittentiFiscaliBAStore()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const isReadonly = useInjectReadonly()

const props = defineProps({
  emittenteId: { type: Number, required: true }
})

const selectedBA = ref(null)
const adding = ref(false)

const { searchText, onPage, onSort, reload: reloadList, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'billing_account_codice'
})

// Reload composto: ricarica lista + summary in parallelo (entrambi necessari
// per coerenza del pulsante "default", che dipende dal summary indipendente
// dalla pagina). Allineato al pattern Promise.all gia' usato da
// addMapping/removeMapping nello store.
function reload() {
  reloadList()
  store.fetchSummary()
}

// Quando l'emittenteId cambia, aggiorna lo store e ricarica lista + summary.
// Il summary e' indipendente dalla pagina corrente (vedi A8/C3 del WIP):
// senza summary, `hasDefault` derivato da `store.items` falliva quando il
// record default era fuori dalla pagina paginata.
watch(() => props.emittenteId, (id) => {
  if (!id) {
    store.reset()
    return
  }
  store.emittenteId = id
  store.filters.offset = 0
  store.filters.search = ''
  searchText.value = ''
  // Parallelizzato: nessuna dipendenza tra list e summary, riduce latenza.
  Promise.all([store.fetchList(), store.fetchSummary()])
}, { immediate: true })

// Pulsante "default" disabilitato se il default esiste a livello di emittente
// (qualsiasi pagina). La fonte di verita' e' il summary BE, non la pagina FE.
const hasDefault = computed(() => store.hasDefaultMapping)

async function addSpecificMapping() {
  if (!selectedBA.value?.id) {
    notify.warn(t('amm_emittenti_fiscali.ba_select_required'))
    return
  }
  adding.value = true
  try {
    await store.addMapping({ billing_account_id: selectedBA.value.id })
    notify.success(t('amm_emittenti_fiscali.ba_added'))
    selectedBA.value = null
  } catch {
    // Errore gestito dall'interceptor axios globale.
  } finally {
    adding.value = false
  }
}

async function addDefaultMapping() {
  if (hasDefault.value) {
    notify.warn(t('amm_emittenti_fiscali.ba_default_exists'))
    return
  }
  try {
    await store.addMapping({})
    notify.success(t('amm_emittenti_fiscali.ba_default_added'))
  } catch {
    // Errore gestito dall'interceptor axios globale.
  }
}

function removeMapping(row) {
  confirmAction({
    title: t('common.confirm'),
    message: row.is_default
      ? t('amm_emittenti_fiscali.ba_remove_default_confirm')
      : t('amm_emittenti_fiscali.ba_remove_confirm', { codice: row.billing_account_codice || '-' }),
    danger: true,
    onAccept: async () => {
      try {
        await store.removeMapping(row.id)
        notify.success(t('amm_emittenti_fiscali.ba_removed'))
      } catch {
        // Errore gestito dall'interceptor axios globale.
      }
    }
  })
}

// Scopo: azioni di riga mapping BA (rimozione con conferma), nascoste in readonly.
function buildRowActions(data) {
  return [
    {
      key: 'rimuovi-mapping',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      command: () => removeMapping(data),
    },
  ]
}
</script>

<template>
  <div class="app-tab-content">
    <Message severity="info" :closable="false" class="mb-3">
      {{ t('amm_emittenti_fiscali.ba_help') }}
    </Message>

    <div v-if="!isReadonly" class="form-grid-2col mb-3">
      <BillingAccountLookup
        v-model="selectedBA"
        :placeholder="t('amm_emittenti_fiscali.ba_search_placeholder')"
      />
      <div class="flex gap-2">
        <Button
          :label="t('amm_emittenti_fiscali.ba_add_specific')"
          icon="pi pi-plus"
          :loading="adding"
          :disabled="!selectedBA?.id"
          @click="addSpecificMapping"
        />
        <Button
          :label="t('amm_emittenti_fiscali.ba_add_default')"
          icon="pi pi-star"
          severity="secondary"
          :disabled="hasDefault"
          @click="addDefaultMapping"
        />
      </div>
    </div>

    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <InputText
          v-model="searchText"
          :placeholder="t('amm_emittenti_fiscali.ba_filter_placeholder')"
          style="width: 300px;"
        />
      </div>
      <div class="app-page-actions">
        <Button
          icon="pi pi-refresh"
          text
          class="app-reload-btn"
          v-tooltip.bottom="t('common.reload_list')"
          @click="reload"
        />
      </div>
    </div>

    <DataTable
      :value="store.items"
      :loading="store.loading"
      v-bind="paginatorProps"
      lazy
      removable-sort
      striped-rows
      scrollable
      scrollHeight="flex"
      class="app-datatable"
      @page="onPage"
      @sort="onSort"
    >
      <Column :header="t('amm_emittenti_fiscali.ba_col_default')" style="width: 110px;">
        <template #body="{ data }">
          <Badge v-if="data.is_default" :value="t('common.default')" severity="info" />
        </template>
      </Column>
      <Column field="billing_account_codice" :header="t('amm_emittenti_fiscali.ba_col_codice')" sortable style="width: 180px;">
        <template #body="{ data }">
          {{ data.billing_account_codice || '—' }}
        </template>
      </Column>
      <Column field="billing_account_ragione_sociale" :header="t('amm_emittenti_fiscali.ba_col_ragione_sociale')" sortable>
        <template #body="{ data }">
          {{ data.billing_account_ragione_sociale || t('amm_emittenti_fiscali.ba_default_label') }}
        </template>
      </Column>
      <Column field="id_fiscale_univoco" :header="t('amm_emittenti_fiscali.ba_col_id_fiscale')" sortable style="width: 200px;">
        <template #body="{ data }">
          {{ data.id_fiscale_univoco || '—' }}
        </template>
      </Column>
      <Column v-if="!isReadonly" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false" frozen alignFrozen="right">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
      <template #empty>
        <div class="app-empty">{{ t('amm_emittenti_fiscali.ba_empty') }}</div>
      </template>
    </DataTable>
  </div>
</template>

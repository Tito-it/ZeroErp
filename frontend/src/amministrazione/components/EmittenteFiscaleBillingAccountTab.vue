<script setup>
// Scopo: Tab autonomo riusabile per la gestione del mapping BA -> emittente
// fiscale, configurabile
// (`<ListaConfigurabile codice="anagrafiche.emittente_billing_account">`):
// colonne, ordine e visibilita' dal catalogo `ui.lista_colonna`.
// Lista paginata con search su ragione_sociale/codice BA/id_fiscale.
// Nessuna azione "Nuovo": l'inserimento ha una sua form sopra la lista (lookup
// BA + i due pulsanti), quindi lo scaffolding non riceve `onNew`.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEmittentiFiscaliBAStore } from '../stores/emittentiFiscaliBA'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { MANAGE_ICONS } from '../../core/constants'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
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

const {
  searchText, onPage, onSort, reload: reloadList, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato,
} = useListaConfigurabilePage(store, {
  searchTableOptions: { defaultSortField: 'billing_account_codice' },
  // Arrow lazy: `reloadAll` e' dichiarata sotto e viene risolta al click.
  onReload: () => reloadAll(),
})

// Reload composto: ricarica lista + summary (entrambi necessari per coerenza
// del pulsante "default", che dipende dal summary indipendente dalla pagina).
// Passato come `onReload` allo scaffolding, cosi' il pulsante "Ricarica" della
// PageActionsBar ricarica davvero tutto quello che la pagina mostra.
function reloadAll() {
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
    notify.warn(t('amministrazione.emittenti_fiscali.ba_select_required'))
    return
  }
  adding.value = true
  try {
    await store.addMapping({ billing_account_id: selectedBA.value.id })
    notify.success(t('amministrazione.emittenti_fiscali.ba_added'))
    selectedBA.value = null
  } catch {
    // Errore gestito dall'interceptor axios globale.
  } finally {
    adding.value = false
  }
}

async function addDefaultMapping() {
  if (hasDefault.value) {
    notify.warn(t('amministrazione.emittenti_fiscali.ba_default_exists'))
    return
  }
  try {
    await store.addMapping({})
    notify.success(t('amministrazione.emittenti_fiscali.ba_default_added'))
  } catch {
    // Errore gestito dall'interceptor axios globale.
  }
}

function removeMapping(row) {
  confirmAction({
    title: t('common.confirm'),
    message: row.is_default
      ? t('amministrazione.emittenti_fiscali.ba_remove_default_confirm')
      : t('amministrazione.emittenti_fiscali.ba_remove_confirm', { codice: row.billing_account_codice || '-' }),
    danger: true,
    onAccept: async () => {
      try {
        await store.removeMapping(row.id)
        notify.success(t('amministrazione.emittenti_fiscali.ba_removed'))
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
      {{ t('amministrazione.emittenti_fiscali.ba_help') }}
    </Message>

    <div v-if="!isReadonly" class="form-grid-2col mb-3">
      <BillingAccountLookup
        v-model="selectedBA"
        :placeholder="t('amministrazione.emittenti_fiscali.ba_search_placeholder')"
      />
      <div class="flex gap-2">
        <Button
          :label="t('amministrazione.emittenti_fiscali.ba_add_specific')"
          icon="pi pi-plus"
          :loading="adding"
          :disabled="!selectedBA?.id"
          @click="addSpecificMapping"
        />
        <Button
          :label="t('amministrazione.emittenti_fiscali.ba_add_default')"
          icon="pi pi-star"
          severity="secondary"
          :disabled="hasDefault"
          @click="addDefaultMapping"
        />
      </div>
    </div>

    <div class="app-page-toolbar">
      <div class="app-page-filters" :inert="perimetroBloccato">
        <InputText
          v-model="searchText"
          :placeholder="t('amministrazione.emittenti_fiscali.ba_filter_placeholder')"
          style="width: 300px;"
        />
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="anagrafiche.emittente_billing_account"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @config-loaded="onConfigLoaded"
    >
      <!-- `is_default` e' una colonna vera del catalogo (boolean, ordinabile):
           lo slot serve solo a tenere il Badge al posto del "Si'/No". -->
      <template #cell-is_default="{ data }">
        <Badge v-if="data.is_default" :value="t('common.default')" severity="info" />
      </template>
      <template #cell-billing_account_codice="{ data }">
        {{ data.billing_account_codice || '—' }}
      </template>
      <template #cell-billing_account_ragione_sociale="{ data }">
        {{ data.billing_account_ragione_sociale || t('amministrazione.emittenti_fiscali.ba_default_label') }}
      </template>
      <!-- Slot sul `codice` della colonna (`id_fiscale`), non sul campo letto
           (`id_fiscale_univoco`): sono due nomi diversi. -->
      <template #cell-id_fiscale="{ data }">
        {{ data.id_fiscale_univoco || '—' }}
      </template>

      <!-- v-if sul TEMPLATE dello slot: senza slot `actions` la BB non monta
           la colonna (haAzioni), come la <Column v-if> pre-conversione. -->
      <template v-if="!isReadonly" #actions="{ data, compact }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)"
          :force-compact="compact" />
      </template>

      <template #empty>
        <div class="app-empty">{{ t('amministrazione.emittenti_fiscali.ba_empty') }}</div>
      </template>
    </ListaConfigurabile>
  </div>
</template>

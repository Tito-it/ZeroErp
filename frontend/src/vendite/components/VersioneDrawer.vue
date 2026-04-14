<script setup>
// Scopo: Sub-drawer dettaglio versione listino con righe prezzo.
// Righe paginata server-side con filtri (search articolo, billing account).
// Aggiunta riga via sub-drawer NuovaRigaListinoDrawer.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useSearchTable } from '../../core/composables/useSearchTable'
import { displayDate } from '../../core/utils/date'
import { statoVersioneListinoSeverity } from '../../core/utils/severity'
import { deleteRiga } from '../api/listini'
import { useListiniRigheStore } from '../stores/listiniRighe'
import { DRAWER_WIDTH } from '../../core/constants'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import NewButton from '../../core/components/NewButton.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import NuovaRigaListinoDrawer from './NuovaRigaListinoDrawer.vue'
import ApplicaVariazioneDialog from './ApplicaVariazioneDialog.vue'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'

const { t } = useI18n()
const { execute } = useApiHandler()
const isReadonly = useInjectReadonly()
const store = useListiniRigheStore()

const props = defineProps({
  visible: Boolean,
  listinoId: { type: [Number, null], required: true },
  listinoDescrizione: { type: String, default: '' },
  listinoUtilityId: { type: [Number, null], default: null },
  versione: { type: Object, required: true }
})
const emit = defineEmits(['update:visible'])

// Filtro locale per BA (oggetto completo da autocomplete).
const filterBa = ref(null)

const { searchText, onPage, onSort, paginatorProps } = useSearchTable(store, {
  defaultSortField: 'articolo_descrizione',
  defaultSortOrder: 'asc',
  extraFilters: () => ({
    billing_account_id: filterBa.value?.id ?? null
  })
})

// Watch apertura/chiusura drawer e cambio versione: configura contesto store.
watch(
  () => [props.visible, props.versione?.id],
  ([v, vid]) => {
    if (v && vid) {
      store.setContext(props.listinoId, vid)
      searchText.value = ''
      filterBa.value = null
      store.fetchList()
    } else {
      store.clearContext()
    }
  },
  { immediate: true },
)

// Sub-drawer nuova riga
const nuovaRigaVisible = ref(false)

function onNuovaRigaSaved() {
  store.fetchList()
}

async function removeRow(row) {
  await execute(() => deleteRiga(props.listinoId, props.versione.id, row.id), { successMessage: t('listini.riga_eliminata') })
  await store.fetchList()
}

const isBozza = computed(() => props.versione?.stato === 'BOZZA')

const showVariazioneDialog = ref(false)

// Disabilita dismissable del drawer quando un sub-drawer/dialog e` aperto,
// per evitare che la chiusura dell'overlay modale chiuda anche il drawer padre.
const hasChildOpen = computed(() => nuovaRigaVisible.value || showVariazioneDialog.value)

function onVariazioneApplied() {
  store.fetchList()
}

function onFilterBaChange(val) {
  filterBa.value = val
  store.filters.billing_account_id = val?.id ?? null
  store.filters.offset = 0
  store.fetchList()
}

function onFilterBaClear() {
  filterBa.value = null
  store.filters.billing_account_id = null
  store.filters.offset = 0
  store.fetchList()
}
</script>

<template>
  <Drawer :visible="visible" @update:visible="v => emit('update:visible', v)"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE }" :dismissable="!hasChildOpen">
    <template #header>
      <DrawerTitle :action="versione?.codice_versione || `#${versione?.id}`"
        :title="`${t('listini.tab_righe')} — ${listinoDescrizione}`" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-row-inline" style="align-items: center;">
        <span class="form-field" style="flex: 0 0 auto;">
          <label>{{ t('listini.field_valido_dal') }}</label>
          <span>{{ displayDate(versione?.valido_dal) }}</span>
        </span>
        <span class="form-field" style="flex: 0 0 auto;">
          <label>{{ t('listini.field_valido_al') }}</label>
          <span>{{ displayDate(versione?.valido_al) || '—' }}</span>
        </span>
        <span style="margin-left: auto;">
          <Tag :value="versione?.stato" :severity="statoVersioneListinoSeverity(versione?.stato)" />
        </span>
      </div>

      <!-- Toolbar standard: filtri a sinistra, azioni a destra -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="searchText" :placeholder="t('listini.righe_cerca_articolo')"
            style="width: 200px;" />
          <BillingAccountLookup :modelValue="filterBa"
            @select="onFilterBaChange" @clear="onFilterBaClear"
            :utilityId="listinoUtilityId"
            :placeholder="t('listini.righe_filtra_ba')" style="width: 220px;" />
        </div>
        <div v-if="isBozza" class="app-page-actions">
          <Button icon="pi pi-percentage" :label="t('listini.variazione_short')"
            v-tooltip.bottom="t('listini.variazione_pct_titolo')"
            class="app-page-action" @click="showVariazioneDialog = true" />
          <NewButton :tooltip="t('listini.aggiungi_prezzo_hint')" @click="nuovaRigaVisible = true" />
        </div>
      </div>

      <DataTable :value="store.items" :loading="store.loading" striped-rows class="app-datatable" data-key="id"
        lazy v-bind="paginatorProps" @page="onPage" @sort="onSort" removable-sort
        scrollable scrollHeight="flex">
        <Column field="articolo_codice" :header="t('listini.col_articolo')" sortable style="width: 120px;" />
        <Column field="articolo_descrizione" :header="t('catalogo.col_descrizione')" sortable style="min-width: 200px;" />
        <Column field="uom_codice" :header="t('catalogo.col_uom')" style="width: 70px;" />
        <Column field="prezzo" :header="t('listini.col_prezzo')" sortable style="width: 110px;">
          <template #body="{ data }">{{ data.prezzo }}</template>
        </Column>
        <Column field="billing_account_descrizione" :header="t('listini.col_ba')" sortable style="min-width: 200px;" />
        <Column v-if="isBozza" style="width: 50px;">
          <template #body="{ data }">
            <Button icon="pi pi-trash" text rounded size="small" class="app-delete-btn" @click="removeRow(data)" />
          </template>
        </Column>
      </DataTable>
    </div>

    <NuovaRigaListinoDrawer
      :visible="nuovaRigaVisible"
      @update:visible="v => nuovaRigaVisible = v"
      :listino-id="listinoId"
      :versione-id="versione?.id"
      :listino-utility-id="listinoUtilityId"
      @saved="onNuovaRigaSaved" />

    <ApplicaVariazioneDialog
      :visible="showVariazioneDialog"
      @update:visible="v => showVariazioneDialog = v"
      :listino-id="listinoId"
      :versione-id="versione?.id"
      @applied="onVariazioneApplied" />
  </Drawer>
</template>

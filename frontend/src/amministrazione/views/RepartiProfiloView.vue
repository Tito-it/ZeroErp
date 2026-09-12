<script setup>
// Scopo: pagina lista reparti con DataTable.
// Click riga -> apre RepartoProfiloEditor drawer.
import { onActivated, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRepartiStore } from '../stores/reparti'
import { useTabEvents } from '../../core/composables/useTabEvents'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import RepartoProfiloEditor from '../components/RepartoProfiloEditor.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Badge from 'primevue/badge'

const { t } = useI18n()
const store = useRepartiStore()
useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
const { onDataChanged } = useTabEvents()

const editorVisible = ref(false)
const selectedUoId = ref(null)
const selectedUoNome = ref('')

const cleanup = onDataChanged(e => {
  if (e.entityType === 'profilo-reparto') store.fetchList()
})
onUnmounted(cleanup)

// ⚠️ `onActivated` e non `onMounted`: la view vive sotto `<KeepAlive :max="10">`
//    (AppLayout), quindi al rientro `onMounted` non riscatta e a video resterebbe
//    l'elenco di prima. ⛔ Sostituisce, non si aggiunge: sotto KeepAlive al primo
//    montaggio scattano ENTRAMBI, quindi tenerli tutti e due farebbe due fetch.
onActivated(() => {
  store.fetchList()
})

function onRowClick(event) {
  selectedUoId.value = event.data.id
  selectedUoNome.value = event.data.descrizione
  editorVisible.value = true
}

function onEditorSaved() {
  editorVisible.value = false
  store.fetchList()
}

function profiloSeverity(count) {
  return count > 0 ? 'success' : 'warn'
}
</script>

<template>
  <div class="app-page">
    <DataTable
      :value="store.items"
      :loading="store.loading"
      striped-rows
      scrollable
      scrollHeight="flex"
      class="app-datatable"
      @row-click="onRowClick"
      selection-mode="single"
      data-key="id"
    >
      <Column field="descrizione" :header="t('amministrazione.col_reparto')" />
      <Column field="profilo_aree_count" :header="t('amministrazione.col_profilo')">
        <template #body="{ data }">
          <Badge
            :value="data.profilo_aree_count > 0 ? t('amministrazione.profilo_configurato') : t('amministrazione.profilo_mancante')"
            :severity="profiloSeverity(data.profilo_aree_count)"
          />
        </template>
      </Column>
      <Column field="operatori_count" :header="t('amministrazione.col_operatori')" />
    </DataTable>

    <RepartoProfiloEditor
      v-model:visible="editorVisible"
      :uo-id="selectedUoId"
      :uo-nome="selectedUoNome"
      @saved="onEditorSaved"
      @cancelled="editorVisible = false"
    />
  </div>
</template>

<!-- Stile .app-page definito in main.css -->

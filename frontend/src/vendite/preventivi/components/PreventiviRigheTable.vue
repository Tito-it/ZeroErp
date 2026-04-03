<script setup>
// Scopo: Tabella righe preventivo con visualizzazione inline.
// Le righe si caricano dal dettaglio, modifica/aggiunta via PreventiviRigaForm.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../core/composables/useApiHandler'
import { useConfirmAction } from '../../../core/composables/useConfirmAction'
import { usePreventiviStore } from '../stores/preventivi'
import PreventiviRigaForm from './PreventiviRigaForm.vue'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'

const { t } = useI18n()
const store = usePreventiviStore()
const { execute, loading } = useApiHandler()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  preventivoId: { type: Number, required: true },
  isModificabile: { type: Boolean, default: true }
})

const righe = ref([])
const rigaDialogVisible = ref(false)
const rigaSelezionata = ref(null)

// Scopo: Carica righe dal backend.
async function loadRighe() {
  if (!props.preventivoId) return
  righe.value = await store.loadRighe(props.preventivoId)
}

watch(() => props.preventivoId, loadRighe, { immediate: true })

// Scopo: Apri dialog per nuova riga.
function onNuovaRiga() {
  rigaSelezionata.value = null
  rigaDialogVisible.value = true
}

// Scopo: Apri dialog per modifica riga.
function onEditRiga(riga) {
  rigaSelezionata.value = riga
  rigaDialogVisible.value = true
}

// Scopo: Salva riga (crea o aggiorna).
async function onRigaSaved() {
  rigaDialogVisible.value = false
  await loadRighe()
}

// Scopo: Elimina riga con conferma.
function onDeleteRiga(riga) {
  confirmAction({
    message: t('preventivi.conferma_elimina_riga'),
    accept: async () => {
      await execute(
        () => store.eliminaRiga(props.preventivoId, riga.id),
        { successMessage: t('preventivi.riga_eliminata') }
      )
      await loadRighe()
    }
  })
}

function formatCurrency(value) {
  if (value == null) return ''
  return Number(value).toLocaleString('it-IT', { style: 'currency', currency: 'EUR' })
}

function formatNumber(value) {
  if (value == null) return ''
  return Number(value).toLocaleString('it-IT', { minimumFractionDigits: 2 })
}

defineExpose({ loadRighe })
</script>

<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
      <h4 style="margin: 0;">{{ t('preventivi.section_righe') }}</h4>
      <Button v-if="isModificabile" icon="pi pi-plus" :label="t('preventivi.aggiungi_riga')"
        size="small" severity="success" @click="onNuovaRiga" />
    </div>

    <DataTable :value="righe" striped-rows size="small" class="app-datatable"
      scrollable scrollHeight="250px" data-key="id">
      <Column field="articolo_codice" :header="t('preventivi.riga_articolo')" style="min-width: 140px;" />
      <Column field="descrizione" :header="t('preventivi.riga_descrizione')" style="min-width: 180px;" />
      <Column field="quantita" :header="t('preventivi.riga_quantita')" style="width: 90px;">
        <template #body="{ data }">{{ formatNumber(data.quantita) }}</template>
      </Column>
      <Column field="uom_codice" :header="t('preventivi.riga_uom')" style="width: 70px;" />
      <Column field="prezzo_unitario" :header="t('preventivi.riga_prezzo')" style="width: 110px;">
        <template #body="{ data }">{{ formatCurrency(data.prezzo_unitario) }}</template>
      </Column>
      <Column field="sconto_percentuale" :header="t('preventivi.riga_sconto')" style="width: 80px;">
        <template #body="{ data }">{{ data.sconto_percentuale ? `${data.sconto_percentuale}%` : '' }}</template>
      </Column>
      <Column field="importo_riga" :header="t('preventivi.riga_importo')" style="width: 120px;">
        <template #body="{ data }">{{ formatCurrency(data.importo_riga) }}</template>
      </Column>
      <Column field="iva_descrizione" :header="t('preventivi.riga_iva')" style="width: 80px;" />
      <Column v-if="isModificabile" style="width: 80px;">
        <template #body="{ data }">
          <div style="display: flex; gap: 0.25rem;">
            <Button icon="pi pi-pencil" text size="small" @click="onEditRiga(data)" />
            <Button icon="pi pi-trash" text size="small" severity="danger" @click="onDeleteRiga(data)" />
          </div>
        </template>
      </Column>
    </DataTable>

    <Dialog v-model:visible="rigaDialogVisible" :header="rigaSelezionata ? t('preventivi.modifica_riga') : t('preventivi.nuova_riga')"
      :style="{ width: '600px' }" modal :closable="true">
      <PreventiviRigaForm
        :preventivo-id="preventivoId"
        :riga="rigaSelezionata"
        @saved="onRigaSaved"
        @cancel="rigaDialogVisible = false"
      />
    </Dialog>
  </div>
</template>

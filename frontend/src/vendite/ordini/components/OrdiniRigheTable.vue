<script setup>
// Scopo: righe ordine master-detail inline. Thin wrapper su
//        `core/components/RigheMasterDetailTable.vue` (B10, regola del 2): la
//        macchina a stati vive nel BB, qui restano solo colonne e form di riga.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOrdiniStore } from '../stores/ordini'
import { formatCurrency, formatNumber } from '../../../core/utils/format'
import { displayDate } from '../../../core/utils/date'
import RigheMasterDetailTable from '../../../core/components/RigheMasterDetailTable.vue'
import OrdiniRigaForm from './OrdiniRigaForm.vue'
import Column from 'primevue/column'

const { t } = useI18n()
const store = useOrdiniStore()

defineProps({
  ordineId: { type: Number, required: true },
  isModificabile: { type: Boolean, default: true },
})
const emit = defineEmits(['changed', 'form-aperto'])

// Il drawer parent (OrdiniDrawer) chiama loadRighe sul ref: ri-espone quello del BB.
const tableRef = ref(null)
defineExpose({ loadRighe: () => tableRef.value?.loadRighe() })
</script>

<template>
  <RigheMasterDetailTable
    ref="tableRef"
    :parent-id="ordineId"
    :rows-loader="(id) => store.loadRighe(id)"
    :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
    :is-modificabile="isModificabile"
    title-key="vendite.ordini.section_righe"
    new-tooltip-key="vendite.ordini.aggiungi_riga"
    confirm-delete-key="vendite.ordini.conferma_elimina_riga"
    deleted-message-key="vendite.ordini.riga_eliminata"
    new-label-key="vendite.ordini.nuova_riga"
    edit-label-key="vendite.ordini.modifica_riga"
    sort-field="riga_nr"
    @changed="emit('changed')"
    @form-aperto="emit('form-aperto', $event)"
  >
    <template #columns>
      <Column field="articolo_codice" :header="t('vendite.ordini.riga_articolo')" sortable style="width: 120px;" />
      <Column field="descrizione" :header="t('vendite.ordini.riga_descrizione')" sortable />
      <Column field="qta_operativa" :header="t('vendite.ordini.riga_quantita')" sortable style="width: 90px;">
        <template #body="{ data }">{{ formatNumber(data.qta_operativa) }}</template>
      </Column>
      <Column field="uom_codice" :header="t('vendite.ordini.riga_uom')" style="width: 70px;" />
      <Column field="prezzo_unitario" :header="t('vendite.ordini.riga_prezzo')" sortable style="width: 130px;">
        <template #body="{ data }">
          {{ formatCurrency(data.prezzo_unitario, { minimumFractionDigits: 6, maximumFractionDigits: 6 }) }}
        </template>
      </Column>
      <Column field="sconto_percentuale" :header="t('vendite.ordini.riga_sconto')" sortable style="width: 80px;">
        <template #body="{ data }">{{ data.sconto_percentuale ? `${data.sconto_percentuale}%` : '' }}</template>
      </Column>
      <Column field="importo_riga" :header="t('vendite.ordini.riga_importo')" sortable style="width: 120px;">
        <template #body="{ data }">{{ formatCurrency(data.importo_riga) }}</template>
      </Column>
      <Column field="iva_descrizione" :header="t('vendite.ordini.riga_iva')" sortable style="width: 80px;">
        <template #body="{ data }">{{ data.iva_descrizione || data.iva_codice || '' }}</template>
      </Column>
      <!-- La data di consegna della riga (Blocco A): a video la PROMESSA
           (confermata) se c'e', altrimenti la RICHIESTA del cliente — la stessa
           regola con cui la situazione merce misura il ritardo. Il tooltip
           dice quale delle due si sta leggendo. -->
      <Column field="data_consegna_confermata" :header="t('vendite.ordini.riga_data_consegna')" sortable style="width: 110px;">
        <template #body="{ data }">
          <span v-if="data.data_consegna_confermata"
            v-tooltip.top="t('vendite.ordini.riga_data_consegna_confermata')">
            {{ displayDate(data.data_consegna_confermata) }}
          </span>
          <span v-else-if="data.data_consegna_richiesta_cliente" class="app-text-muted"
            v-tooltip.top="t('vendite.ordini.riga_data_consegna_richiesta_cliente')">
            {{ displayDate(data.data_consegna_richiesta_cliente) }}
          </span>
        </template>
      </Column>
    </template>

    <template #form="{ riga, onSaved, onComponentiChanged, onCancel }">
      <OrdiniRigaForm
        :ordine-id="ordineId"
        :riga="riga"
        @saved="onSaved"
        @componenti-changed="onComponentiChanged"
        @cancel="onCancel"
      />
    </template>
  </RigheMasterDetailTable>
</template>

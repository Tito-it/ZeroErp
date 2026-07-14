<script setup>
// Scopo: righe reso master-detail inline. Thin wrapper su
//        `core/components/RigheMasterDetailTable.vue` (B10, regola del 2):
//        la macchina a stati vive nel BB, qui restano colonne e form di riga.
//        Post-conferma le righe per ri-consegna espongono lo stato copertura
//        derivato (Tag) + quantita' residua. Clone ridotto di DdtRigheTable.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Column from 'primevue/column'

import RigheMasterDetailTable from '../../../core/components/RigheMasterDetailTable.vue'
import { formatNumber } from '../../../core/utils/format'
import { statoRiconsegnaSeverity } from '../../../core/utils/severity'
import { useResiStore } from '../stores/resi'
import ResoRigaForm from './ResoRigaForm.vue'

const { t } = useI18n()
const store = useResiStore()

defineProps({
  resoId: { type: Number, required: true },
  // DDT di origine del reso: serve al form riga per proporre le righe DDT
  // con residuo rendibile.
  ddtOrigineId: { type: [Number, null], default: null },
  isModificabile: { type: Boolean, default: true },
})
const emit = defineEmits(['changed', 'form-aperto'])

// Il drawer parent chiama loadRighe sul ref: ri-espone quello del BB.
const tableRef = ref(null)
defineExpose({ loadRighe: () => tableRef.value?.loadRighe() })
</script>

<template>
  <RigheMasterDetailTable
    ref="tableRef"
    :parent-id="resoId"
    :rows-loader="(id) => store.loadRighe(id)"
    :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
    :is-modificabile="isModificabile"
    title-key="vendite.resi.section_righe"
    new-tooltip-key="vendite.resi.aggiungi_riga"
    confirm-delete-key="vendite.resi.conferma_elimina_riga"
    deleted-message-key="vendite.resi.riga_eliminata"
    new-label-key="vendite.resi.nuova_riga"
    edit-label-key="vendite.resi.modifica_riga"
    sort-field="riga_nr"
    @changed="emit('changed')"
    @form-aperto="emit('form-aperto', $event)"
  >
    <template #columns>
      <Column field="articolo_codice" :header="t('vendite.resi.riga_articolo')" sortable style="width: 120px;" />
      <Column field="descrizione" :header="t('vendite.resi.riga_descrizione')" sortable />
      <Column field="qta_operativa" :header="t('vendite.resi.riga_quantita')" sortable style="width: 100px;">
        <template #body="{ data }">{{ formatNumber(data.qta_operativa) }}</template>
      </Column>
      <Column field="uom_codice" :header="t('vendite.resi.riga_uom')" style="width: 70px;" />
      <Column field="tipo_reso_descrizione" :header="t('vendite.resi.riga_tipo')" sortable style="width: 160px;" />
      <Column field="motivo" :header="t('vendite.resi.riga_motivo')" />
      <!-- Copertura ri-consegna: solo per righe con riapre_residuo (derivata). -->
      <Column field="stato_riconsegna" :header="t('vendite.resi.riga_stato_riconsegna')" style="width: 140px;">
        <template #body="{ data }">
          <Tag v-if="data.stato_riconsegna"
            :value="t(`vendite.resi.riconsegna_stato.${data.stato_riconsegna}`)"
            :severity="statoRiconsegnaSeverity(data.stato_riconsegna)" />
        </template>
      </Column>
    </template>

    <template #form="{ riga, onSaved, onCancel }">
      <ResoRigaForm
        :reso-id="resoId"
        :ddt-origine-id="ddtOrigineId"
        :riga="riga"
        @saved="onSaved"
        @cancel="onCancel"
      />
    </template>
  </RigheMasterDetailTable>
</template>

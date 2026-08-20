<script setup>
// Scopo: righe DDT master-detail inline. Thin wrapper su
//        `core/components/RigheMasterDetailTable.vue` (B10, regola del 2): la
//        macchina a stati vive nel BB, qui restano solo colonne e form di riga.
//        Clone di OrdiniRigheTable (§D-4).
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDdtStore } from '../stores/ddt'
import { formatCurrency, formatNumber } from '../../../core/utils/format'
import RigheMasterDetailTable from '../../../core/components/RigheMasterDetailTable.vue'
import DdtRigaForm from './DdtRigaForm.vue'
import Column from 'primevue/column'
import Tag from 'primevue/tag'

const { t } = useI18n()
const store = useDdtStore()

defineProps({
  ddtId: { type: Number, required: true },
  isModificabile: { type: Boolean, default: true },
  // FE-A: la causale del documento vende? Serve al form e ai componenti per
  // decidere se il prezzo e' obbligatorio (default `true` = comportamento
  // storico, cosi' un chiamante che non la passa non cambia).
  causaleFatturabile: { type: Boolean, default: true },
})
const emit = defineEmits(['changed', 'form-aperto'])

// Il drawer parent (DdtDrawer) chiama loadRighe sul ref: ri-espone quello del BB.
const tableRef = ref(null)
defineExpose({ loadRighe: () => tableRef.value?.loadRighe() })
</script>

<template>
  <RigheMasterDetailTable
    ref="tableRef"
    :parent-id="ddtId"
    :rows-loader="(id) => store.loadRighe(id)"
    :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
    :is-modificabile="isModificabile"
    title-key="vendite.ddt.section_righe"
    new-tooltip-key="vendite.ddt.aggiungi_riga"
    confirm-delete-key="vendite.ddt.conferma_elimina_riga"
    deleted-message-key="vendite.ddt.riga_eliminata"
    new-label-key="vendite.ddt.nuova_riga"
    edit-label-key="vendite.ddt.modifica_riga"
    sort-field="riga_nr"
    @changed="emit('changed')"
    @form-aperto="emit('form-aperto', $event)"
  >
    <template #columns>
      <Column field="articolo_codice" :header="t('vendite.ddt.riga_articolo')" sortable style="width: 120px;" />
      <Column field="descrizione" :header="t('vendite.ddt.riga_descrizione')" sortable />
      <Column field="qta_operativa" :header="t('vendite.ddt.riga_quantita')" sortable style="width: 90px;">
        <template #body="{ data }">{{ formatNumber(data.qta_operativa) }}</template>
      </Column>
      <Column field="uom_codice" :header="t('vendite.ddt.riga_uom')" style="width: 70px;" />
      <!-- DEC-6: prezzo assente non e' prezzo zero. Senza il Tag la cella
           resterebbe vuota (o peggio, 0,00) e l'operatore non saprebbe se il
           prezzo manca o se qualcuno ha deciso che vale zero. -->
      <Column field="prezzo_unitario" :header="t('vendite.ddt.riga_prezzo')" sortable style="width: 130px;">
        <template #body="{ data }">
          <Tag v-if="data.prezzo_unitario == null"
               severity="secondary" :value="t('vendite.ddt.riga_senza_prezzo')" />
          <template v-else>
            {{ formatCurrency(data.prezzo_unitario, { minimumFractionDigits: 6, maximumFractionDigits: 6 }) }}
          </template>
        </template>
      </Column>
      <Column field="sconto_percentuale" :header="t('vendite.ddt.riga_sconto')" sortable style="width: 80px;">
        <template #body="{ data }">{{ data.sconto_percentuale ? `${data.sconto_percentuale}%` : '' }}</template>
      </Column>
      <!-- Dopo B4 l'importo arriva NULL quando manca il prezzo: stessa cura. -->
      <Column field="importo_riga" :header="t('vendite.ddt.riga_importo')" sortable style="width: 120px;">
        <template #body="{ data }">
          <Tag v-if="data.importo_riga == null"
               severity="secondary" :value="t('vendite.ddt.riga_senza_prezzo')" />
          <template v-else>{{ formatCurrency(data.importo_riga) }}</template>
        </template>
      </Column>
      <Column field="iva_descrizione" :header="t('vendite.ddt.riga_iva')" sortable style="width: 80px;">
        <template #body="{ data }">{{ data.iva_descrizione || data.iva_codice || '' }}</template>
      </Column>
    </template>

    <template #form="{ riga, onSaved, onComponentiChanged, onCancel }">
      <DdtRigaForm
        :ddt-id="ddtId"
        :riga="riga"
        :causale-fatturabile="causaleFatturabile"
        @saved="onSaved"
        @componenti-changed="onComponentiChanged"
        @cancel="onCancel"
      />
    </template>
  </RigheMasterDetailTable>
</template>

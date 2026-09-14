<script setup>
// Scopo: righe preventivo master-detail inline. Thin wrapper su
//        `core/components/RigheMasterDetailTable.vue` (B10, regola del 2): la
//        macchina a stati vive nel BB, qui restano colonne (col badge
//        approvazione prezzo), form di riga e il predicato "elimina bloccato
//        su PENDING".
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePreventiviStore } from '../stores/preventivi'
import { formatCurrency, formatNumber } from '../../../core/utils/format'
import { displayDate } from '../../../core/utils/date'
import { coerceJsonbToObject } from '../../../core/utils/meta'
import { STATO_APPROVAZIONE } from '../../constants'
import RigheMasterDetailTable from '../../../core/components/RigheMasterDetailTable.vue'
import PreventiviRigaForm from './PreventiviRigaForm.vue'
import Column from 'primevue/column'
import Tag from 'primevue/tag'

const { t } = useI18n()
const store = usePreventiviStore()

defineProps({
  preventivoId: { type: Number, required: true },
  // Refactor cascata 2026-05-15: propaga al PreventiviRigaForm per la
  // cascata soglie L2 con livello categoria_cliente del BA.
  billingAccountId: { type: Number, default: null },
  isModificabile: { type: Boolean, default: true },
})
const emit = defineEmits(['changed', 'form-aperto'])

const tableRef = ref(null)
defineExpose({ loadRighe: () => tableRef.value?.loadRighe() })

// Elimina bloccata su righe con approvazione prezzo PENDING (lo blocca anche il
// backend via guard, ma il FE evita il round-trip).
function deleteDisabled(riga) {
  return riga?.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING
}

// severity Tag per stato approvazione prezzo (workflow L3): PENDING=warn,
// APPROVED=success, REJECTED=danger.
function approvazioneSeverity(stato) {
  if (stato === STATO_APPROVAZIONE.APPROVED) return 'success'
  if (stato === STATO_APPROVAZIONE.REJECTED) return 'danger'
  return 'warn'
}

function approvazioneLabel(stato) {
  if (stato === STATO_APPROVAZIONE.APPROVED) return t('vendite.preventivi.badge_approvazione_approved')
  if (stato === STATO_APPROVAZIONE.REJECTED) return t('vendite.preventivi.badge_approvazione_rejected')
  return t('vendite.preventivi.badge_approvazione_pending')
}

// Tooltip contestuale: per REJECTED legge la motivazione denormalizzata in
// `meta.approvazione_rifiuto.motivazione`; per PENDING torna il riferimento
// pratica.
function approvazioneTooltip(data) {
  if (data.stato_approvazione_prezzo === STATO_APPROVAZIONE.REJECTED) {
    const meta = coerceJsonbToObject(data.meta)
    const rif = meta.approvazione_rifiuto || {}
    if (rif.motivazione) {
      return t('vendite.preventivi.badge_approvazione_rejected_tooltip', { motivazione: rif.motivazione })
    }
    return t('vendite.preventivi.badge_approvazione_rejected_no_motivo')
  }
  if (data.stato_approvazione_prezzo === STATO_APPROVAZIONE.PENDING && data.pratica_approvazione_prezzo_id) {
    return t('vendite.preventivi.badge_approvazione_pending_tooltip', {
      pratica_id: data.pratica_approvazione_prezzo_id,
    })
  }
  return ''
}
</script>

<template>
  <RigheMasterDetailTable
    ref="tableRef"
    :parent-id="preventivoId"
    :rows-loader="(id) => store.loadRighe(id)"
    :delete-action="(id, rigaId) => store.eliminaRiga(id, rigaId)"
    :is-modificabile="isModificabile"
    :delete-disabled="deleteDisabled"
    title-key="vendite.preventivi.section_righe"
    new-tooltip-key="vendite.preventivi.aggiungi_riga"
    confirm-delete-key="vendite.preventivi.conferma_elimina_riga"
    deleted-message-key="vendite.preventivi.riga_eliminata"
    new-label-key="vendite.preventivi.nuova_riga"
    edit-label-key="vendite.preventivi.modifica_riga"
    sort-field="descrizione"
    @changed="emit('changed')"
    @form-aperto="emit('form-aperto', $event)"
  >
    <template #columns>
      <Column field="articolo_codice" :header="t('vendite.preventivi.riga_articolo')" sortable style="width: 120px;" />
      <Column field="descrizione" :header="t('vendite.preventivi.riga_descrizione')" sortable />
      <Column field="qta_operativa" :header="t('vendite.preventivi.riga_quantita')" sortable style="width: 90px;">
        <template #body="{ data }">{{ formatNumber(data.qta_operativa) }}</template>
      </Column>
      <Column field="uom_codice" :header="t('vendite.preventivi.riga_uom')" style="width: 70px;" />
      <Column field="prezzo_unitario" :header="t('vendite.preventivi.riga_prezzo')" sortable style="width: 130px;">
        <template #body="{ data }">
          <div style="display: flex; flex-direction: column; gap: 0.15rem; align-items: flex-start;">
            <span>{{ formatCurrency(data.prezzo_unitario, { minimumFractionDigits: 6, maximumFractionDigits: 6 }) }}</span>
            <Tag
              v-if="data.stato_approvazione_prezzo"
              :severity="approvazioneSeverity(data.stato_approvazione_prezzo)"
              :value="approvazioneLabel(data.stato_approvazione_prezzo)"
              v-tooltip.top="approvazioneTooltip(data)"
            />
          </div>
        </template>
      </Column>
      <Column field="sconto_percentuale" :header="t('vendite.preventivi.riga_sconto')" sortable style="width: 80px;">
        <template #body="{ data }">{{ data.sconto_percentuale ? `${data.sconto_percentuale}%` : '' }}</template>
      </Column>
      <Column field="importo_riga" :header="t('vendite.preventivi.riga_importo')" sortable style="width: 120px;">
        <template #body="{ data }">{{ formatCurrency(data.importo_riga) }}</template>
      </Column>
      <Column field="iva_descrizione" :header="t('vendite.preventivi.riga_iva')" sortable style="width: 80px;">
        <template #body="{ data }">{{ data.iva_descrizione || data.iva_codice || '' }}</template>
      </Column>
      <!-- La data di consegna richiesta dal cliente (Blocco A): sul preventivo
           c'e' solo la richiesta, e il push la porta sull'ordine. -->
      <Column field="data_consegna_richiesta_cliente" :header="t('vendite.preventivi.riga_data_consegna_richiesta_cliente')" sortable style="width: 110px;">
        <template #body="{ data }">{{ displayDate(data.data_consegna_richiesta_cliente) }}</template>
      </Column>
    </template>

    <template #form="{ riga, onSaved, onComponentiChanged, onCancel }">
      <PreventiviRigaForm
        :preventivo-id="preventivoId"
        :billing-account-id="billingAccountId"
        :riga="riga"
        @saved="onSaved"
        @componenti-changed="onComponentiChanged"
        @cancel="onCancel"
      />
    </template>
  </RigheMasterDetailTable>
</template>

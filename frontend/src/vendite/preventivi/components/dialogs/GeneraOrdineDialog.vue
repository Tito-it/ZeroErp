<script setup>
// Scopo: dialog di smistamento MERCE → ordine (modello split D8). Mostra le
// righe merce del preventivo ancora da ordinare (natura destinazione ORDINE,
// non allocate), preselezionate tutte; l'operatore conferma il sottoinsieme da
// portare a un nuovo ordine DRAFT. Emette `confirm({ righeIds })`: la POST
// /genera-ordine/ + notifica + refresh li orchestra il drawer padre (mirror di
// PreventivoEmissioneDialog).
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../../../core/composables/useApiHandler'
import AppDialog from '../../../../core/components/AppDialog.vue'
import { formatCurrency, formatNumber } from '../../../../core/utils/format'
import { listRigheSmistabiliOrdine } from '../../api/preventiviApi'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const props = defineProps({
  visible: { type: Boolean, required: true },
  preventivoId: { type: Number, default: null },
  // loading della conferma (POST), gestito dal padre.
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'confirm'])

const { t } = useI18n()
const { execute, loading: loadingRighe } = useApiHandler()

const righe = ref([])
const selected = ref([])

// Carica le righe smistabili all'apertura e preseleziona tutte (D2 "preseleziona
// tutte"; l'operatore può deselezionare per uno smistamento parziale).
async function loadRighe() {
  righe.value = []
  selected.value = []
  if (!props.preventivoId) return
  const res = await execute(() => listRigheSmistabiliOrdine(props.preventivoId))
  if (res === null) return
  righe.value = res
  selected.value = [...res]
}

watch(() => props.visible, (v) => { if (v) loadRighe() })

function onSave() {
  emit('confirm', { righeIds: selected.value.map(r => r.id) })
}
function onCancel() {
  emit('update:visible', false)
}
</script>

<template>
  <AppDialog
    :visible="visible"
    @update:visible="$emit('update:visible', $event)"
    :header="t('preventivi.genera_ordine_titolo')"
    width="xl"
    :readonly="false"
    :loading="loading"
    :save-disabled="loadingRighe || selected.length === 0"
    :save-label="t('common.confirm')"
    @save="onSave"
    @cancel="onCancel"
  >
    <p class="app-field-hint">{{ t('preventivi.genera_ordine_hint') }}</p>
    <DataTable
      :value="righe"
      v-model:selection="selected"
      dataKey="id"
      :loading="loadingRighe"
      class="app-datatable"
      size="small"
    >
      <Column selectionMode="multiple" headerStyle="width: 3rem" />
      <Column :header="t('preventivi.riga_articolo')">
        <template #body="{ data }">
          {{ data.articolo_codice }} — {{ data.articolo_descrizione }}
        </template>
      </Column>
      <Column :header="t('preventivi.riga_descrizione')" field="descrizione" />
      <Column :header="t('preventivi.riga_quantita')">
        <template #body="{ data }">
          {{ formatNumber(data.qta_operativa) }} {{ data.uom_codice }}
        </template>
      </Column>
      <Column :header="t('preventivi.riga_prezzo')">
        <template #body="{ data }">{{ formatCurrency(data.prezzo_unitario) }}</template>
      </Column>
      <template #empty>{{ t('preventivi.genera_ordine_nessuna_riga') }}</template>
    </DataTable>
  </AppDialog>
</template>

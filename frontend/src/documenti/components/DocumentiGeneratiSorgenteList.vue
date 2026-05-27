<script setup>
// Scopo: Lista documenti generati per una sorgente specifica
//        (Tranche M building block riusabile). Visualizza la
//        timeline (ORDER BY `generato_at DESC` lato BE) con azioni
//        per riga: Scarica PDF (RowActionsMenu).
//
//        v1: niente azioni di stato (ARCHIVIA/ANNULLA) ne' eliminazione
//        (trigger DB block_delete su documenti_generati).
//
//        Riusabile da qualsiasi caller che imposti la coppia
//        (sorgenteCode, sorgenteId) sullo store. Il caller e' anche
//        responsabile di chiamare `fetchList` al cambio di sorgente.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDocumentiPerSorgenteStore } from '../stores/documentiPerSorgente'
import { useNotify } from '../../core/composables/useNotify'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import DocumentoEmissioneDialog from './DocumentoEmissioneDialog.vue'
import { downloadBlob } from '../../core/utils/download'
import { MANAGE_ICONS } from '../../core/constants'

const props = defineProps({
  sorgenteCode: { type: String, required: true },
  sorgenteId: { type: [Number, null], required: true },
  // Se true, fetch automatico al mount/cambio props.
  autoFetch: { type: Boolean, default: true },
  // Se true, quando la lista e' vuota mostra solo il messaggio empty.
  hideHeaderWhenEmpty: { type: Boolean, default: false },
  // Se true, abilita l'azione di riga "Aggiungi allegati" (append di file
  // secondari al documento generato). Il caller la attiva quando lo stato
  // della sorgente lo consente (es. offerta in EMESSA).
  allowAllegati: { type: Boolean, default: false },
})

const { t } = useI18n()
const store = useDocumentiPerSorgenteStore()
const notify = useNotify()

// Stato dialog append allegati (modalita' non-advances-state).
const allegatiDialogVisible = ref(false)
const allegatiDocId = ref(null)
const allegatiLoading = ref(false)

watch(
  () => [props.sorgenteCode, props.sorgenteId],
  async ([code, id]) => {
    if (!code || !id) return
    store.setSorgente(code, id)
    if (props.autoFetch) {
      try { await store.fetchList() } catch { /* errore gia' gestito dallo store */ }
    }
  },
  { immediate: true },
)

// Scopo: Severity stato applicativo documento (DDL CHECK chiuso v1).
function statoSeverity(stato) {
  if (stato === 'GENERATO') return 'info'
  if (stato === 'ARCHIVIATO') return 'success'
  if (stato === 'ANNULLATO') return 'danger'
  return 'secondary'
}

const isEmpty = computed(() => !store.loading && (store.items?.length ?? 0) === 0)
const showListChrome = computed(() => !isEmpty.value || !props.hideHeaderWhenEmpty)

function buildRowActions(row) {
  const actions = [
    {
      key: 'download',
      label: t('documenti.lista.action_download'),
      icon: MANAGE_ICONS.DOWNLOAD,
      severity: 'primary',
      command: () => onDownload(row.id),
    },
  ]
  if (props.allowAllegati) {
    actions.push({
      key: 'allegati',
      label: t('documenti.lista.action_aggiungi_allegati'),
      icon: 'pi pi-paperclip',
      command: () => openAllegati(row.id),
    })
  }
  return actions
}

function openAllegati(documentoId) {
  allegatiDocId.value = documentoId
  allegatiDialogVisible.value = true
}

// Scopo: Append allegati al documento (modalita' non-advances-state). Su
//        conferma carica i file scelti come file secondari del documento.
async function onAllegatiConferma(payload) {
  const files = payload?.files || []
  if (!files.length || allegatiDocId.value == null) return
  allegatiLoading.value = true
  try {
    store.setSorgente(props.sorgenteCode, props.sorgenteId)
    await store.aggiungiAllegati(allegatiDocId.value, files)
    notify.success(t('documenti.allegati.aggiunti_ok'))
    allegatiDialogVisible.value = false
    await store.fetchList()
  } catch (err) {
    notify.error(t('documenti.allegati.errore'))
    console.error('aggiungiAllegati', err)
  } finally {
    allegatiLoading.value = false
  }
}

async function onDownload(documentoId) {
  try {
    const { blob, fileName } = await store.download(documentoId)
    downloadBlob(blob, fileName)
  } catch (err) {
    notify.error(t('documenti.genera_pdf.download_error'))
    console.error('download', err)
  }
}

async function reload() {
  try { await store.fetchList() } catch { /* gia' gestito */ }
}
</script>

<template>
  <div class="documenti-sorgente-list">
    <div v-if="showListChrome" class="section-header">
      <h4>{{ t('documenti.lista.title') }}</h4>
      <Button
        :icon="MANAGE_ICONS.RELOAD"
        text
        size="small"
        :loading="store.loading"
        @click="reload"
        :tooltip="t('common.refresh')"
      />
    </div>

    <DataTable
      v-if="showListChrome"
      :value="store.items"
      :loading="store.loading"
      striped-rows
      class="app-datatable"
      data-key="id"
    >
      <Column field="progressivo_sorgente" :header="t('documenti.lista.col_progressivo')" style="width: 80px;" />
      <Column field="generato_at" :header="t('documenti.lista.col_generato_at')" style="width: 180px;">
        <template #body="{ data }">
          {{ data.generato_at ? new Date(data.generato_at).toLocaleString('it-IT') : '' }}
        </template>
      </Column>
      <Column field="titolo" :header="t('documenti.lista.col_titolo')" />
      <Column field="nome_file" :header="t('documenti.lista.col_nome_file')" style="width: 200px;" />
      <Column field="stato" :header="t('documenti.lista.col_stato')" style="width: 120px;">
        <template #body="{ data }">
          <Tag :value="data.stato" :severity="statoSeverity(data.stato)" />
        </template>
      </Column>
      <Column :header="''" class="app-col-actions" style="width: 80px;">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>

    <div v-if="isEmpty" class="text-color-secondary text-center mt-1">
      {{ t('documenti.lista.empty') }}
    </div>

    <!-- Append allegati a un documento gia' generato (modalita' append). -->
    <DocumentoEmissioneDialog
      v-if="allowAllegati"
      v-model:visible="allegatiDialogVisible"
      :sorgente-code="sorgenteCode"
      :sorgente-id="sorgenteId"
      :advances-state="false"
      :header="t('documenti.allegati.dialog_titolo')"
      :confirm-label="t('documenti.allegati.conferma')"
      :loading="allegatiLoading"
      @confirm="onAllegatiConferma"
    />
  </div>
</template>

<style scoped>
.documenti-sorgente-list .section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
</style>

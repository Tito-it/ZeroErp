<script setup>
// Scopo: Dialog di conferma attivazione versione listino con preview auto-close
//        delle precedenti (decisione D3 sviluppo-listini-v2).
//        Workflow: il padre passa preview=null all'apertura, il dialog richiede
//        al backend il dry_run, mostra l'elenco delle versioni che verranno
//        chiuse e il nuovo valido_al, poi su conferma esegue il POST reale.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { changeVersioneStato } from '../api/listini'
import { displayDate } from '../../core/utils/date'
import Dialog from 'primevue/dialog'
import Button from 'primevue/button'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'

const { t } = useI18n()
const { execute, loading } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  listinoId: { type: Number, default: null },
  versione: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'confirmed'])

const preview = ref(null)
const previewLoading = ref(false)
const previewError = ref(null)

async function loadPreview() {
  if (!props.listinoId || !props.versione?.id) return
  preview.value = null
  previewError.value = null
  previewLoading.value = true
  try {
    // dry_run=true: il backend valida tutto e restituisce la lista versioni che
    // verrebbero auto-chiuse, senza scrivere nulla nel DB.
    const res = await changeVersioneStato(props.listinoId, props.versione.id, {
      stato: 'ATTIVA',
      dry_run: true,
    })
    preview.value = res.data?.data ?? res.data
  } catch (err) {
    previewError.value = err?.response?.data?.error?.message || t('common.error_loading')
  } finally {
    previewLoading.value = false
  }
}

// Carica la preview ogni volta che il dialog viene aperto su una versione.
watch(
  () => [props.visible, props.versione?.id],
  ([v, _vid]) => {
    if (v) {
      loadPreview()
    } else {
      preview.value = null
      previewError.value = null
    }
  },
  { immediate: true },
)

async function handleConfirm() {
  if (!props.listinoId || !props.versione?.id) return
  // Chiamata reale: niente dry_run, esegue auto-close + transizione in transazione.
  const result = await execute(
    () => changeVersioneStato(props.listinoId, props.versione.id, { stato: 'ATTIVA' }),
    { successMessage: t('listini.stato_aggiornato') },
  )
  if (result !== null) {
    emit('confirmed', { listinoId: props.listinoId, versioneId: props.versione.id })
    close()
  }
}

function close() {
  emit('update:visible', false)
}
</script>

<template>
  <Dialog
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    modal
    :header="t('listini.attiva_versione_titolo')"
    :style="{ width: '560px' }"
    :dismissable-mask="!loading"
    :closable="!loading"
  >
    <div v-if="versione" class="app-drawer-section">
      <h4>{{ versione.codice_versione }}</h4>
      <p class="app-text-muted">
        {{ t('listini.field_valido_dal') }}: {{ displayDate(versione.valido_dal) }}
        <span v-if="versione.valido_al"> · {{ t('listini.field_valido_al') }}: {{ displayDate(versione.valido_al) }}</span>
      </p>
    </div>

    <div v-if="previewLoading" class="app-loading mt-1">
      <ProgressSpinner style="width: 32px; height: 32px;" />
    </div>

    <Message v-else-if="previewError" severity="error" :closable="false" class="mt-1">
      {{ previewError }}
    </Message>

    <template v-else-if="preview">
      <div v-if="!preview.auto_close?.length" class="mt-1">
        <Message severity="info" :closable="false">
          {{ t('listini.attivazione_no_precedenti') }}
        </Message>
      </div>
      <template v-else>
        <Message severity="warn" :closable="false" class="mt-1">
          {{ t('listini.attivazione_autoclose_warning', { count: preview.auto_close.length }) }}
        </Message>
        <DataTable :value="preview.auto_close" class="app-datatable mt-1" striped-rows data-key="id">
          <Column field="codice_versione" :header="t('listini.col_codice_versione')" style="width: 140px;" />
          <Column :header="t('listini.field_valido_dal')" style="width: 110px;">
            <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
          </Column>
          <Column :header="t('listini.attivazione_valido_al_prima')" style="width: 110px;">
            <template #body="{ data }">{{ displayDate(data.valido_al_prima) || '∞' }}</template>
          </Column>
          <Column :header="t('listini.attivazione_valido_al_dopo')" style="width: 110px;">
            <template #body="{ data }">{{ displayDate(data.valido_al_dopo) }}</template>
          </Column>
        </DataTable>
      </template>
    </template>

    <template #footer>
      <Button :label="t('common.cancel')" text @click="close" :disabled="loading" />
      <Button
        :label="t('listini.conferma_attivazione')"
        icon="pi pi-check"
        :loading="loading"
        :disabled="!preview || !!previewError"
        @click="handleConfirm"
      />
    </template>
  </Dialog>
</template>

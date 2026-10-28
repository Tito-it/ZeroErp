<script setup>
// Scopo: Dialog di conferma attivazione versione listino con preview auto-close
//        delle precedenti (decisione D3 sviluppo-listini-v2).
//        Workflow: il padre passa preview=null all'apertura, il dialog richiede
//        al backend il dry_run, mostra l'elenco delle versioni che verranno
//        chiuse e il nuovo valido_al, poi su conferma esegue il POST reale.
//        Data `valido_dal` modificabile inline: l'admin puo' decidere all'ultimo
//        momento una data diversa da quella salvata sulla BOZZA (caso d'uso:
//        vecchia bozza con valido_dal nel passato che si vuole spostare a oggi
//        o a una data futura). Il cambio data fa un PATCH `updateVersione` +
//        ri-fetch del preview, perche' le versioni auto-chiuse dipendono dalla
//        data.
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { changeVersioneStato, updateVersione } from '../api/listini'
import { displayDate, toDateString, parseIsoDate } from '../../core/utils/date'
import { DATE_FORMAT } from '../../core/constants'
import { STATO_VERSIONE_LISTINO } from '../constants'
import AppDialog from '../../core/components/AppDialog.vue'
// DataTable grezza: anteprima dry_run delle versioni che l'attivazione
// chiuderebbe, dentro il dialog di conferma — non paginata, non configurabile.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'
import ProgressSpinner from 'primevue/progressspinner'
import DatePicker from 'primevue/datepicker'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

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

// Data modificabile (oggetto Date locale per il DatePicker). Init = valido_dal
// salvato della BOZZA; l'admin puo' cambiarla prima di confermare.
const dataValidoDal = ref(null)
// Stato salvataggio cambio data (PATCH updateVersione).
const updatingDate = ref(false)
const dateError = ref(null)

async function loadPreview() {
  if (!props.listinoId || !props.versione?.id) return
  preview.value = null
  previewError.value = null
  previewLoading.value = true
  try {
    // dry_run=true: il verbo del DB gira in un savepoint annullato (rifiuta come
    // il gesto vero) e il backend restituisce le versioni che verrebbero
    // auto-chiuse, senza scrivere nulla.
    const res = await changeVersioneStato(props.listinoId, props.versione.id, {
      stato: STATO_VERSIONE_LISTINO.ATTIVA,
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
// Inizializza anche `dataValidoDal` col valore corrente per il DatePicker.
watch(
  () => [props.visible, props.versione?.id],
  ([v]) => {
    if (v) {
      dataValidoDal.value = props.versione?.valido_dal
        ? parseIsoDate(props.versione.valido_dal)
        : null
      dateError.value = null
      loadPreview()
    } else {
      preview.value = null
      previewError.value = null
      dataValidoDal.value = null
      dateError.value = null
    }
  },
  { immediate: true },
)

// PATCH versione con nuova data + ricarica preview. Chiamato al
// @date-select del DatePicker (no debounce: l'evento scatta sulla scelta
// finale dell'utente, non sul typing). Se la nuova data == originale,
// skippa per evitare PATCH inutile.
async function onDateChange(newDate) {
  if (!props.listinoId || !props.versione?.id) return
  const newIso = newDate ? toDateString(newDate) : null
  const originalIso = props.versione?.valido_dal
    ? toDateString(parseIsoDate(props.versione.valido_dal))
    : null
  if (!newIso || newIso === originalIso) return
  dateError.value = null
  updatingDate.value = true
  try {
    await updateVersione(props.listinoId, props.versione.id, { valido_dal: newIso })
    // La versione in memoria del parent non viene aggiornata: il prossimo
    // open del dialog leggera' il nuovo valido_dal dalla lista. Nel
    // contesto attuale del dialog usiamo il `dataValidoDal` locale per la
    // preview (che chiede al BE i nuovi auto-close calcolati sul DB).
    await loadPreview()
    // La data e' gia' salvata: e' la nuova base della fotografia, o uscire
    // chiederebbe «modifiche non salvate» per una modifica gia' a DB.
    fotografia.fissa()
  } catch (err) {
    dateError.value = err?.response?.data?.error?.message || t('common.error_generic')
    // Rollback UI: ripristina la data precedente nel DatePicker.
    dataValidoDal.value = props.versione?.valido_dal
      ? parseIsoDate(props.versione.valido_dal)
      : null
  } finally {
    updatingDate.value = false
  }
}

async function handleConfirm() {
  if (!props.listinoId || !props.versione?.id) return
  // Chiamata reale: niente dry_run, esegue auto-close + transizione in transazione.
  // Il valido_dal e' gia' stato persistito da onDateChange (se modificato).
  const result = await execute(
    () => changeVersioneStato(props.listinoId, props.versione.id, { stato: STATO_VERSIONE_LISTINO.ATTIVA }),
    { successMessage: t('vendite.listini.stato_aggiornato') },
  )
  if (result !== null) {
    emit('confirmed', { listinoId: props.listinoId, versioneId: props.versione.id })
    close()
  }
}

function close() {
  emit('update:visible', false)
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ dataValidoDal: dataValidoDal.value }), { visibile: () => props.visible })
</script>

<template>
  <!-- ESC spento anche mentre si aggiorna la data inline (`updatingDate`):
       il `loading` del salvataggio lo copre gia' il BB, questo secondo
       lavoro in volo e' solo di questo dialog. -->
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    :header="t('vendite.listini.attiva_versione_titolo')"
    width="md"
    :close-on-escape="!updatingDate"
    :save-label="t('vendite.listini.conferma_attivazione')"
    :loading="loading"
    :save-disabled="!preview || !!previewError || updatingDate"
    @save="handleConfirm"
  >
    <div v-if="versione" class="app-drawer-section">
      <h4>{{ versione.codice_versione }}</h4>
      <div class="form-grid-2col mt-05">
        <div class="form-field">
          <label>{{ t('vendite.listini.field_valido_dal') }} *</label>
          <DatePicker v-model="dataValidoDal" :dateFormat="DATE_FORMAT" showIcon
            :disabled="updatingDate || loading"
            @date-select="onDateChange" />
          <small v-if="updatingDate" class="app-text-muted">
            {{ t('common.saving') }}
          </small>
          <small v-else-if="dateError" class="app-field-error">{{ dateError }}</small>
        </div>
        <div class="form-field">
          <label>{{ t('vendite.listini.field_valido_al') }}</label>
          <span>{{ displayDate(versione.valido_al) || '—' }}</span>
        </div>
      </div>
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
          {{ t('vendite.listini.attivazione_no_precedenti') }}
        </Message>
      </div>
      <template v-else>
        <Message severity="warn" :closable="false" class="mt-1">
          {{ t('vendite.listini.attivazione_autoclose_warning', { count: preview.auto_close.length }) }}
        </Message>
        <DataTable :value="preview.auto_close" class="app-datatable mt-1" striped-rows data-key="id">
          <Column field="codice_versione" :header="t('vendite.listini.col_codice_versione')" style="width: 140px;" />
          <Column :header="t('vendite.listini.field_valido_dal')" style="width: 110px;">
            <template #body="{ data }">{{ displayDate(data.valido_dal) }}</template>
          </Column>
          <Column :header="t('vendite.listini.attivazione_valido_al_prima')" style="width: 110px;">
            <template #body="{ data }">{{ displayDate(data.valido_al_prima) || '∞' }}</template>
          </Column>
          <Column :header="t('vendite.listini.attivazione_valido_al_dopo')" style="width: 110px;">
            <template #body="{ data }">{{ displayDate(data.valido_al_dopo) }}</template>
          </Column>
        </DataTable>
      </template>
    </template>
  </AppDialog>
</template>

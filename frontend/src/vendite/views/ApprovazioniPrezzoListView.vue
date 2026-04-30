<script setup>
// Scopo: Coda approver workflow L3 approvazione prezzo (Sprint E listini v5 §14.6).
//        Lista paginata pratiche tipo APPROVAZIONE_PREZZO in stato APERTA,
//        scope emittente derivato dal JWT operatore. Azioni di riga
//        approva/rifiuta con dialog conferma + nota opzionale.
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotify } from '../../core/composables/useNotify'
import { extractApiError } from '../../core/utils/apiError'
import {
  listCodaApprovazioni,
  approvaPrezzoRiga,
  rifiutaPrezzoRiga,
} from '../api/approvazioniPrezzo'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import Textarea from 'primevue/textarea'

const { t } = useI18n()
const notify = useNotify()

const items = ref([])
const total = ref(0)
const loading = ref(false)
const limit = ref(50)
const offset = ref(0)

// Dialog stato (approva | rifiuta)
const dialogVisible = ref(false)
const dialogMode = ref(null)  // 'approva' | 'rifiuta'
const dialogPratica = ref(null)
const dialogText = ref('')

const dialogTitle = computed(() =>
  dialogMode.value === 'approva'
    ? t('approvazioni_prezzo.approva_dialog_title')
    : t('approvazioni_prezzo.rifiuta_dialog_title')
)
const dialogMessage = computed(() =>
  dialogMode.value === 'approva'
    ? t('approvazioni_prezzo.approva_dialog_message')
    : t('approvazioni_prezzo.rifiuta_dialog_message')
)
const dialogTextLabel = computed(() =>
  dialogMode.value === 'approva'
    ? t('approvazioni_prezzo.approva_nota_label')
    : t('approvazioni_prezzo.rifiuta_motivazione_label')
)

// Scopo: carica una pagina della coda approver. Il scope emittente
// viene applicato lato BE (PermissionResolver.get_emittente_for_user).
async function fetchPage() {
  loading.value = true
  try {
    const res = await listCodaApprovazioni({ limit: limit.value, offset: offset.value })
    const payload = res.data?.data ?? res.data
    items.value = payload?.results ?? []
    total.value = payload?.count ?? items.value.length
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(fetchPage)

function openApprovaDialog(pratica) {
  dialogMode.value = 'approva'
  dialogPratica.value = pratica
  dialogText.value = ''
  dialogVisible.value = true
}

function openRifiutaDialog(pratica) {
  dialogMode.value = 'rifiuta'
  dialogPratica.value = pratica
  dialogText.value = ''
  dialogVisible.value = true
}

// Estrae riga_id dal meta della pratica. Contratto BE:
// `META_KEY_RIGA_PREVENTIVO_ID = "riga_preventivo_id"` in
// approvazioni_prezzo_service. Fallback `riga_id` per pratiche legacy.
// Mantenere allineato col BE: typo qui = bottone disabilitato silenziosamente.
const META_KEY_RIGA_PREVENTIVO_ID = 'riga_preventivo_id'
function rigaIdFromPratica(pratica) {
  const m = pratica?.meta ?? {}
  return m[META_KEY_RIGA_PREVENTIVO_ID] ?? m.riga_id ?? null
}

async function confirmDialog() {
  const pratica = dialogPratica.value
  const rigaId = rigaIdFromPratica(pratica)
  if (!rigaId) {
    notify.error(t('common.error'))
    return
  }
  loading.value = true
  try {
    if (dialogMode.value === 'approva') {
      await approvaPrezzoRiga(rigaId, { nota: dialogText.value || null })
      notify.success(t('approvazioni_prezzo.approvazione_inviata'))
    } else {
      await rifiutaPrezzoRiga(rigaId, { motivazione: dialogText.value || null })
      notify.success(t('approvazioni_prezzo.rifiuto_inviato'))
    }
    dialogVisible.value = false
    await fetchPage()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    loading.value = false
  }
}

function onPage(event) {
  limit.value = event.rows
  offset.value = event.first
  fetchPage()
}

// Fase 5.F1: tooltip per bottoni disabilitati. action_reason e' codice
// stabile lato BE; mappiamo qui in chiave i18n. Restituisce undefined se
// non c'e' reason (bottone abilitato): v-tooltip non viene attivato.
const ACTION_REASON_KEYS = {
  PERMESSO_MANCANTE: 'approvazioni_prezzo.reason_permesso_mancante',
  RIGA_NON_LINKATA: 'approvazioni_prezzo.reason_riga_non_linkata',
}
function actionReasonTooltip(item) {
  const code = item?.action_reason
  if (!code) return undefined
  const key = ACTION_REASON_KEYS[code]
  return key ? t(key) : code
}
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <h2>{{ t('approvazioni_prezzo.page_title') }}</h2>
      <small class="text-color-secondary">{{ t('approvazioni_prezzo.page_description') }}</small>
    </div>

    <DataTable
      :value="items"
      :loading="loading"
      :total-records="total"
      :rows="limit"
      :first="offset"
      paginator
      lazy
      :rows-per-page-options="[10, 25, 50, 100]"
      class="app-datatable"
      striped-rows
      data-key="id"
      @page="onPage"
    >
      <template #empty>
        <div class="app-empty-state">
          <i class="pi pi-check-circle" />
          <p>{{ t('approvazioni_prezzo.nessuna_richiesta') }}</p>
        </div>
      </template>

      <Column field="id" :header="t('approvazioni_prezzo.col_pratica')" style="width: 100px;" />
      <Column field="data_insert" :header="t('approvazioni_prezzo.col_data')" style="width: 160px;">
        <template #body="{ data }">
          {{ data.data_insert ? new Date(data.data_insert).toLocaleString() : '—' }}
        </template>
      </Column>
      <Column field="descrizione" :header="t('approvazioni_prezzo.col_descrizione')" />
      <Column field="priorita_codice" :header="t('approvazioni_prezzo.col_priorita')" style="width: 110px;" />
      <Column :header="t('approvazioni_prezzo.col_azioni')" class="app-col-actions" style="width: 200px;">
        <template #body="{ data }">
          <Button
            :label="t('approvazioni_prezzo.azione_approva')"
            icon="pi pi-check"
            size="small"
            severity="success"
            text
            :disabled="!data.can_approve"
            v-tooltip.top="actionReasonTooltip(data)"
            @click="openApprovaDialog(data)"
          />
          <Button
            :label="t('approvazioni_prezzo.azione_rifiuta')"
            icon="pi pi-times"
            size="small"
            severity="danger"
            text
            :disabled="!data.can_reject"
            v-tooltip.top="actionReasonTooltip(data)"
            @click="openRifiutaDialog(data)"
          />
        </template>
      </Column>
    </DataTable>

    <Dialog
      v-model:visible="dialogVisible"
      :header="dialogTitle"
      modal
      :style="{ width: '500px' }"
    >
      <p>{{ dialogMessage }}</p>
      <div class="form-field mt-1">
        <label>{{ dialogTextLabel }}</label>
        <Textarea v-model="dialogText" rows="3" auto-resize class="w-full" />
      </div>
      <template #footer>
        <Button :label="t('common.cancel')" text @click="dialogVisible = false" />
        <Button
          :label="t('common.confirm')"
          :loading="loading"
          :severity="dialogMode === 'rifiuta' ? 'danger' : 'primary'"
          @click="confirmDialog"
        />
      </template>
    </Dialog>
  </div>
</template>

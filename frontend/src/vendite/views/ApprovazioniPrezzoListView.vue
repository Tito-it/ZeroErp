<script setup>
// Scopo: Coda approver workflow approvazione prezzo.
//        Lista paginata pratiche tipo APPROVAZIONE_PREZZO in stato APERTA,
//        scope emittente derivato dal JWT operatore. Azioni di riga
//        approva/rifiuta gestite da `RowActionsMenu` (icone inline su
//        desktop + kebab popup su touch/schermi piccoli, frontend-standards
//        §"Colonna azioni di riga"). Paginatore in alto (paginatorPosition).
import { ref, onMounted, onActivated, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotify } from '../../core/composables/useNotify'
import { extractApiError } from '../../core/utils/apiError'
import { coerceJsonbToObject } from '../../core/utils/meta'
import { displayTimestamp } from '../../core/utils/date'
import { MANAGE_ICONS, PAGINATION } from '../../core/constants'
import {
  listCodaApprovazioni,
  approvaPrezzoRiga,
  rifiutaPrezzoRiga,
} from '../api/approvazioniPrezzo'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import AppDialog from '../../core/components/AppDialog.vue'
import Textarea from 'primevue/textarea'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'

const { t } = useI18n()
const notify = useNotify()

const items = ref([])
const total = ref(0)
const loading = ref(false)
const listError = ref('')
const limit = ref(PAGINATION.DEFAULT_ROWS)
const offset = ref(0)

// Dialog stato (approva | rifiuta)
const dialogVisible = ref(false)
const dialogMode = ref(null)  // 'approva' | 'rifiuta'
const dialogPratica = ref(null)
const dialogText = ref('')

const dialogTitle = computed(() =>
  dialogMode.value === 'approva'
    ? t('vendite.approvazioni_prezzo.approva_dialog_title')
    : t('vendite.approvazioni_prezzo.rifiuta_dialog_title')
)
const dialogMessage = computed(() =>
  dialogMode.value === 'approva'
    ? t('vendite.approvazioni_prezzo.approva_dialog_message')
    : t('vendite.approvazioni_prezzo.rifiuta_dialog_message')
)
const dialogTextLabel = computed(() =>
  dialogMode.value === 'approva'
    ? t('vendite.approvazioni_prezzo.approva_nota_label')
    : t('vendite.approvazioni_prezzo.rifiuta_motivazione_label')
)

// Scopo: carica una pagina della coda approver. Lo scope emittente
// viene applicato lato BE (PermissionResolver.get_emittente_for_user).
async function fetchPage() {
  loading.value = true
  listError.value = ''
  try {
    const res = await listCodaApprovazioni({ limit: limit.value, offset: offset.value })
    const payload = res.data?.data ?? res.data
    items.value = payload?.results ?? []
    total.value = payload?.count ?? items.value.length
  } catch (err) {
    listError.value = err?.response?.status === 403
      ? t('vendite.approvazioni_prezzo.accesso_negato')
      : extractApiError(err, t('common.error'))
    items.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

onMounted(fetchPage)
// La tab ContentTabs e' KeepAlive: `onMounted` non scatta al ritorno
// in foreground, quindi una nuova richiesta creata in un'altra tab
// (drawer preventivo "Richiedi approvazione") non comparirebbe finche'
// l'utente non clicca "Ricarica". `onActivated` scatta a ogni rientro
// in foreground e rinfresca la coda automaticamente. Pattern standard
// per liste cross-tab che non hanno uno store Pinia con fetchList
// (altrimenti useremmo useTabFreshness).
onActivated(fetchPage)

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

// Chiave meta della riga per sorgente (allineata ai
// `META_KEY_RIGA_*_ID` del BE `_approvazioni_prezzo_constants`). Fallback
// `riga_id` per pratiche legacy Sprint E. Typo qui = bottone disabilitato
// silenziosamente: mantenere allineato col BE.
// Coerce difensivo: meta puo' arrivare come stringa JSON.
const _RIGA_KEY_BY_SORGENTE = {
  preventivo: 'riga_preventivo_id',
  contratto: 'riga_contratto_id',
  offerta: 'riga_offerta_id',
}

// Sorgente della pratica: esposta dalla coda BE come campo top-level
// (`_capabilities_per_pratica`); fallback al meta e infine `preventivo`
// (pratiche legacy senza discriminator).
function sorgenteFromPratica(pratica) {
  const m = coerceJsonbToObject(pratica?.meta)
  return pratica?.sorgente || m.sorgente || 'preventivo'
}

function rigaIdFromPratica(pratica) {
  const m = coerceJsonbToObject(pratica?.meta)
  const key = _RIGA_KEY_BY_SORGENTE[sorgenteFromPratica(pratica)]
    || _RIGA_KEY_BY_SORGENTE.preventivo
  return m[key] ?? m.riga_id ?? null
}

async function confirmDialog() {
  const pratica = dialogPratica.value
  const rigaId = rigaIdFromPratica(pratica)
  if (!rigaId) {
    // Diagnostica esplicita: senza riga_id la chiamata API non parte e
    // l'utente vede un toast generico. Logghiamo motivo + meta in console
    // per debug, e differenziamo il messaggio dall'errore HTTP generico.
    console.warn(
      '[approvazioni-prezzo] confirmDialog abort: riga_id non trovata nel meta della pratica',
      { pratica_id: pratica?.id, meta_raw: pratica?.meta },
    )
    notify.error(t('vendite.approvazioni_prezzo.reason_riga_non_linkata'))
    return
  }
  const sorgente = sorgenteFromPratica(pratica)
  loading.value = true
  try {
    if (dialogMode.value === 'approva') {
      await approvaPrezzoRiga(rigaId, { nota: dialogText.value || null }, sorgente)
      notify.success(t('vendite.approvazioni_prezzo.approvazione_inviata'))
    } else {
      await rifiutaPrezzoRiga(rigaId, { motivazione: dialogText.value || null }, sorgente)
      notify.success(t('vendite.approvazioni_prezzo.rifiuto_inviato'))
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

// Tooltip per bottoni disabilitati. action_reason e' codice stabile lato BE;
// mappiamo qui in chiave i18n. Restituisce stringa vuota se non c'e' reason
// (bottone abilitato): RowActionsMenu non mostra tooltip vuoto.
const ACTION_REASON_KEYS = {
  PERMESSO_MANCANTE: 'vendite.approvazioni_prezzo.reason_permesso_mancante',
  RIGA_NON_LINKATA: 'vendite.approvazioni_prezzo.reason_riga_non_linkata',
}
function actionReasonTooltip(item) {
  const code = item?.action_reason
  if (!code) return ''
  const key = ACTION_REASON_KEYS[code]
  return key ? t(key) : code
}

// Azioni di riga in formato standard (frontend-standards §"Colonna azioni
// di riga"). RowActionsMenu sceglie automaticamente la resa: icone inline
// (desktop hover) o kebab popup (touch / viewport <1024px).
function buildRowActions(data) {
  const tooltip = actionReasonTooltip(data)
  return [
    {
      key: 'approva',
      label: t('vendite.approvazioni_prezzo.azione_approva'),
      icon: MANAGE_ICONS.APPROVE,
      severity: 'primary',
      disabled: !data.can_approve,
      tooltip,
      command: () => openApprovaDialog(data),
    },
    {
      key: 'rifiuta',
      label: t('vendite.approvazioni_prezzo.azione_rifiuta'),
      icon: MANAGE_ICONS.REJECT,
      severity: 'danger',
      disabled: !data.can_reject,
      tooltip,
      command: () => openRifiutaDialog(data),
    },
  ]
}

// Toolbar standard: solo "Ricarica" — niente "Nuovo" (le pratiche sono
// create dal flusso preventivo, non da questa view).
const pageActions = computed(() => [
  {
    key: 'reload',
    kind: 'utility',
    label: t('common.reload_list'),
    icon: MANAGE_ICONS.RELOAD,
    command: fetchPage,
  },
])
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h2 style="margin: 0;">{{ t('vendite.approvazioni_prezzo.page_title') }}</h2>
        <small class="text-color-secondary">{{ t('vendite.approvazioni_prezzo.page_description') }}</small>
      </div>
      <PageActionsBar :actions="pageActions" />
    </div>

    <DataTable
      :value="items"
      :loading="loading"
      :total-records="total"
      :rows="limit"
      :first="offset"
      paginator
      paginator-position="top"
      lazy
      :rows-per-page-options="[10, 25, 50, 100]"
      class="app-datatable"
      striped-rows
      scrollable
      scroll-height="flex"
      removable-sort
      data-key="id"
      @page="onPage"
    >
      <template #empty>
        <div v-if="listError" class="app-empty-state app-empty-state-error">
          <i class="pi pi-lock" />
          <p>{{ listError }}</p>
        </div>
        <div v-else class="app-empty-state">
          <i class="pi pi-check-circle" />
          <p>{{ t('vendite.approvazioni_prezzo.nessuna_richiesta') }}</p>
        </div>
      </template>

      <Column field="id" :header="t('vendite.approvazioni_prezzo.col_pratica')" sortable style="width: 100px;" />
      <Column field="data_insert" :header="t('vendite.approvazioni_prezzo.col_data')" sortable style="width: 160px;">
        <template #body="{ data }">
          {{ displayTimestamp(data.data_insert) || '—' }}
        </template>
      </Column>
      <Column field="descrizione" :header="t('vendite.approvazioni_prezzo.col_descrizione')" sortable />
      <Column field="priorita_codice" :header="t('vendite.approvazioni_prezzo.col_priorita')" sortable style="width: 110px;" />
      <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
        <template #body="{ data }">
          <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
        </template>
      </Column>
    </DataTable>

    <AppDialog
      v-model:visible="dialogVisible"
      :header="dialogTitle"
      width="md"
      :loading="loading"
      :save-label="t('common.confirm')"
      :save-severity="dialogMode === 'rifiuta' ? 'danger' : null"
      @save="confirmDialog"
    >
      <p>{{ dialogMessage }}</p>
      <div class="form-field mt-1">
        <label>{{ dialogTextLabel }}</label>
        <Textarea v-model="dialogText" rows="3" auto-resize class="w-full" />
      </div>
    </AppDialog>
  </div>
</template>

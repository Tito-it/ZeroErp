<script setup>
// Scopo: Coda approver workflow approvazione prezzo.
//        Lista paginata pratiche tipo APPROVAZIONE_PREZZO in stato APERTA,
//        scope emittente derivato dal JWT operatore. Azioni di riga
//        approva/rifiuta gestite da `RowActionsMenu` (slot #actions).
//
//        Convertita a <ListaConfigurabile> (config DB
//        `vendite.approvazioni_prezzo`, ui.lista_definizione id 36 — 7° lotto,
//        2026-08-03): personalizzazione colonne + ordinamento server-side
//        (whitelist BE PRATICHE_ORDER_COLS, inchiodatura rimossa il
//        2026-08-02) + paginatore in alto. Stato lista nello store Pinia
//        `useApprovazioniPrezzoStore` (coda di lavoro: alwaysFetch, nessun
//        floor temporale). La colonna priorità monta `priorita_descrizione`
//        (campo_sorgente del seed); il codice serve solo al colore del Tag.
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import AppDialog from '../../core/components/AppDialog.vue'
import ListaConfigStatusTag from '../../core/components/ListaConfigStatusTag.vue'
import ListaConfigurabile from '../../core/components/ListaConfigurabile.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useListaConfigurabilePage } from '../../core/composables/useListaConfigurabilePage'
import { useNotify } from '../../core/composables/useNotify'
import { MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import { extractApiError } from '../../core/utils/apiError'
import { coerceJsonbToObject } from '../../core/utils/meta'
import { prioritaPraticaSeverity } from '../../core/utils/severity'
import {
  approvaPrezzoRiga,
  rifiutaPrezzoRiga,
} from '../api/approvazioniPrezzo'
import { useApprovazioniPrezzoStore } from '../stores/approvazioniPrezzo'

const { t } = useI18n()
const notify = useNotify()
const store = useApprovazioniPrezzoStore()

// Errore di lista fail-visible (403 scope emittente o errore generico): una
// tabella vuota per errore non deve sembrare "nessuna richiesta".
const listError = ref('')

// Scopo: fetch con cattura errore (lo store propaga; qui si traduce in
//        empty-state parlante). Sostituisce anche il comando "Ricarica".
async function safeFetch() {
  listError.value = ''
  try {
    await store.fetchList()
  } catch (err) {
    listError.value = err?.response?.status === 403
      ? t('vendite.approvazioni_prezzo.accesso_negato')
      : extractApiError(err, t('common.error'))
  }
}

const {
  onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions,
} = useListaConfigurabilePage(store, { onReload: safeFetch })

// Primo caricamento al mount. La freshness al rientro tab (KeepAlive) —
// una nuova richiesta creata in un'altra tab deve comparire senza click su
// "Ricarica" — la gestisce gia' l'onActivated di useSearchTable (dentro lo
// scaffolding): refetch idempotente della pagina corrente.
onMounted(safeFetch)

// Dialog stato (approva | rifiuta)
const dialogVisible = ref(false)
const dialogMode = ref(null)  // 'approva' | 'rifiuta'
const dialogPratica = ref(null)
const dialogText = ref('')
const dialogLoading = ref(false)

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
  dialogLoading.value = true
  try {
    if (dialogMode.value === 'approva') {
      await approvaPrezzoRiga(rigaId, { nota: dialogText.value || null }, sorgente)
      notify.success(t('vendite.approvazioni_prezzo.approvazione_inviata'))
    } else {
      await rifiutaPrezzoRiga(rigaId, { motivazione: dialogText.value || null }, sorgente)
      notify.success(t('vendite.approvazioni_prezzo.rifiuto_inviato'))
    }
    dialogVisible.value = false
    await safeFetch()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    dialogLoading.value = false
  }
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
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <!-- ⛔ NIENTE `:inert` qui: questa lista non ha filtri, e il blocco
           porta il TITOLO della pagina. Inertizzare un titolo lo toglie
           anche agli screen reader proprio quando la pagina spiega perche'
           non si vede niente (cancello di perimetro emittente). -->
      <div class="app-page-toolbar-start">
        <h2 style="margin: 0;">{{ t('vendite.approvazioni_prezzo.page_title') }}</h2>
        <small class="app-text-muted">{{ t('vendite.approvazioni_prezzo.page_description') }}</small>
      </div>
      <PageActionsBar :actions="pageActions">
        <template #suffix>
          <ListaConfigStatusTag :dirty="dirty" />
        </template>
      </PageActionsBar>
    </div>

    <ListaConfigurabile
      ref="listaRef"
      codice="vendite.approvazioni_prezzo"
      data-key="id"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      @page="onPage"
      @sort="onSort"
      @config-loaded="onConfigLoaded"
    >
      <!-- data_insert non ha slot: il seed dichiara `datetime_short` e il
           formatter di serie la rende gia' cosi'. -->
      <!-- Priorita': campo_sorgente `priorita_descrizione`, colore dal codice
           (stesso pattern della lista pratiche, seed riga 257). -->
      <template #cell-priorita="{ data }">
        <Tag v-if="data.priorita_descrizione" :value="data.priorita_descrizione"
          :severity="prioritaPraticaSeverity(data.priorita_codice_interno)" />
      </template>

      <template #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>

      <template #empty>
        <div v-if="listError" class="app-empty-state app-empty-state-error">
          <i :class="STATUS_ICONS.VIETATO" />
          <p>{{ listError }}</p>
        </div>
        <div v-else-if="store.hasSearched" class="app-empty-state">
          <i :class="STATUS_ICONS.TUTTO_OK" />
          <p>{{ t('vendite.approvazioni_prezzo.nessuna_richiesta') }}</p>
        </div>
      </template>
    </ListaConfigurabile>

    <AppDialog
      v-model:visible="dialogVisible"
      :header="dialogTitle"
      width="md"
      :loading="dialogLoading"
      :save-label="t('common.confirm')"
      :save-severity="dialogMode === 'rifiuta' ? 'danger' : null"
      @save="confirmDialog"
    >
      <p>{{ dialogMessage }}</p>
      <div class="form-field mt-1">
        <label>{{ dialogTextLabel }}</label>
        <Textarea v-model="dialogText" rows="3" auto-resize />
      </div>
    </AppDialog>
  </div>
</template>

<script setup>
// Scopo: Drawer autonomo di GOVERNO della commessa (cockpit fatturazione,
//        Fase A-4 — brief-be-fe-processi-fatturazione). Complementare al
//        CommessaDrawer lineage (sola lettura): qui l'operatore ESERCITA i
//        processi — approvazione righe (A-1, per selezione o tutte), azioni
//        di stato utente da capabilities data-driven, azioni prezzo N5/N7/
//        sblocco per riga — e consulta contatori + genealogia (Passaggi).
//        Nessuna logica di dominio: testata/righe/guard vivono nel DB/BE,
//        la view invoca e rende (fail-visible sugli errori parlanti).
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Checkbox from 'primevue/checkbox'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import AppDialog from '../../core/components/AppDialog.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import LineagePassaggiPanel from '../_shared/lineage/LineagePassaggiPanel.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { mapAvailableActionsToDrawerActions } from '../../core/composables/useDrawerActions'
import { useSelezioneToggle } from '../_shared/righe/useSelezioneToggle'
import { DRAWER_WIDTH, PAGINATION } from '../../core/constants'
import { displayDate, toDateString } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { extractApiError } from '../../core/utils/apiError'
import {
  statoApprovazioneAttivitaSeverity,
  statoCommessaSeverity,
  statoEmissioneAttivitaSeverity,
} from '../../core/utils/severity'
import {
  aggiungiOnereCommessa,
  approvaCommessaAttivita,
  cambiaStatoCommessa,
  getCommessaStato,
  listCommessaAttivita,
  riallineaPrezzoAttivita,
  sbloccaPrezzoAttivita,
  variazionePrezzoAttivita,
} from '../api/commesse'
import { lookupArticoli } from '../../catalogo/api/catalogo'

const props = defineProps({
  visible: { type: Boolean, default: false },
  commessaId: { type: [Number, null], default: null },
  // Ispezione pura (feedback_drawer_readonly): nasconde ogni azione.
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'saved'])
const { t, te } = useI18n()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

// Readonly effettivo: area in LETTURA (inject) o prop di ispezione.
const parentReadonly = useInjectReadonly()
const isReadonly = computed(() => parentReadonly.value || props.readonly)
// Gate azione di processo (L2): senza permesso i pulsanti Approva spariscono.
const { isAllowed: canApprovare } = useActionPermission('approva_attivita_commessa')
// Gate unico dell'approvazione (readonly + permesso): un solo predicato per
// toolbar e colonna checkbox — mai due copie che possono divergere.
const canApprova = computed(() => !isReadonly.value && canApprovare.value)
// Gate azioni prezzo N5/N7 (specchio del `post_permission` sugli endpoint:
// senza il permesso il kebab non le propone invece di farle fallire in 403).
const { isAllowed: canPrezzo } = useActionPermission('prezzo_override_manuale')
// Gate di STATO commessa per le azioni prezzo (specchio di
// `_assert_commessa_modificabile` lato BE, data-driven su
// stati_commessa.modificabile): su CHIUSA/ANNULLATA il kebab non propone
// azioni che il BE rifiuterebbe. Fail-closed: capabilities non ancora
// caricate ⇒ nessuna azione.
const canEditRighe = computed(() => capabilities.value.can_edit_righe === true)

// ------------------------------------------------------------------ stato
const stato = ref(null)
const righe = ref([])
const righePage = ref(1)
const righePageSize = ref(PAGINATION.DEFAULT_ROWS)
const righeLoading = ref(false)
const selected = ref([])

const capabilities = computed(() => stato.value?.capabilities ?? {})

// Contatori testata (fn_get_commessa_stato): chip di sintesi del funnel.
const contatori = computed(() => {
  const s = stato.value ?? {}
  return [
    { key: 'attivita', label: t('vendite.commesse.tot_attivita'), value: s.total_attivita ?? 0, severity: 'secondary' },
    { key: 'da_approvare', label: t('vendite.commesse.tot_da_approvare'), value: s.total_non_approvate ?? 0, severity: (s.total_non_approvate ?? 0) > 0 ? 'warn' : 'secondary' },
    { key: 'approvate', label: t('vendite.commesse.tot_approvate'), value: s.total_approvate ?? 0, severity: 'success' },
    { key: 'emesse', label: t('vendite.commesse.tot_emesse'), value: s.total_emesse ?? 0, severity: 'info' },
    { key: 'da_riallineare', label: t('vendite.commesse.tot_da_riallineare'), value: s.total_prezzo_da_riallineare ?? 0, severity: (s.total_prezzo_da_riallineare ?? 0) > 0 ? 'warn' : 'secondary' },
  ]
})

// Selezione: solo le righe ancora approvabili (BOZZA + NON_EMESSA).
const righeApprovabili = computed(() =>
  righe.value.filter((r) => r.stato_approvazione === 'BOZZA' && r.stato_emissione === 'NON_EMESSA'),
)
const { isSelectable, isSelected, toggleRow, toggleAll, allSelected, anySelected } =
  useSelezioneToggle({ selected, selezionabili: righeApprovabili })

// ------------------------------------------------------------------ load
// Scopo: carica testata+capabilities; 404/fuori scope RLS → toast + chiusura.
async function loadStato() {
  const res = await loadDetailOrClose(() => getCommessaStato(props.commessaId))
  if (res == null) return false
  stato.value = res.data?.data ?? null
  return true
}

// Scopo: carica la pagina corrente delle righe (limit/offset; totale dal
//        contatore di testata total_attivita — la lista non espone il totale).
async function loadRighe() {
  righeLoading.value = true
  try {
    const res = await listCommessaAttivita(props.commessaId, {
      limit: righePageSize.value,
      offset: (righePage.value - 1) * righePageSize.value,
    })
    righe.value = res.data?.data?.rows ?? []
  } catch (err) {
    // Fail-visible: una tabella vuota per errore non deve sembrare "no righe".
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    righeLoading.value = false
  }
}

// Scopo: ricarica completa post-azione (testata + righe, selezione azzerata).
async function reloadAll() {
  selected.value = []
  if (await loadStato()) await loadRighe()
}

watch(
  () => [props.visible, props.commessaId],
  async ([visible]) => {
    if (!visible || !props.commessaId) return
    stato.value = null
    righe.value = []
    righePage.value = 1
    selected.value = []
    await reloadAll()
  },
  { immediate: true },
)

function onRighePage(event) {
  righePage.value = Math.floor(event.first / event.rows) + 1
  righePageSize.value = event.rows
  loadRighe()
}

// ------------------------------------------------------------------ approva (A-1)
// Scopo: approvazione con conferma; righeIds null = tutte (fn idempotente).
function approva(righeIds) {
  const n = righeIds ? righeIds.length : (stato.value?.total_non_approvate ?? 0)
  confirmAction({
    title: t('vendite.commesse.approva_header'),
    message: t('vendite.commesse.approva_conferma', { n }),
    onAccept: async () => {
      const res = await execute(() => approvaCommessaAttivita(props.commessaId, righeIds))
      if (res !== null) {
        notify.success(t('vendite.commesse.approva_esito', { n: res?.approvate ?? 0 }))
        await reloadAll()
        emit('saved')
      }
    },
  })
}

// ------------------------------------------------------------------ porta oneri
// Riga di puro valore sulla commessa (qta=1, causale+IVA dall'articolo-onere).
// Il presidio e' all'ingresso: senza `carica_voce_manuale` l'azione non compare
// (gate nativo di DrawerActionsBar via `action`), e il BE la rifiuta comunque.
const onereDialog = ref(false)
const onereArticoli = ref([])
const onereArticoliLoading = ref(false)
const onereForm = ref({
  articoloOnereId: null,
  importo: null,
  tipoDocFiscaleId: null,
  motivo: '',
  dataAttivita: null,
})

// Scopo: carica gli articoli-onere del catalogo (uno per causale: pochi, si
//        presentano come tendina e non come autocomplete).
async function loadArticoliOnere() {
  if (onereArticoli.value.length) return
  onereArticoliLoading.value = true
  try {
    const res = await lookupArticoli({ solo_oneri: true, limit: 50 })
    onereArticoli.value = res.data?.data?.results ?? []
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    onereArticoliLoading.value = false
  }
}

// Scopo: apre il dialog azzerando il form (mai residui del giro precedente).
async function apriOnere() {
  onereForm.value = {
    articoloOnereId: null,
    importo: null,
    tipoDocFiscaleId: null,
    motivo: '',
    dataAttivita: null,
  }
  onereDialog.value = true
  await loadArticoliOnere()
}

const onereValido = computed(() =>
  !!onereForm.value.articoloOnereId
  && onereForm.value.importo != null
  && onereForm.value.importo > 0
  && !!onereForm.value.tipoDocFiscaleId)

// Scopo: carica l'onere; la riga nasce APPROVATA e compare subito in lista.
async function salvaOnere() {
  const f = onereForm.value
  const res = await execute(() => aggiungiOnereCommessa(props.commessaId, {
    articoloOnereId: f.articoloOnereId,
    importo: f.importo,
    tipoDocFiscaleId: f.tipoDocFiscaleId,
    motivo: f.motivo,
    dataAttivita: f.dataAttivita ? toDateString(f.dataAttivita) : null,
  }))
  if (res !== null) {
    onereDialog.value = false
    notify.success(t('vendite.commesse.onere_esito'))
    await reloadAll()
    emit('saved')
  }
}

// ------------------------------------------------------------------ stato (capabilities)
// Azioni di stato utente dal blob capabilities (transizioni manuali).
const stateActions = computed(() => mapAvailableActionsToDrawerActions({
  availableActions: capabilities.value.available_actions ?? [],
  t,
  te,
  readonly: isReadonly,
  onAction: (action) => {
    confirmAction({
      title: t('vendite.commesse.stato_header'),
      message: t('vendite.commesse.stato_conferma', { stato: t(action.label_key) }),
      onAccept: async () => {
        const res = await execute(() => cambiaStatoCommessa(props.commessaId, action.target_state))
        if (res !== null) {
          await reloadAll()
          emit('saved')
        }
      },
    })
  },
}))

// ------------------------------------------------------------------ prezzi (N5/N7)
const variazioneDialog = ref(false)
const variazioneRiga = ref(null)
const variazionePrezzo = ref(null)
const variazioneMotivo = ref('')

// Sblocco (N7-sblocco): il BE esige motivo obbligatorio, quindi dialog (non
// più solo confirm) — stesso pattern della variazione.
const sbloccaDialog = ref(false)
const sbloccaRiga = ref(null)
const sbloccaMotivo = ref('')

// Scopo: kebab riga — azioni prezzo condizionate dai flag riga; il guard vero
//        (riga fatturata, commessa non modificabile) resta al BE (fail-visible).
function buildRowActions(row) {
  if (isReadonly.value || !canPrezzo.value || !canEditRighe.value) return []
  return [
    {
      key: 'riallinea',
      label: t('vendite.commesse.azione_riallinea'),
      icon: 'pi pi-sync',
      visible: !row.prezzo_bloccato,
      command: () => riallinea(row, false),
    },
    {
      // DEC-3: la variazione eccezionale è vietata su prezzo bloccato — prima
      // si sblocca (con motivo). Specchio del guard BE E-BE-1.
      key: 'variazione',
      label: t('vendite.commesse.azione_variazione'),
      icon: 'pi pi-pencil',
      visible: !row.prezzo_bloccato,
      command: () => {
        variazioneRiga.value = row
        variazionePrezzo.value = null
        variazioneMotivo.value = ''
        variazioneDialog.value = true
      },
    },
    {
      // Icona-azione (chiave) distinta dai lucchetti-STATO della colonna prezzo
      // (pi-lock chiuso = bloccato): il bottone inline icon-only non deve
      // leggersi come uno stato «aperto».
      key: 'sblocca',
      label: t('vendite.commesse.azione_sblocca'),
      icon: 'pi pi-key',
      visible: row.prezzo_bloccato === true,
      command: () => sblocca(row),
    },
  ]
}

// Scopo: N5 — al primo giro senza conferma; se il BE segnala versione listino
//        cambiata (richiede_conferma) chiede conferma esplicita e ripete.
async function riallinea(row, conferma) {
  const res = await execute(() =>
    riallineaPrezzoAttivita(props.commessaId, row.id, { confermaVersioneDiversa: conferma }))
  if (res === null) return
  if (res.richiede_conferma && !conferma) {
    confirmAction({
      title: t('vendite.commesse.riallinea_header'),
      message: t('vendite.commesse.riallinea_versione_diversa'),
      onAccept: () => riallinea(row, true),
    })
    return
  }
  notify.success(t('vendite.commesse.riallinea_esito'))
  await reloadAll()
  emit('saved')
}

// Scopo: N7 — salva variazione eccezionale (prezzo+motivo obbligatori).
async function salvaVariazione() {
  const res = await execute(() =>
    variazionePrezzoAttivita(props.commessaId, variazioneRiga.value.id, {
      prezzo: variazionePrezzo.value,
      motivo: variazioneMotivo.value,
    }))
  if (res !== null) {
    variazioneDialog.value = false
    notify.success(t('vendite.commesse.variazione_esito'))
    await reloadAll()
    emit('saved')
  }
}

const variazioneValida = computed(() =>
  variazionePrezzo.value !== null && String(variazioneMotivo.value ?? '').trim().length > 0)

// Scopo: N7-sblocco — apre il dialog motivo (motivo obbligatorio lato BE).
function sblocca(row) {
  sbloccaRiga.value = row
  sbloccaMotivo.value = ''
  sbloccaDialog.value = true
}

const sbloccaValido = computed(() =>
  String(sbloccaMotivo.value ?? '').trim().length > 0)

// Scopo: N7-sblocco — rimuove il blocco e ricalcola dal resolver (motivo obbligatorio).
async function salvaSblocco() {
  const res = await execute(() =>
    sbloccaPrezzoAttivita(props.commessaId, sbloccaRiga.value.id, { motivo: sbloccaMotivo.value }))
  if (res !== null) {
    sbloccaDialog.value = false
    notify.success(t('vendite.commesse.sblocca_esito'))
    await reloadAll()
    emit('saved')
  }
}

const selectedIds = computed(() => selected.value.map((r) => r.id))

// Barra azioni del drawer: porta oneri + transizioni di stato. `action` fa da
// gate permesso e `hideWhenReadonly` da gate ispezione (logica in DrawerActionsBar,
// che applica anche `app-escape` — i pannelli-azione vivono in contenuto readonly).
const drawerActions = computed(() => [
  {
    key: 'aggiungi-onere',
    kind: 'primary',
    label: t('vendite.commesse.onere_azione'),
    icon: 'pi pi-plus-circle',
    tooltip: t('vendite.commesse.onere_tooltip'),
    action: 'carica_voce_manuale',
    hideWhenReadonly: true,
    command: apriOnere,
  },
  ...stateActions.value,
])
</script>

<template>
  <Drawer
    :visible="visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :dismissable="true"
    @update:visible="(v) => { if (!v) onClose() }"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle :title="t('vendite.commesse.gestione_titolo')" icon="pi pi-briefcase" />
    </template>

    <div class="app-drawer-content">
      <template v-if="contentReady">
        <DrawerEntityHeader v-if="stato">
          <Tag :value="`#${stato.commessa_id}`" severity="secondary" />
          <span v-if="stato.policy_fatturazione" class="text-color-secondary">
            {{ stato.policy_fatturazione }}
          </span>
          <template #status>
            <Tag
              v-if="stato.stato_commessa"
              :value="stato.stato_commessa"
              :severity="statoCommessaSeverity(stato.stato_codice_interno)"
            />
          </template>
        </DrawerEntityHeader>

        <!-- Porta oneri + azioni di stato utente (capabilities data-driven). -->
        <DrawerActionsBar v-if="drawerActions.length" :actions="drawerActions" :disabled="loading" />

        <!-- Contatori funnel testata. -->
        <div v-if="stato" class="app-commessa-contatori">
          <span v-for="c in contatori" :key="c.key" class="app-commessa-contatore">
            <Tag :value="String(c.value)" :severity="c.severity" />
            <small>{{ c.label }}</small>
          </span>
        </div>

        <!-- Righe attivita' + approvazione (A-1). -->
        <div class="app-page-toolbar" style="margin-top: 1rem;">
          <h4 style="margin: 0;">{{ t('vendite.commesse.righe_titolo') }}</h4>
          <div v-if="canApprova" style="display: flex; gap: 0.5rem;">
            <Button
              :label="t('vendite.commesse.approva_selezionate', { n: selectedIds.length })"
              icon="pi pi-check"
              size="small"
              :disabled="loading || selectedIds.length === 0"
              @click="approva(selectedIds)"
            />
            <Button
              :label="t('vendite.commesse.approva_tutte')"
              icon="pi pi-check-circle"
              size="small"
              outlined
              :disabled="loading || (stato?.total_non_approvate ?? 0) === 0"
              @click="approva(null)"
            />
          </div>
        </div>

        <DataTable
          :value="righe"
          :loading="righeLoading"
          :total-records="stato?.total_attivita ?? 0"
          :rows="righePageSize"
          :first="(righePage - 1) * righePageSize"
          paginator
          paginator-position="top"
          lazy
          :rows-per-page-options="PAGINATION.ROWS_OPTIONS"
          class="app-datatable app-datatable--inner"
          striped-rows
          size="small"
          data-key="id"
          @page="onRighePage"
        >
          <!-- Checkbox custom (pattern useSelezioneToggle): solo approvabili. -->
          <Column v-if="canApprova && righeApprovabili.length" headerStyle="width: 3rem">
            <template #header>
              <Checkbox
                :model-value="allSelected"
                binary
                :indeterminate="anySelected"
                @update:model-value="toggleAll"
              />
            </template>
            <template #body="{ data }">
              <Checkbox
                :model-value="isSelected(data)"
                binary
                :disabled="!isSelectable(data)"
                @update:model-value="toggleRow(data)"
              />
            </template>
          </Column>
          <Column field="data_attivita" :header="t('vendite.commesse.col_data')" style="width: 100px;">
            <template #body="{ data }">
              {{ data.data_attivita ? displayDate(data.data_attivita) : '—' }}
            </template>
          </Column>
          <Column field="competenza_mese" :header="t('vendite.commesse.col_competenza')" style="width: 100px;">
            <template #body="{ data }">
              {{ data.competenza_mese ? displayDate(data.competenza_mese) : '—' }}
            </template>
          </Column>
          <Column field="segment_key" :header="t('vendite.commesse.col_segmento')">
            <template #body="{ data }">
              <span class="app-commessa-segment" :title="data.segment_key">{{ data.segment_key }}</span>
            </template>
          </Column>
          <Column field="quantita" :header="t('vendite.commesse.col_quantita')" style="width: 80px;">
            <template #body="{ data }">
              {{ data.quantita ?? '—' }}
            </template>
          </Column>
          <Column field="prezzo_snapshot" :header="t('vendite.commesse.col_prezzo')" style="width: 110px;">
            <template #body="{ data }">
              <span>
                {{ data.prezzo_snapshot != null ? formatCurrency(Number(data.prezzo_snapshot)) : '—' }}
                <i
                  v-if="data.prezzo_bloccato"
                  class="pi pi-lock"
                  v-tooltip.bottom="t('vendite.commesse.prezzo_bloccato')"
                />
                <i
                  v-if="data.prezzo_da_riallineare"
                  class="pi pi-exclamation-triangle app-dash-ritardo"
                  v-tooltip.bottom="t('vendite.commesse.prezzo_da_riallineare')"
                />
              </span>
            </template>
          </Column>
          <Column field="stato_approvazione" :header="t('vendite.commesse.col_approvazione')" style="width: 100px;">
            <template #body="{ data }">
              <Tag :value="data.stato_approvazione" :severity="statoApprovazioneAttivitaSeverity(data.stato_approvazione)" />
            </template>
          </Column>
          <Column field="stato_emissione" :header="t('vendite.commesse.col_emissione')" style="width: 100px;">
            <template #body="{ data }">
              <Tag :value="data.stato_emissione" :severity="statoEmissioneAttivitaSeverity(data.stato_emissione)" />
            </template>
          </Column>
          <Column v-if="!isReadonly" :header="t('vendite.commesse.col_azioni')" class="app-col-actions" :exportable="false">
            <template #body="{ data }">
              <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
            </template>
          </Column>
        </DataTable>

        <!-- Genealogia (riuso pannello lineage, chiuso di default). -->
        <LineagePassaggiPanel
          v-if="commessaId"
          base-path="/vendite/commesse"
          :doc-id="commessaId"
        />
      </template>

      <FormFooter close-only @cancel="onClose" />
    </div>

    <!-- Dialog N7 — variazione prezzo eccezionale (prezzo + motivo). -->
    <AppDialog
      v-model:visible="variazioneDialog"
      :header="t('vendite.commesse.variazione_header')"
      width="sm"
      :loading="loading"
      :save-disabled="!variazioneValida"
      @save="salvaVariazione"
      @cancel="variazioneDialog = false"
    >
      <div class="form-field">
        <label>{{ t('vendite.commesse.variazione_prezzo') }}</label>
        <InputNumber
          v-model="variazionePrezzo"
          mode="decimal"
          :min-fraction-digits="2"
          :max-fraction-digits="10"
          fluid
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.commesse.variazione_motivo') }}</label>
        <Textarea v-model="variazioneMotivo" rows="3" fluid />
      </div>
    </AppDialog>

    <!-- Dialog N7-sblocco — motivo obbligatorio (il BE lo esige). -->
    <AppDialog
      v-model:visible="sbloccaDialog"
      :header="t('vendite.commesse.sblocca_header')"
      width="sm"
      :loading="loading"
      :save-disabled="!sbloccaValido"
      :save-label="t('vendite.commesse.sblocca_salva')"
      @save="salvaSblocco"
      @cancel="sbloccaDialog = false"
    >
      <p class="text-color-secondary" style="margin-top: 0;">
        {{ t('vendite.commesse.sblocca_conferma') }}
      </p>
      <div class="form-field">
        <label>{{ t('vendite.commesse.sblocca_motivo') }}</label>
        <Textarea v-model="sbloccaMotivo" rows="3" fluid />
      </div>
    </AppDialog>

    <!-- Dialog porta oneri — riga di valore (qta=1) sulla commessa. -->
    <AppDialog
      v-model:visible="onereDialog"
      :header="t('vendite.commesse.onere_header')"
      width="md"
      :loading="loading"
      :save-disabled="!onereValido"
      :save-label="t('vendite.commesse.onere_salva')"
      @save="salvaOnere"
      @cancel="onereDialog = false"
    >
      <div class="form-field">
        <label>{{ t('vendite.commesse.onere_articolo') }}</label>
        <!-- Voce ricca: l'IVA e' propria di ogni onere (la penale e' fuori
             campo art.15), va vista al momento della scelta. -->
        <Select
          v-model="onereForm.articoloOnereId"
          :options="onereArticoli"
          option-label="descrizione"
          option-value="id"
          :loading="onereArticoliLoading"
          :placeholder="t('vendite.commesse.onere_articolo_placeholder')"
          fluid
        >
          <template #option="{ option }">
            <div class="app-lookup-option">
              <div class="app-lookup-option__primary">
                {{ option.descrizione }}
                <Tag v-if="option.iva_codice" :value="option.iva_codice" severity="secondary" />
              </div>
              <div class="app-lookup-option__secondary">{{ option.codice }}</div>
              <div class="app-lookup-option__meta">
                <span v-if="option.causale_onere_descrizione">
                  {{ option.causale_onere_descrizione }}
                </span>
                <span v-if="option.iva_descrizione">{{ option.iva_descrizione }}</span>
              </div>
            </div>
          </template>
        </Select>
      </div>
      <div class="form-field">
        <label>{{ t('vendite.commesse.onere_importo') }}</label>
        <InputNumber
          v-model="onereForm.importo"
          mode="decimal"
          :min="0"
          :min-fraction-digits="2"
          :max-fraction-digits="10"
          fluid
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.commesse.onere_tipo_doc') }}</label>
        <LookupSelect
          v-model="onereForm.tipoDocFiscaleId"
          rel="config.tipi_doc_fiscale"
          :placeholder="t('vendite.commesse.onere_tipo_doc_placeholder')"
          show-code
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.commesse.onere_data') }}</label>
        <DatePicker
          v-model="onereForm.dataAttivita"
          date-format="dd/mm/yy"
          show-icon
          show-button-bar
          fluid
        />
      </div>
      <div class="form-field">
        <label>{{ t('vendite.commesse.onere_motivo') }}</label>
        <Textarea v-model="onereForm.motivo" rows="2" fluid />
      </div>
    </AppDialog>
  </Drawer>
</template>

<style scoped>
.app-commessa-contatori {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-top: 0.75rem;
}
.app-commessa-contatore {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.15rem;
}
.app-commessa-segment {
  display: inline-block;
  max-width: 10rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

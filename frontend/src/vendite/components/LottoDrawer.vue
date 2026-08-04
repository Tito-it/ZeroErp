<script setup>
// Scopo: Drawer diagnostico del lotto di fatturazione (cockpit Fase B, B-3/B-4).
//        Il posto dove si capisce in pochi secondi se un lotto è sano o bloccato
//        e lo si sblocca: testata + step corrente, tab fatture / task-run
//        (tentativi ed esiti) / segnalazioni, e le azioni di governo — avanza
//        step, rerun su ERRORE, riporta a bozza (demolizione pre-fiscale),
//        reset singola fattura DRAFT. Nessuna logica: la macchina step/gate/
//        rollback vive nel motore DB/BE (fail-visible sugli errori parlanti).
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Drawer from 'primevue/drawer'
import Tag from 'primevue/tag'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Message from 'primevue/message'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import PdfDocumentiSorgenteDialog from '../../documenti/components/PdfDocumentiSorgenteDialog.vue'
import FatturaDrawer from './FatturaDrawer.vue'
import { useDocumentiPerSorgenteStore } from '../../documenti/stores/documentiPerSorgente'
import { SORGENTE_CODES } from '../../documenti/constants'
import { downloadBlob } from '../../core/utils/download'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { mapAvailableActionsToDrawerActions } from '../../core/composables/useDrawerActions'
import {
  useLottoAzioni,
  LOTTO_AZIONE_PERMESSO,
  LOTTO_AZIONE_PIPELINE_UI,
} from '../composables/useLottoAzioni'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { displayDate, displayTimestamp } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { extractApiError } from '../../core/utils/apiError'
import {
  statoEsecuzioneFatturaSeverity,
  statoLottoSeverity,
  statoTaskRunSeverity,
} from '../../core/utils/severity'
import {
  getLotto,
  listLottoFatture,
  listLottoTaskRuns,
  getLottoSegnalazioni,
  eliminaFatturaDaLotto,
} from '../api/lotti'

const props = defineProps({
  visible: { type: Boolean, default: false },
  lottoId: { type: [Number, null], default: null },
  // Ispezione pura (feedback_drawer_readonly): nasconde ogni azione di governo.
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'changed'])
// `te` serve a `mapAvailableActionsToDrawerActions`: chiave i18n mancante →
// mostra il codice macchina invece del path (fail-visible).
const { t, te } = useI18n()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const docStore = useDocumentiPerSorgenteStore()

// Readonly effettivo: area in LETTURA (inject dal provider della view) o prop
// di ispezione. In readonly le azioni di governo spariscono (il BE resta il
// guard vero, questo e' UX coerente col pattern protect).
const parentReadonly = useInjectReadonly()
const isReadonly = computed(() => parentReadonly.value || props.readonly)

// Gate azioni di riga fattura. I permessi delle azioni di GOVERNO del lotto non
// si leggono più qui: viaggiano come `action` sulle entry della barra e li
// filtra `DrawerActionsBar` (`auth.isActionAllowed`), un solo meccanismo per
// tutti i drawer.
const { isAllowed: canResetFattura } = useActionPermission('reset_lotto_fattura_draft')

const lotto = ref(null)
const fatture = ref([])
const taskRuns = ref([])
const segnalazioni = ref(null)
const tabLoading = ref(false)
// Dialog archivio documenti fattura (C-8). Dichiarati QUI, PRIMA del watch
// immediate che li resetta: una ref toccata da un watch immediate dichiarata
// dopo va in TDZ silenziosa (memoria feedback_vue_watch_immediate_tdz).
const pdfDialogVisible = ref(false)
const pdfFatturaId = ref(null)
// Drawer di consultazione fattura: stessa regola di dichiarazione anticipata
// (il watch immediate sotto lo resetta).
const fatturaDrawerVisible = ref(false)
const fatturaDrawerId = ref(null)

// Capability dal BE (`script.fn_available_actions_lotto`, 2026-08-04): quali
// verbi di governo esistono su QUESTO lotto, quali sono abilitati e — se non lo
// sono — perché. Le condizioni fiscali (DRAFT / EMESSA / DEFINITIVA) NON si
// scrivono più qui: erano cinque `computed` che ricopiavano in JavaScript
// precondizioni scritte in PL/pgSQL, e avevano già prodotto un pulsante-vicolo
// cieco («Annulla lotto» visibile da EMESSA, trovato in-app il 2026-07-31).
// Ora la sorgente è una sola: le stesse `fn_check_*` da cui le funzioni di
// mutazione sollevano. Resta al frontend il solo gate di pipeline (avanza /
// rilancia), che il DB non espone di proposito: vive in `useLottoAzioni`,
// condiviso col kebab della lista.
const availableActions = computed(() => lotto.value?.available_actions ?? [])

// Segnalazioni bloccanti: mostra il banner se il lotto ha criticità.
const haSegnalazioniCritiche = computed(() => (segnalazioni.value?.critical_count ?? 0) > 0)

// ------------------------------------------------------------------ load
async function loadLotto() {
  const res = await loadDetailOrClose(() => getLotto(props.lottoId))
  if (res == null) return false
  lotto.value = res.data?.data ?? null
  return true
}

async function loadFatture() {
  const res = await listLottoFatture(props.lottoId, { page: 1, page_size: 100 })
  fatture.value = res.data?.data?.results ?? []
}

async function loadTabs() {
  tabLoading.value = true
  try {
    const [tRes, sRes] = await Promise.all([
      listLottoTaskRuns(props.lottoId, { limit: 100 }),
      getLottoSegnalazioni(props.lottoId),
      loadFatture(),
    ])
    taskRuns.value = tRes.data?.data?.task_runs ?? []
    segnalazioni.value = sRes.data?.data ?? null
  } catch (err) {
    // Fail-visible: un tab vuoto per errore non deve sembrare "nessun dato".
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    tabLoading.value = false
  }
}

async function reloadAll() {
  if (await loadLotto()) await loadTabs()
}

// Scopo: reload mirato post reset-fattura — cambiano solo testata (step/stato)
//        e lista fatture; task-run e segnalazioni restano com'erano.
async function reloadFatture() {
  tabLoading.value = true
  try {
    if (await loadLotto()) await loadFatture()
  } catch (err) {
    notify.error(extractApiError(err, t('common.error')))
  } finally {
    tabLoading.value = false
  }
}

watch(
  () => [props.visible, props.lottoId],
  async ([visible]) => {
    // Il dialog documenti e' teleported (fuori dal DOM del drawer): senza
    // chiusura esplicita resterebbe aperto orfano alla chiusura del drawer.
    // Stessa ragione per il drawer fattura, anch'esso teleported.
    pdfDialogVisible.value = false
    fatturaDrawerVisible.value = false
    if (!visible || !props.lottoId) return
    lotto.value = null
    fatture.value = []
    taskRuns.value = []
    segnalazioni.value = null
    await reloadAll()
  },
  { immediate: true },
)

// ------------------------------------------------- barra azioni di governo
// Le azioni (conferme, chiamate, toast) vivono nel composable condiviso col
// kebab della lista lotti: una sola sede — estratto alla seconda occorrenza
// (regola del 2, ok Tid 2026-08-04). Qui resta solo il refresh post-azione,
// che è del drawer.
const { esegui: eseguiAzione, verbiPipeline, loading: azioniLoading } = useLottoAzioni({
  onDone: async () => {
    await reloadAll()
    emit('changed')
  },
})

// Scopo: azioni del drawer — quelle di stato dal blob capability, più i due
//        verbi di pipeline che il DB deliberatamente NON espone (avanza e
//        rilancia): il loro gate è fatto di step successivo, criticità attive e
//        distinzione avanza/rilancio dello stesso step, e vive per intero nel
//        runner Python. Finché sta lì, resta gate del frontend — farne scendere
//        solo un pezzo creerebbe la seconda copia della regola che questo
//        lavoro elimina (risposta DB 2026-08-04 §5).
const drawerActions = computed(() => {
  const azioni = mapAvailableActionsToDrawerActions({
    availableActions: availableActions.value,
    t,
    te,
    readonly: isReadonly,
    onAction: (action) => eseguiAzione(props.lottoId, action.key),
  }).map((a) => ({
    ...a,
    ...(LOTTO_AZIONE_PERMESSO[a.key] ? { action: LOTTO_AZIONE_PERMESSO[a.key] } : {}),
    // La numerazione è uno STEP di pipeline: con criticità attive il runner la
    // rifiuta (`blocks_next_step`). Il DB non conosce le segnalazioni, quindi
    // questo disabilitato lo aggiunge chi le ha: noi. Non sovrascrive un
    // `disabled` già vero arrivato dalle `fn_check_*` (né il suo tooltip,
    // che spiega il motivo del DB).
    ...(a.key === 'numera' && haSegnalazioniCritiche.value && !a.disabled
      ? { disabled: true, tooltip: t('vendite.lotti.blocca_step') }
      : {}),
  }))

  if (isReadonly.value) return azioni

  // I due verbi di pipeline, con la stessa regola che usa il kebab della lista
  // (sede unica nel composable). Il rilancio dello stesso step è ammesso ANCHE
  // con criticità attive (D-Q p.1): è la via d'uscita — si corregge il dato a
  // monte e si ri-esegue. L'avanzamento no, quello lo blocca il runner.
  for (const key of verbiPipeline(lotto.value)) {
    const ui = LOTTO_AZIONE_PIPELINE_UI[key]
    const bloccato = key === 'avanza_step' && haSegnalazioniCritiche.value
    azioni.unshift({
      key,
      kind: 'state',
      label: t(ui.label_key),
      icon: ui.icon,
      severity: ui.severity,
      action: LOTTO_AZIONE_PERMESSO[key],
      disabled: bloccato,
      tooltip: bloccato ? t('vendite.lotti.blocca_step') : undefined,
      command: () => eseguiAzione(props.lottoId, key),
    })
  }
  return azioni
})

// Scopo: elimina una singola fattura dal lotto (lotto e fattura pre-fiscali).
//        La conferma dice esplicitamente che il documento viene CANCELLATO:
//        non esiste un archivio di fatture «estratte» (RD-7).
function eliminaFattura(row) {
  confirmAction({
    title: t('vendite.lotti.reset_fattura_header'),
    message: t('vendite.lotti.reset_fattura_conferma'),
    danger: true,
    acceptLabel: t('vendite.lotti.azione_reset_fattura'),
    onAccept: async () => {
      const res = await execute(() => eliminaFatturaDaLotto(props.lottoId, row.fattura_id))
      if (res !== null) {
        notify.success(t('vendite.lotti.reset_fattura_esito', {
          attivita: res?.updated_attivita ?? 0,
          riemesse: res?.riemesse_attivita ?? 0,
        }))
        await reloadFatture()
        emit('changed')
      }
    },
  })
}

// ---------------------------------------------------------------- stampa (C-8)
// Stampa/ristampa di una fattura via il motore documentale (sorgente FATTURA).
// La stampa è una LETTURA (I-4: legge le tabelle e renderizza, non edita):
// disponibile anche in sola lettura, a differenza delle azioni di governo.

// Scopo: anteprima PDF sincrona on-the-fly (nessun record, download immediato).
//        Render della fattura corrente (context builder FATTURA → template).
async function anteprimaFattura(row) {
  docStore.setSorgente(SORGENTE_CODES.FATTURA, row.fattura_id)
  const result = await execute(() => docStore.anteprima({}))
  if (result) downloadBlob(result.blob, result.fileName)
}

// Scopo: apre il dialog archivio documenti generati della fattura
//        (lista + download). Le ref del dialog sono dichiarate in testa
//        (prima del watch immediate che le resetta).
function apriDocumentiFattura(row) {
  pdfFatturaId.value = row.fattura_id
  pdfDialogVisible.value = true
}

// Scopo: apre il drawer di consultazione della fattura (documento a video).
//        Il drawer si sovrappone a questo: e' consultazione pura e alla
//        chiusura si torna al lotto senza ricaricare nulla.
function apriFattura(row) {
  fatturaDrawerId.value = row.fattura_id
  fatturaDrawerVisible.value = true
}

// Azioni di riga fattura: consultazione e stampa (anteprima + archivio) sempre
// disponibili (lettura); l'eliminazione dal lotto solo fuori sola-lettura, col
// permesso, e dentro il perimetro pre-fiscale. I gate usano il codice stabile
// (codice_interno), MAI la descrizione display.
function buildFatturaActions(row) {
  const actions = [
    {
      // Apre il documento a video (testata + righe + riepilogo IVA): fino a
      // ieri la fattura si poteva solo scaricare in PDF per sapere cosa c'e'
      // dentro. Prima voce del kebab perche' e' la consultazione, non
      // un'azione — le due voci di stampa restano sotto.
      key: 'apri',
      label: t('vendite.lotti.azione_apri_fattura'),
      icon: MANAGE_ICONS.INSPECT,
      command: () => apriFattura(row),
    },
    {
      key: 'anteprima',
      label: t('vendite.lotti.azione_anteprima_fattura'),
      icon: MANAGE_ICONS.PDF,
      command: () => anteprimaFattura(row),
    },
    {
      key: 'documenti',
      label: t('vendite.lotti.azione_documenti_fattura'),
      icon: MANAGE_ICONS.ARCHIVE,
      command: () => apriDocumentiFattura(row),
    },
  ]
  // Perimetro pre-fiscale, cioe' non numerato: DRAFT **o EMESSA**. Vale per la
  // fattura (allargato dal DB il 2026-08-02, D-T: restringere a DRAFT
  // nasconderebbe l'azione proprio nel caso che la motiva — la fattura critica
  // rimasta indietro) **e per il lotto** (slice 6-B del 2026-08-04: il DB ha un
  // codice dedicato, `E_LOTTO_NON_PRE_FISCALE`, quindi il caso lo considera
  // raggiungibile). Le due condizioni sono separate a DB e vanno lette
  // entrambe: guardare solo la riga rimetterebbe in scena il
  // pulsante-vicolo-cieco che questo cantiere ha appena tolto altrove.
  // Il presidio vero resta fiscale e sta a DB — qui si evita soltanto di
  // proporre un'azione destinata a fallire.
  const PRE_FISCALI = ['DRAFT', 'EMESSA']
  const fatturaPreFiscale = PRE_FISCALI.includes(row.stato_doc_fiscale_codice)
  const lottoPreFiscale = PRE_FISCALI.includes(lotto.value?.stato_doc_fiscale_codice)
  if (!isReadonly.value && canResetFattura.value && fatturaPreFiscale && lottoPreFiscale) {
    actions.push({
      key: 'elimina',
      label: t('vendite.lotti.azione_reset_fattura'),
      // Distruttiva e irreversibile (RD-7: il contenuto non e' recuperabile,
      // `vendite.fatture` non e' storicizzata) → cestino + rosso, come impone
      // lo standard per le azioni di riga distruttive. L'icona «undo» di prima
      // raccontava il verbo vecchio («riporta a bozza»), non questo.
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      command: () => eliminaFattura(row),
    })
  }
  return actions
}

function fatturaNumero(row) {
  if (!row.numero) return '—'
  const serie = row.serie ? `${row.serie} ` : ''
  return `${serie}${row.numero}`
}
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
      <DrawerTitle :title="t('vendite.lotti.drawer_titolo')" icon="pi pi-server" />
    </template>

    <div class="app-drawer-content">
      <template v-if="contentReady && lotto">
        <DrawerEntityHeader>
          <Tag :value="lotto.codice" severity="secondary" />
          <span class="text-color-secondary">{{ lotto.tipo_lotto }}</span>
          <span v-if="lotto.competenza_mese" class="text-color-secondary">
            {{ displayDate(lotto.competenza_mese) }}
          </span>
          <template #status>
            <Tag :value="lotto.stato_lotto" :severity="statoLottoSeverity(lotto.stato_lotto)" />
          </template>
        </DrawerEntityHeader>

        <!-- Step corrente (stato doc fiscale del lotto). -->
        <div class="app-lotto-step">
          <span class="text-color-secondary">{{ t('vendite.lotti.step_corrente') }}:</span>
          <Tag :value="lotto.stato_doc_fiscale_descrizione ?? '—'" severity="info" />
          <span v-if="lotto.stato_operativo" class="text-color-secondary">· {{ lotto.stato_operativo }}</span>
        </div>

        <!-- Banner segnalazioni critiche (blocca l'avanzamento). -->
        <Message v-if="haSegnalazioniCritiche" severity="error" :closable="false" class="app-mt-1">
          {{ t('vendite.lotti.segnalazioni_bloccanti', { n: segnalazioni.critical_count }) }}
        </Message>

        <!-- Azioni di governo del lotto. Quali esistono, quali sono abilitate e
             perché no lo dice il BE (`available_actions`): qui si rende e si
             chiama. In sola lettura la barra resta vuota. -->
        <DrawerActionsBar :actions="drawerActions" :disabled="loading || azioniLoading" />

        <Tabs value="fatture" class="app-mt-1">
          <TabList>
            <Tab value="fatture">{{ t('vendite.lotti.tab_fatture') }} ({{ fatture.length }})</Tab>
            <Tab value="task">{{ t('vendite.lotti.tab_task') }} ({{ taskRuns.length }})</Tab>
            <Tab value="segnalazioni">{{ t('vendite.lotti.tab_segnalazioni') }}</Tab>
          </TabList>
          <TabPanels>
            <!-- Fatture del lotto. -->
            <TabPanel value="fatture">
              <DataTable
                :value="fatture"
                :loading="tabLoading"
                class="app-datatable app-datatable--inner"
                striped-rows
                size="small"
                data-key="fattura_id"
              >
                <Column field="numero" :header="t('vendite.lotti.col_numero')" style="width: 110px;">
                  <template #body="{ data }">{{ fatturaNumero(data) }}</template>
                </Column>
                <Column field="ragione_sociale_completa" :header="t('vendite.lotti.col_cliente')">
                  <template #body="{ data }">{{ data.ragione_sociale_completa ?? '—' }}</template>
                </Column>
                <Column field="stato_doc_fiscale_descrizione" :header="t('vendite.lotti.col_stato_doc')" style="width: 130px;">
                  <template #body="{ data }">
                    <Tag :value="data.stato_doc_fiscale_descrizione ?? '—'" severity="info" />
                  </template>
                </Column>
                <Column field="stato_esecuzione" :header="t('vendite.lotti.col_esecuzione')" style="width: 120px;">
                  <template #body="{ data }">
                    <Tag :value="data.stato_esecuzione" :severity="statoEsecuzioneFatturaSeverity(data.stato_esecuzione)" />
                  </template>
                </Column>
                <Column field="totale_doc" :header="t('vendite.lotti.col_totale')" style="width: 110px;">
                  <template #body="{ data }">
                    {{ data.totale_doc != null ? formatCurrency(Number(data.totale_doc)) : '—' }}
                  </template>
                </Column>
                <!-- Azioni sempre presenti: la stampa (anteprima/documenti) è
                     una lettura, disponibile anche in sola lettura. -->
                <Column class="app-col-actions" :exportable="false">
                  <template #body="{ data }">
                    <RowActionsMenu :row="data" :actions="buildFatturaActions(data)" />
                  </template>
                </Column>
                <template #empty>
                  <div class="app-empty-state"><i class="pi pi-inbox" /><p>{{ t('vendite.lotti.nessuna_fattura') }}</p></div>
                </template>
              </DataTable>
            </TabPanel>

            <!-- Task-run (tentativi ed esiti per step). -->
            <TabPanel value="task">
              <DataTable
                :value="taskRuns"
                :loading="tabLoading"
                class="app-datatable app-datatable--inner"
                striped-rows
                size="small"
                data-key="id"
              >
                <Column field="task_code" :header="t('vendite.lotti.col_task')">
                  <template #body="{ data }">{{ data.fase || data.task_code }}</template>
                </Column>
                <Column field="tentativo" :header="t('vendite.lotti.col_tentativo')" style="width: 90px;">
                  <template #body="{ data }">{{ data.tentativo }}</template>
                </Column>
                <Column field="task_stato" :header="t('vendite.lotti.col_esito')" style="width: 120px;">
                  <template #body="{ data }">
                    <Tag :value="data.task_stato" :severity="statoTaskRunSeverity(data.task_stato)" />
                  </template>
                </Column>
                <Column field="error_message" :header="t('vendite.lotti.col_errore')">
                  <template #body="{ data }">
                    <span v-if="data.error_code" class="app-dash-ritardo">
                      {{ data.error_code }}: {{ data.error_message ?? '' }}
                    </span>
                    <span v-else>—</span>
                  </template>
                </Column>
                <Column field="ended_at" :header="t('vendite.lotti.col_fine')" style="width: 150px;">
                  <template #body="{ data }">
                    {{ data.ended_at ? displayTimestamp(data.ended_at) : '—' }}
                  </template>
                </Column>
                <template #empty>
                  <div class="app-empty-state"><i class="pi pi-inbox" /><p>{{ t('vendite.lotti.nessun_task') }}</p></div>
                </template>
              </DataTable>
            </TabPanel>

            <!-- Segnalazioni (riepilogo). -->
            <TabPanel value="segnalazioni">
              <div v-if="segnalazioni" class="app-lotto-segnalazioni">
                <div class="app-lotto-segn-row">
                  <Tag :value="String(segnalazioni.critical_count ?? 0)" severity="danger" />
                  <span>{{ t('vendite.lotti.critical') }}</span>
                </div>
                <div class="app-lotto-segn-row">
                  <Tag :value="String(segnalazioni.warning_count ?? 0)" severity="warn" />
                  <span>{{ t('vendite.lotti.warning') }}</span>
                </div>
                <div class="app-lotto-segn-row">
                  <Tag :value="String(segnalazioni.attention_count ?? 0)" severity="info" />
                  <span>{{ t('vendite.lotti.attention') }}</span>
                </div>
                <Message v-if="segnalazioni.blocks_next_step" severity="warn" :closable="false">
                  {{ t('vendite.lotti.blocca_step') }}
                </Message>
              </div>
              <div v-else class="app-empty-state"><i class="pi pi-check-circle" /><p>{{ t('vendite.lotti.nessuna_segnalazione') }}</p></div>
            </TabPanel>
          </TabPanels>
        </Tabs>
      </template>

      <FormFooter close-only @cancel="onClose" />
    </div>

    <!-- Archivio documenti generati della fattura selezionata (sorgente FATTURA). -->
    <PdfDocumentiSorgenteDialog
      v-model:visible="pdfDialogVisible"
      :sorgente-code="SORGENTE_CODES.FATTURA"
      :sorgente-id="pdfFatturaId"
      :title="t('vendite.lotti.documenti_fattura_titolo')"
    />

    <!-- Consultazione della fattura a video (documento completo). -->
    <FatturaDrawer
      v-model:visible="fatturaDrawerVisible"
      :fattura-id="fatturaDrawerId"
    />
  </Drawer>
</template>

<style scoped>
.app-lotto-step {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
}
.app-mt-1 {
  margin-top: 1rem;
}
.app-lotto-segnalazioni {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem 0;
}
.app-lotto-segn-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
</style>

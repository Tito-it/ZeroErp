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
import Button from 'primevue/button'
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
import FormFooter from '../../core/components/FormFooter.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useNotify } from '../../core/composables/useNotify'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerDetailLoad } from '../../core/composables/useDrawerDetailLoad'
import { useActionPermission } from '../../core/composables/useActionPermission'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
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
  runLottoPipeline,
  resetLottoDraft,
  resetLottoFatturaDraft,
} from '../api/lotti'

const props = defineProps({
  visible: { type: Boolean, default: false },
  lottoId: { type: [Number, null], default: null },
  // Ispezione pura (feedback_drawer_readonly): nasconde ogni azione di governo.
  readonly: { type: Boolean, default: false },
})

const emit = defineEmits(['update:visible', 'changed'])
const { t } = useI18n()
const { execute, loading } = useApiHandler()
const notify = useNotify()
const { confirmAction } = useConfirmAction()
const onClose = useDrawerClose(emit)
const { loadDetailOrClose } = useDrawerDetailLoad(onClose)
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

// Readonly effettivo: area in LETTURA (inject dal provider della view) o prop
// di ispezione. In readonly le azioni di governo spariscono (il BE resta il
// guard vero, questo e' UX coerente col pattern protect).
const parentReadonly = useInjectReadonly()
const isReadonly = computed(() => parentReadonly.value || props.readonly)

// Gate azioni: pipeline (avanza/rerun) e i due reset hanno permessi propri.
const { isAllowed: canPipeline } = useActionPermission('genera_fatture_lotti')
const { isAllowed: canResetLotto } = useActionPermission('reset_lotto_draft')
const { isAllowed: canResetFattura } = useActionPermission('reset_lotto_fattura_draft')

const lotto = ref(null)
const fatture = ref([])
const taskRuns = ref([])
const segnalazioni = ref(null)
const tabLoading = ref(false)

const isErrore = computed(() => lotto.value?.stato_lotto === 'ERRORE')
const isInEsecuzione = computed(() => lotto.value?.stato_lotto === 'IN_ESECUZIONE')

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
    if (!visible || !props.lottoId) return
    lotto.value = null
    fatture.value = []
    taskRuns.value = []
    segnalazioni.value = null
    await reloadAll()
  },
  { immediate: true },
)

// ------------------------------------------------------------------ azioni
// Scopo: avanza la pipeline del lotto di UN step (com'è il motore). Il rerun
//        su ERRORE è lo stesso comando: ri-esegue lo step corrente.
function avanzaStep(isRerun) {
  confirmAction({
    title: isRerun ? t('vendite.lotti.rerun_header') : t('vendite.lotti.avanza_header'),
    message: isRerun ? t('vendite.lotti.rerun_conferma') : t('vendite.lotti.avanza_conferma'),
    onAccept: async () => {
      const res = await execute(() => runLottoPipeline(props.lottoId))
      if (res !== null) {
        notify.success(t('vendite.lotti.avanza_esito'))
        await reloadAll()
        emit('changed')
      }
    },
  })
}

// Scopo: riporta il lotto a bozza — DEMOLIZIONE. Conferma forte e onesta.
function resetDraft() {
  confirmAction({
    title: t('vendite.lotti.reset_header'),
    message: t('vendite.lotti.reset_conferma'),
    danger: true,
    acceptLabel: t('vendite.lotti.reset_accept'),
    onAccept: async () => {
      const res = await execute(() => resetLottoDraft(props.lottoId))
      if (res !== null) {
        notify.success(t('vendite.lotti.reset_esito', {
          fatture: res?.deleted_fatture ?? 0,
          attivita: res?.updated_attivita ?? 0,
        }))
        await reloadAll()
        emit('changed')
      }
    },
  })
}

// Scopo: reset di una singola fattura DRAFT del lotto.
function resetFattura(row) {
  confirmAction({
    title: t('vendite.lotti.reset_fattura_header'),
    message: t('vendite.lotti.reset_fattura_conferma'),
    danger: true,
    onAccept: async () => {
      const res = await execute(() => resetLottoFatturaDraft(props.lottoId, row.fattura_id))
      if (res !== null) {
        notify.success(t('vendite.lotti.reset_fattura_esito'))
        await reloadFatture()
        emit('changed')
      }
    },
  })
}

// Riga fattura DRAFT (pre-fiscale) → reset ammesso; oltre no (gate vero al BE).
// Il gate usa il codice stabile (codice_interno), MAI la descrizione display.
function buildFatturaActions(row) {
  if (isReadonly.value) return []
  return [
    {
      key: 'reset',
      label: t('vendite.lotti.azione_reset_fattura'),
      icon: 'pi pi-undo',
      visible: canResetFattura.value && row.stato_doc_fiscale_codice === 'DRAFT',
      command: () => resetFattura(row),
    },
  ]
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

        <!-- Azioni di governo del lotto (nascoste in sola lettura). -->
        <div v-if="!isReadonly" class="app-lotto-actions">
          <Button
            v-if="canPipeline && isErrore"
            :label="t('vendite.lotti.rerun')"
            icon="pi pi-replay"
            severity="warn"
            size="small"
            :disabled="loading"
            @click="avanzaStep(true)"
          />
          <Button
            v-else-if="canPipeline && !isInEsecuzione"
            :label="t('vendite.lotti.avanza')"
            icon="pi pi-forward"
            size="small"
            :disabled="loading || haSegnalazioniCritiche"
            @click="avanzaStep(false)"
          />
          <Button
            v-if="canResetLotto"
            :label="t('vendite.lotti.reset')"
            icon="pi pi-undo"
            severity="danger"
            outlined
            size="small"
            :disabled="loading"
            @click="resetDraft"
          />
        </div>

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
                <Column v-if="!isReadonly" class="app-col-actions" :exportable="false">
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
  </Drawer>
</template>

<style scoped>
.app-lotto-step {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 0.75rem;
}
.app-lotto-actions {
  display: flex;
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

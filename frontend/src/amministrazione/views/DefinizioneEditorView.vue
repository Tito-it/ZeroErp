<script setup>
// Scopo: Editor/ispettore di una singola edizione di workflow versionata (Fase 3).
// FE-3.1 = SOLA LETTURA: header + banner drift, lista step, e per lo step
// selezionato i figli (canali/handler-eventi/competenze) + i prerequisiti;
// in coda gli archi a livello edizione (formule tempo / regole generazione).
// Consuma GET /pratiche/definizioni/<id>/ (anelli BE 1-2).
//
// La sola-lettura dell'editor è derivata: livello area (useReadonlyMode) OR
// stato ≠ BOZZA (solo le BOZZE per emittente sono strutturalmente editabili —
// vincolo enforce dal DB). Il provide(READONLY_KEY) propaga il gate ai futuri
// componenti di editing (FE-3.2+), rispettando la convenzione OR del composable.
import { computed, onActivated, provide, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
// ⛔ DEBITO, non eccezione: gli step della definizione col form sotto sono un
// master-detail inline, da portare sullo standard insieme alle sotto-liste
// di `CollectionEditorPanel`.
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import Button from 'primevue/button'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import { useReadonlyMode, READONLY_KEY } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useFormInline } from '../../core/composables/useFormInline'
import { MANAGE_ICONS, READONLY_DOMAINS, STATO_DEFINIZIONE, STATUS_ICONS } from '../../core/constants'
import { updateStep, deleteStep, forkDefinizione } from '../api/definizioniWorkflow'
import { useDefinizioneEditorStore } from '../stores/definizioneEditor'
import DefinizioneStepForm from '../components/DefinizioneStepForm.vue'
import StepCanaliTab from '../components/StepCanaliTab.vue'
import StepHandlerEventiTab from '../components/StepHandlerEventiTab.vue'
import StepCompetenzeTab from '../components/StepCompetenzeTab.vue'
import StepPrerequisitiTab from '../components/StepPrerequisitiTab.vue'
import ArchiFormuleTab from '../components/ArchiFormuleTab.vue'
import ArchiRegoleTab from '../components/ArchiRegoleTab.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const store = useDefinizioneEditorStore()
const { execute, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()

const defId = computed(() => Number(route.params.id))

// Readonly di area (LETTURA/BLOCCATO amm-software) + gate stato edizione.
const { isReadonly } = useReadonlyMode(READONLY_DOMAINS.AMM_SOFTWARE)
const editorReadonly = computed(
  () => isReadonly.value || store.definizione?.stato !== STATO_DEFINIZIONE.BOZZA,
)
// Sovrascrive il READONLY_KEY per i figli: l'OR con isReadonly (che a sua volta
// ingloba l'eventuale parent) preserva la propagazione da contesti superiori.
provide(READONLY_KEY, editorReadonly)

// Step selezionato (riga master); il dettaglio figli/prerequisiti lo segue.
const selectedStep = ref(null)

const drift = computed(() => {
  const d = store.definizione?.drift
  return d && d.versioni_indietro > 0 ? d : null
})

// Prerequisiti entranti nello step selezionato (arco: template_flusso_id =
// step che richiede, prerequisito_id = step richiesto).
const prereqSelezionato = computed(() =>
  selectedStep.value
    ? store.archi.prerequisiti.filter((p) => p.template_flusso_id === selectedStep.value.id)
    : [],
)

function statoSeverity(stato) {
  if (stato === STATO_DEFINIZIONE.PUBBLICATA) return 'success'
  if (stato === STATO_DEFINIZIONE.BOZZA) return 'warn'
  return 'secondary'
}

function emittenteLabel(def) {
  return def?.emittente_fiscale_id
    ? def.emittente_display
    : t('amministrazione.definizioni_workflow.preset')
}

function tornaLista() {
  router.push({ name: 'amm-software-definizioni-workflow' })
}

// «Allinea al preset» (FE-3.5, strada A). Nessun BE nuovo: forka il preset
// CORRENTE (aggiornato) per questo emittente → nuova BOZZA copia-fresca; le
// personalizzazioni le ri-applica l'admin a mano confrontando con l'edizione
// attuale. Il ≤1-BOZZA-per-scope resta guard DB (errore parlante se già aperta).
const allineaLoading = ref(false)
function onAllinea() {
  const d = drift.value
  const emittenteId = store.definizione?.emittente_fiscale_id
  if (!d?.preset_corrente_id || !emittenteId) return
  confirmAction({
    header: t('amministrazione.definizioni_workflow.ed_allinea'),
    message: t('amministrazione.definizioni_workflow.ed_allinea_conferma', { corrente: d.versione_preset_corrente }),
    onAccept: async () => {
      allineaLoading.value = true
      try {
        const res = await execute(
          () => forkDefinizione(d.preset_corrente_id, emittenteId),
          { successMessage: t('amministrazione.definizioni_workflow.ed_msg_allinea_ok') },
        )
        const nuovoId = res?.definizione_id
        if (res !== null && nuovoId) {
          router.push({ name: 'amm-software-definizione-editor', params: { id: nuovoId } })
        }
      } finally {
        allineaLoading.value = false
      }
    },
  })
}

async function loadDettaglio() {
  selectedStep.value = null
  chiudiForm()
  if (!defId.value) return
  try {
    await store.load(defId.value)
    // Preseleziona il primo step per un dettaglio immediato.
    selectedStep.value = store.steps[0] ?? null
  } catch {
    // lastError già valorizzato dallo store → banner in template.
  }
}

// --- Editing step (FE-3.2, anello BE 3). Solo con editor editabile. ---
// La macchina del form (null | 'create' | 'edit', e lo step in modifica) e' il
// BB core `useFormInline` (sede unica, ok Tid 2026-09-28). Il padre e' la
// definizione: aprirne un'altra chiude il form.
const {
  formMode, rigaInModifica: stepInForm, nuovaRiga: onNuovoStep, apriRiga, chiudiForm, ancoraForm,
} = useFormInline({ padre: () => defId.value })

// Ordine stabile per il riordino ▲▼ (la DataTable ordina per sequenza in view).
const stepsOrdinati = computed(() => [...store.steps].sort((a, b) => a.sequenza - b.sequenza))
const nextSequenza = computed(
  () => store.steps.reduce((m, s) => Math.max(m, s.sequenza ?? 0), 0) + 10,
)

// Modificare uno step lo seleziona anche nel dettaglio.
function onEditStep(step) {
  apriRiga(step)
  selectedStep.value = step
}

// Ricarica il dettaglio e riseleziona lo step per id. Default-param (non `??`)
// per distinguere i due intenti: omesso → preserva la selezione corrente;
// `null` esplicito → reset al primo step (usato dopo l'eliminazione del selezionato).
async function reloadPreserving(reselectId = selectedStep.value?.id) {
  await store.load(defId.value)
  selectedStep.value =
    (reselectId != null && store.steps.find((s) => s.id === reselectId)) || store.steps[0] || null
}

async function onStepSaved(stepId) {
  chiudiForm()
  await reloadPreserving(stepId)
}

// Un figlio (canale/handler-evento/competenza) è stato mutato → ricarica il
// dettaglio preservando lo step selezionato (le sue sotto-liste si aggiornano).
async function onFigliChanged() {
  await reloadPreserving(selectedStep.value?.id)
}

function onDeleteStep(step) {
  confirmAction({
    header: t('confirm.delete_title'),
    message: t('amministrazione.definizioni_workflow.ed_conferma_elimina_step', { codice: step.codice }),
    onAccept: async () => {
      const res = await execute(() => deleteStep(defId.value, step.id), {
        successMessage: t('amministrazione.definizioni_workflow.ed_msg_step_eliminato'),
      })
      if (res === null) return
      if (stepInForm.value?.id === step.id) chiudiForm()
      await reloadPreserving(selectedStep.value?.id === step.id ? null : selectedStep.value?.id)
    },
  })
}

// Riordino ▲▼ zero-dep: normalizza le sequenze a (i+1)*10 sull'ordine nuovo e
// PATCH solo gli step la cui sequenza cambia. Nessun UNIQUE su `sequenza` (solo
// su definizione_id+codice) → niente collisione durante lo swap. Le PATCH sono
// sequenziali: su fallimento parziale si ricarica comunque per riconciliare la UI
// con lo stato DB effettivo.
async function onMoveStep(step, dir) {
  const ordered = stepsOrdinati.value
  const idx = ordered.findIndex((s) => s.id === step.id)
  const swap = dir === 'up' ? idx - 1 : idx + 1
  if (swap < 0 || swap >= ordered.length) return
  const nuovo = [...ordered]
  ;[nuovo[idx], nuovo[swap]] = [nuovo[swap], nuovo[idx]]
  const changed = nuovo
    .map((s, i) => ({ id: s.id, seq: (i + 1) * 10, old: s.sequenza }))
    .filter((c) => c.seq !== c.old)
  if (!changed.length) return
  await execute(async () => {
    let last
    for (const c of changed) last = await updateStep(defId.value, c.id, { sequenza: c.seq })
    return last
  }, {})
  await reloadPreserving(step.id)
}

function buildStepActions(step) {
  const ordered = stepsOrdinati.value
  const idx = ordered.findIndex((s) => s.id === step.id)
  return [
    { key: 'edit', label: t('common.edit'), icon: MANAGE_ICONS.EDIT, command: () => onEditStep(step) },
    {
      key: 'up',
      label: t('amministrazione.definizioni_workflow.ed_step_su'),
      icon: MANAGE_ICONS.COLLAPSE,
      disabled: idx <= 0,
      command: () => onMoveStep(step, 'up'),
    },
    {
      key: 'down',
      label: t('amministrazione.definizioni_workflow.ed_step_giu'),
      icon: MANAGE_ICONS.EXPAND,
      disabled: idx >= ordered.length - 1,
      command: () => onMoveStep(step, 'down'),
    },
    {
      key: 'delete',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      command: () => onDeleteStep(step),
    },
  ]
}

// ⚠️ `onActivated` e non `onMounted`: la view vive sotto `<KeepAlive :max="10">`
//    (AppLayout), quindi al rientro `onMounted` non riscatta e a video resterebbe
//    l'elenco di prima. ⛔ Sostituisce, non si aggiunge: sotto KeepAlive al primo
//    montaggio scattano ENTRAMBI, quindi tenerli tutti e due farebbe due fetch.
onActivated(loadDettaglio)
watch(defId, loadDettaglio)
</script>

<template>
  <div class="app-page definizione-editor">
    <div class="app-page-toolbar">
      <div class="app-page-toolbar-start">
        <Button
          :label="t('amministrazione.definizioni_workflow.ed_torna_lista')"
          :icon="MANAGE_ICONS.BACK"
          text
          @click="tornaLista"
        />
      </div>
    </div>

    <Message v-if="store.lastError" severity="error" :closable="false">
      {{ t('amministrazione.definizioni_workflow.ed_caricamento_errore') }}
    </Message>

    <template v-if="store.definizione">
      <!-- Header edizione -->
      <div class="editor-header">
        <div class="editor-header__main">
          <span class="editor-header__title">
            {{ store.definizione.tipo_prestazione_descrizione }}
          </span>
          <Tag :value="store.definizione.stato" :severity="statoSeverity(store.definizione.stato)" />
        </div>
        <div class="editor-header__meta">
          <span>
            <strong>{{ t('amministrazione.definizioni_workflow.ed_lbl_emittente') }}:</strong>
            {{ emittenteLabel(store.definizione) }}
          </span>
          <span>
            <strong>{{ t('amministrazione.definizioni_workflow.ed_lbl_versione') }}:</strong>
            {{ store.definizione.versione }}
          </span>
        </div>
        <p v-if="store.definizione.descrizione" class="editor-header__descr">
          {{ store.definizione.descrizione }}
        </p>
      </div>

      <Message v-if="editorReadonly" severity="info" :closable="false" size="small">
        {{ t('amministrazione.definizioni_workflow.ed_readonly_hint') }}
      </Message>

      <Message v-if="drift" severity="warn" :closable="false">
        <div class="editor-drift">
          <span>
            {{ t('amministrazione.definizioni_workflow.ed_drift_banner', {
              n: drift.versioni_indietro,
              origine: store.definizione.versione_origine,
              corrente: drift.versione_preset_corrente,
            }) }}
          </span>
          <Button
            v-if="!isReadonly"
            :label="t('amministrazione.definizioni_workflow.ed_allinea')"
            :icon="MANAGE_ICONS.CLONE"
            size="small"
            severity="warn"
            :loading="allineaLoading"
            @click="onAllinea"
          />
        </div>
      </Message>

      <!-- Step del workflow -->
      <div class="editor-section-head">
        <h2 class="editor-section-title">{{ t('amministrazione.definizioni_workflow.ed_sez_steps') }}</h2>
        <Button
          v-if="!editorReadonly"
          :label="t('amministrazione.definizioni_workflow.ed_nuovo_step')"
          :icon="MANAGE_ICONS.ADD"
          size="small"
          @click="onNuovoStep"
        />
      </div>
      <DataTable
        v-model:selection="selectedStep"
        :value="store.steps"
        :loading="store.loading"
        selection-mode="single"
        data-key="id"
        striped-rows
        class="app-datatable"
        :sort-field="'sequenza'"
        :sort-order="1"
      >
        <template #empty>{{ t('amministrazione.definizioni_workflow.ed_steps_vuoto') }}</template>
        <Column field="sequenza" :header="t('amministrazione.definizioni_workflow.ed_col_sequenza')" sortable style="width: 70px;" />
        <Column field="codice" :header="t('amministrazione.definizioni_workflow.ed_col_codice')" sortable style="min-width: 180px;" />
        <Column field="descrizione" :header="t('amministrazione.definizioni_workflow.ed_col_descrizione')" style="min-width: 200px;" />
        <Column :header="t('amministrazione.definizioni_workflow.ed_col_obbligatorio')" style="width: 70px;">
          <template #body="{ data }">
            <i v-if="data.obbligatorio" class="editor-bool-yes" :class="STATUS_ICONS.SI" />
          </template>
        </Column>
        <Column field="direzione" :header="t('amministrazione.definizioni_workflow.ed_col_direzione')" style="width: 110px;" />
        <Column field="modalita_esito" :header="t('amministrazione.definizioni_workflow.ed_col_modalita_esito')" style="width: 130px;" />
        <Column :header="t('amministrazione.definizioni_workflow.ed_col_attivo')" style="width: 70px;">
          <template #body="{ data }">
            <i v-if="data.attivo" class="editor-bool-yes" :class="STATUS_ICONS.SI" />
          </template>
        </Column>
        <Column v-if="!editorReadonly" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
          <template #body="{ data }">
            <RowActionsMenu :row="data" :actions="buildStepActions(data)" />
          </template>
        </Column>
      </DataTable>

      <!-- Form step inline (create/edit) -->
      <div v-if="formMode" :ref="ancoraForm" class="app-drawer-section editor-step-form">
        <h3 class="editor-section-title">
          {{ formMode === 'edit'
            ? t('amministrazione.definizioni_workflow.ed_step_form_edit', { codice: stepInForm?.codice })
            : t('amministrazione.definizioni_workflow.ed_step_form_new') }}
        </h3>
        <DefinizioneStepForm
          :definizione-id="defId"
          :step="stepInForm"
          :next-sequenza="nextSequenza"
          @saved="onStepSaved"
          @cancel="chiudiForm"
        />
      </div>

      <!-- Dettaglio dello step selezionato -->
      <template v-if="selectedStep">
        <h2 class="editor-section-title">
          {{ t('amministrazione.definizioni_workflow.ed_step_dettaglio', { codice: selectedStep.codice }) }}
        </h2>
        <Tabs value="canali">
          <TabList>
            <Tab value="canali">{{ t('amministrazione.definizioni_workflow.ed_tab_canali') }}</Tab>
            <Tab value="handler">{{ t('amministrazione.definizioni_workflow.ed_tab_handler_eventi') }}</Tab>
            <Tab value="competenze">{{ t('amministrazione.definizioni_workflow.ed_tab_competenze') }}</Tab>
            <Tab value="prerequisiti">{{ t('amministrazione.definizioni_workflow.ed_tab_prerequisiti') }}</Tab>
          </TabList>
          <TabPanels>
            <!-- :key = step selezionato → remount al cambio step: azzera il form
                 figlio eventualmente aperto (niente save mis-targeted sul nuovo step). -->
            <TabPanel value="canali">
              <StepCanaliTab
                :campi-errati="campiErrati"
                :key="selectedStep.id"
                :definizione-id="defId"
                :step-id="selectedStep.id"
                :rows="selectedStep.canali"
                @changed="onFigliChanged"
              />
            </TabPanel>
            <TabPanel value="handler">
              <StepHandlerEventiTab
                :campi-errati="campiErrati"
                :key="selectedStep.id"
                :definizione-id="defId"
                :step-id="selectedStep.id"
                :rows="selectedStep.handler_eventi"
                @changed="onFigliChanged"
              />
            </TabPanel>
            <TabPanel value="competenze">
              <StepCompetenzeTab
                :campi-errati="campiErrati"
                :key="selectedStep.id"
                :definizione-id="defId"
                :step-id="selectedStep.id"
                :rows="selectedStep.competenze"
                @changed="onFigliChanged"
              />
            </TabPanel>
            <TabPanel value="prerequisiti">
              <StepPrerequisitiTab
                :key="selectedStep.id"
                :definizione-id="defId"
                :step-id="selectedStep.id"
                :rows="prereqSelezionato"
                :steps="store.steps"
                @changed="onFigliChanged"
              />
            </TabPanel>
          </TabPanels>
        </Tabs>
      </template>
      <Message v-else severity="secondary" :closable="false" size="small">
        {{ t('amministrazione.definizioni_workflow.ed_step_seleziona') }}
      </Message>

      <!-- Archi a livello edizione -->
      <h2 class="editor-section-title">{{ t('amministrazione.definizioni_workflow.ed_sez_archi') }}</h2>
      <Tabs value="formule">
        <TabList>
          <Tab value="formule">{{ t('amministrazione.definizioni_workflow.ed_tab_formule_tempo') }}</Tab>
          <Tab value="regole">{{ t('amministrazione.definizioni_workflow.ed_tab_regole_generazione') }}</Tab>
        </TabList>
        <TabPanels>
          <TabPanel value="formule">
            <ArchiFormuleTab
              :campi-errati="campiErrati"
              :definizione-id="defId"
              :rows="store.archi.formule_tempo"
              :steps="store.steps"
              @changed="onFigliChanged"
            />
          </TabPanel>
          <TabPanel value="regole">
            <ArchiRegoleTab
              :campi-errati="campiErrati"
              :definizione-id="defId"
              :rows="store.archi.regole_generazione"
              :steps="store.steps"
              @changed="onFigliChanged"
            />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </template>
  </div>
</template>

<style scoped>
.definizione-editor {
  overflow-y: auto;
}

.editor-header {
  margin-bottom: 0.75rem;
}

.editor-header__main {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.35rem;
}

.editor-header__title {
  font-size: var(--app-font-size-lg);
  font-weight: 600;
}

.editor-header__meta {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  color: var(--app-text-muted);
  font-size: var(--app-font-size-sm);
}

.editor-header__descr {
  margin: 0.35rem 0 0;
  color: var(--app-text-muted);
}

.editor-section-title {
  font-size: var(--app-font-size-base);
  font-weight: 600;
  margin: 0.5rem 0 0.5rem;
}

.editor-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.editor-drift {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  width: 100%;
  flex-wrap: wrap;
}

.editor-step-form {
  margin-bottom: 1rem;
}

.editor-bool-yes {
  color: var(--app-success-color);
}
</style>

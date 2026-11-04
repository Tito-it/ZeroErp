<script setup>
// Scopo: Drawer dettaglio/creazione pratica con Tabs (Dati, Flussi, Giornale).
// In edit: 3 tab + bottoni azioni stato nel tab Dati.
//          I campi display (stato_descrizione, soggetto_display, ecc.) arrivano dal backend.
// In create: solo form creazione (no tab).
import { ref, watch, computed, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePraticheStore } from '../stores/pratiche'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useInjectReadonly, READONLY_KEY } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { displayDate, toDateString, parseIsoDate } from '../../core/utils/date'
import { statoPraticaSeverity, prioritaPraticaSeverity } from '../../core/utils/severity'
import { DRAWER_WIDTH, MANAGE_ICONS, STATO_PRATICA, STATI_PRATICA_TERMINALI, DATE_FORMAT, TIPO_RUOLO } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import AppDrawer from '../../core/components/AppDrawer.vue'
import DrawerEntityHeader from '../../core/components/DrawerEntityHeader.vue'
import DrawerActionsBar from '../../core/components/DrawerActionsBar.vue'
import SoggettoResolver from '../../anagrafiche/components/SoggettoResolver.vue'
import SoggettoRuoloLookup from '../../core/components/SoggettoRuoloLookup.vue'
import IstanzaUtilityLookup from '../../core/components/IstanzaUtilityLookup.vue'
import { getSoggettoRuoloLookupById } from '../../core/apiCore'
import { useLookupCodici } from '../../core/composables/useLookupCodici'
import { useFooterDocumento } from '../../core/composables/useFooterDocumento'
import PraticaFlussiTab from './PraticaFlussiTab.vue'
import PraticaNoteTab from './PraticaNoteTab.vue'
import PraticaAllegatiTab from './PraticaAllegatiTab.vue'
import PraticaSospensioniTab from './PraticaSospensioniTab.vue'
import PraticaGiornaleTab from './PraticaGiornaleTab.vue'
import SospensionePraticaDialog from './SospensionePraticaDialog.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import InputText from 'primevue/inputtext'
import Textarea from 'primevue/textarea'
import DatePicker from 'primevue/datepicker'
import Tab from 'primevue/tab'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const { t } = useI18n()
const store = usePraticheStore()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  praticaId: { type: Number, default: null },
  // Default tipo prestazione in creazione (home launcher / filtro lista
  // attivo): pre-compila il Select, l'operatore puo' sempre cambiarlo.
  presetTipoPrestazioneId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({})
const detail = ref(null)
// Tab attivo, riportato su 'dati' a ogni riapertura del drawer: senza
// reset, riaprendo su un'altra pratica si resterebbe sul tab dell'ultima
// consultazione (con TabView lo faceva implicitamente il remount).
const activeTab = ref('dati')

function defaultForm() {
  return {
    tipo_prestazione_id: null,
    priorita_id: null,
    descrizione: '',
    data_scadenza: null
  }
}

// Selezione contesto anagrafico (solo creazione): lookup ricco a una riga
// per soggetto+ruolo (+ riga "senza ruolo" per i soggetti privi di ruoli) +
// la FORNITURA a valle per il cliente. La fornitura e' il billing account,
// cioe' la coppia istanza+utility: e' il cliente a grana fine di cui la
// pratica parla (D-9 di brief-db-istanza-nasce-col-ba). L'istanza la ricava
// il backend dal BA.
const resolverVisible = ref(false)
const contestoSelezionato = ref(null)
// Riga del lookup forniture (IstanzaUtilityLookup, una riga per BA).
const fornituraSelezionata = ref(null)

// Modifiche non salvate: fotografia a form popolato (apertura, ricarica,
// salvataggio), chiudere con modifiche chiede conferma (BB useDrawerFormPreserve).
// In creazione contesto e fornitura scelti stanno fuori dal form: il confronto
// ne raccoglie gli id. Dopo i loro ref: il computed li legge subito (TDZ).
const formSalvato = computed(() => ({
  ...form.value,
  contesto_soggetto_id: contestoSelezionato.value?.soggetto_id ?? null,
  contesto_soggetto_ruolo_id: contestoSelezionato.value?.soggetto_ruolo_id ?? null,
  fornitura_ba_id: fornituraSelezionata.value?.billing_account_id ?? null
}))
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(formSalvato, { visibile: () => props.visible })

// Solo il ruolo CLIENTE ha forniture (il BA e' del ruolo CL); per gli altri
// ruoli, e per la riga "senza ruolo", il campo non ha senso: la pratica
// accetta un BA solo dal suo ruolo (E_PRATICHE_BA_NON_COERENTE).

// Fornitura auto-derivata: cliente con UN solo BA -> niente picker, hint
// informativo, payload automatico.
const baDerivato = computed(() => {
  const c = contestoSelezionato.value
  return (c?.ruolo_codice_interno === TIPO_RUOLO.CLIENTE && c?.billing_account_unico_id) || null
})

// Picker fornitura visibile solo quando la scelta e' davvero dell'operatore:
// - ruolo diverso da CL o riga "senza ruolo" -> mai;
// - CL con un BA solo -> mai (auto-derivato, vedi hint);
// - CL con piu' BA (piu' istanze, o un'istanza con piu' utility) -> visibile.
const mostraCampoFornitura = computed(() => {
  const c = contestoSelezionato.value
  if (c?.ruolo_codice_interno !== TIPO_RUOLO.CLIENTE) return false
  if (baDerivato.value) return false
  return (c.n_billing_account ?? 0) > 0
})

// Cambio contesto (soggetto O ruolo) → reset fornitura: quella selezionata
// apparteneva alla riga precedente e con ruolo non-CL il campo sparisce ma
// NON deve restare nel payload.
watch(contestoSelezionato, (next, prev) => {
  if (next?.soggetto_id !== prev?.soggetto_id
      || next?.soggetto_ruolo_id !== prev?.soggetto_ruolo_id) {
    fornituraSelezionata.value = null
  }
})

// Scopo: dopo creazione/selezione soggetto dal resolver (percorso secondario,
// es. soggetto nuovo non ancora in anagrafica), ricostruisce la riga lookup
// via restore by-id: per un soggetto appena creato e' la riga "senza ruolo"
// (nessuna fornitura).
async function onSoggettoRicevuto(data) {
  resolverVisible.value = false
  if (!data?.id) return
  // execute() unwrappa l'envelope: res e' direttamente la riga lookup.
  const res = await execute(() => getSoggettoRuoloLookupById({ soggetto_id: data.id }))
  if (res !== null) contestoSelezionato.value = res
}

function resetForm() {
  detail.value = null
  form.value = defaultForm()
  contestoSelezionato.value = null
  fornituraSelezionata.value = null
}

function populateFormFromDetail(d) {
  form.value = {
    tipo_prestazione_id: d.tipo_prestazione_id,
    priorita_id: d.priorita_id,
    descrizione: d.descrizione || '',
    data_scadenza: parseIsoDate(d.data_scadenza)
  }
}

// Stato corrente dalla risposta backend (campo display, no lookup)
const statoCorrente = computed(() => detail.value?.stato_codice_interno || '')

// Sola lettura su pratica in stato terminale (CHIUSA/ANNULLATA): non si modifica
// nulla. Combina col readonly iniettato (area/parent) come da convenzione
// useReadonlyMode e lo ri-fornisce ai figli (tab flussi/note/allegati: già
// reattivi a useInjectReadonly), oltre alla classe CSS app-readonly sul content.
const terminaleReadonly = computed(() =>
  STATI_PRATICA_TERMINALI.includes(statoCorrente.value)
)
const effectiveReadonly = computed(() => isReadonly.value || terminaleReadonly.value)
provide(READONLY_KEY, effectiveReadonly)

// `immediate`: robustezza al mount già-visibile (caller che monta il drawer
// on-demand con `visible` true dal primo render — es. celle lineage): senza,
// il watch non scatterebbe mai e il drawer resterebbe vuoto. Montato nascosto
// (caso normale) il guard `!val` rende la chiamata immediate un no-op.
watch(() => props.visible, async (val) => {
  if (!val) return
  activeTab.value = 'dati'
  if (isEdit.value && props.praticaId) {
    const d = await store.fetchDetail(props.praticaId)
    detail.value = d
    populateFormFromDetail(d)
  } else {
    resetForm()
    await preselectTipoPreset()
    await preselectPrioritaDefault()
  }
  fissa()
}, { immediate: true })

// Scopo: preset tipo dal contesto del caller (filtro lista attivo): default
// visibile, non un lock — il Select resta editabile. Validato contro le
// OPZIONI del Select (lookup no-obsoleti, stessa chiave cache: zero round-trip
// extra): il filtro lista include gli obsoleti, e un id fuori opzioni
// renderebbe il Select vuoto a video ma il valore verrebbe comunque salvato.
// Preset non tra le opzioni → si ignora (campo vuoto, scelta all'operatore).
const tipiLookup = useLookupCodici('pratiche.tipi_prestazione', { includiObsoleti: false })

async function preselectTipoPreset() {
  const presetId = props.presetTipoPrestazioneId
  if (presetId == null) return
  try {
    await tipiLookup.load()
    if (tipiLookup.items.value.some(r => r.id === presetId)) {
      form.value.tipo_prestazione_id = presetId
    }
  } catch {
    // Lookup fallito: nessun preset, l'operatore sceglie dal Select.
  }
}

// Scopo: default priorita' NORMALE in creazione, risolto per codice_interno
// dal lookup (mai id hardcodato — feedback_no_hardcoded_ids). Il BE applica
// comunque lo stesso default se il campo arriva vuoto: qui serve solo a
// renderlo VISIBILE all'operatore nel form. STESSA entry di cache della
// LookupSelect del form, per costruzione (`useLookupCodici`): la
// preselezione non aggiunge round-trip.
const prioritaLookup = useLookupCodici('config.priorita_pratiche')

async function preselectPrioritaDefault() {
  if (form.value.priorita_id != null) return
  try {
    await prioritaLookup.load()
    form.value.priorita_id =
      prioritaLookup.items.value.find(r => r.codice_interno === 'NORMALE')?.id ?? null
  } catch {
    // Lookup fallito: il campo resta vuoto, il BE applica il default.
  }
}

async function reloadDetail() {
  if (!props.praticaId) return
  const d = await store.fetchDetail(props.praticaId)
  detail.value = d
  populateFormFromDetail(d)
  fissa()
}

// --- Azioni stato pratica ---

// Scopo: esegue un'azione sullo store e ricarica il dettaglio se OK.
async function executeAction(fn) {
  const result = await execute(fn, { successMessage: t('pratiche.stato_cambiato') })
  if (result !== null) { await reloadDetail(); emit('saved', result) }
}

function onApriPratica() {
  executeAction(() => store.cambiaStato(props.praticaId, { nuovo_stato: STATO_PRATICA.APERTA }))
}

// Sospendi/Riattiva non sono piu' azioni dirette: aprono il dialog condiviso
// (data/ora manuale + motivo). Il dialog chiama lo store e, su successo, emette
// `saved` → ricarico dettaglio ed emetto `saved` al parent come le altre azioni
// di stato (Apri/Annulla): il parent rinfresca lista/coda e chiude il drawer
// (feedback_dialog_cambio_stato_dati_processo). Lo storico nel tab Sospensioni
// e' quindi sempre fresco alla riapertura della scheda.
const sospDialogVisible = ref(false)
const sospDialogMode = ref('sospendi')

function onSospendiPratica() {
  sospDialogMode.value = 'sospendi'
  sospDialogVisible.value = true
}
function onRiattivaPratica() {
  sospDialogMode.value = 'riattiva'
  sospDialogVisible.value = true
}
async function onSospensioneSaved(result) {
  await reloadDetail()
  emit('saved', result)
}
function onAnnullaPratica() {
  confirmAction({
    header: t('pratiche.azione_annulla'),
    message: t('pratiche.conferma_annulla'),
    danger: true,
    onAccept: () => executeAction(() => store.cambiaStato(props.praticaId, { nuovo_stato: STATO_PRATICA.ANNULLATA }))
  })
}

// Azioni della testata pratica consumate da DrawerActionsBar (refactor UI
// drawer 2026-05-22, Fase 3.A). State actions condizionali per stato corrente:
// Apri (BOZZA), Sospendi (APERTA), Riattiva (SOSPESA), Annulla (non terminale).
// La CHIUSURA non e' un'azione manuale: e' guidata dal workflow (auto-chiusura
// al completamento dei flussi). CHIUSA/ANNULLATA terminali: nessuna azione.
// Annulla con confirmAction integrato.
const drawerActions = computed(() => {
  if (!isEdit.value || !detail.value) return []
  const s = statoCorrente.value
  return [
    {
      key: 'apri',
      kind: 'state',
      label: t('pratiche.azione_apri'),
      icon: MANAGE_ICONS.APRI,
      severity: 'info',
      visible: s === STATO_PRATICA.BOZZA,
      hideWhenReadonly: true,
      command: onApriPratica,
    },
    {
      key: 'sospendi',
      kind: 'state',
      label: t('pratiche.azione_sospendi'),
      icon: MANAGE_ICONS.SOSPENDI,
      severity: 'warn',
      visible: s === STATO_PRATICA.APERTA,
      hideWhenReadonly: true,
      command: onSospendiPratica,
    },
    {
      key: 'riattiva',
      kind: 'state',
      label: t('pratiche.azione_riattiva'),
      icon: MANAGE_ICONS.PLAY,
      severity: 'success',
      visible: s === STATO_PRATICA.SOSPESA,
      hideWhenReadonly: true,
      command: onRiattivaPratica,
    },
    // Chiusura: rimossa come azione manuale — ora e' guidata dal workflow
    // (auto-chiusura al completamento dei flussi, trgfn_flussi_autochiusura_pratica).
    {
      key: 'annulla',
      kind: 'state',
      label: t('pratiche.azione_annulla'),
      icon: MANAGE_ICONS.ANNULLA,
      severity: 'danger',
      outlined: true,
      visible: s !== '' && s !== STATO_PRATICA.CHIUSA && s !== STATO_PRATICA.ANNULLATA,
      hideWhenReadonly: true,
      command: onAnnullaPratica,
    },
  ]
})

// --- Salvataggio ---

async function onSave() {
  if (isEdit.value) {
    const payload = {
      descrizione: form.value.descrizione || null,
      data_scadenza: form.value.data_scadenza
        ? toDateString(form.value.data_scadenza)
        : null
    }
    const result = await execute(
      () => store.update(props.praticaId, payload),
      { successMessage: t('pratiche.pratica_salvata') }
    )
    if (result !== null) { fissa(); emit('saved', result) }
  } else {
    const payload = {
      tipo_prestazione_id: form.value.tipo_prestazione_id,
      priorita_id: form.value.priorita_id,
      descrizione: form.value.descrizione || null,
      data_scadenza: form.value.data_scadenza
        ? toDateString(form.value.data_scadenza)
        : null,
      soggetto_id: contestoSelezionato.value?.soggetto_id || null,
      soggetto_ruolo_id: contestoSelezionato.value?.soggetto_ruolo_id || null,
      // Il cliente a grana fine: scelta esplicita dell'operatore, poi
      // l'auto-derivata (un BA solo, picker nascosto). L'istanza la ricava il
      // backend dal BA.
      billing_account_id: fornituraSelezionata.value?.billing_account_id || baDerivato.value || null,
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('pratiche.pratica_creata') }
    )
    if (result !== null) { fissa(); emit('saved', result) }
  }
}

const canSave = computed(() => {
  if (isEdit.value) return true
  // Priorita' non piu' bloccante: pre-selezionata NORMALE all'apertura e
  // comunque difesa dal default BE se il lookup di preselezione fallisse.
  return !!form.value.tipo_prestazione_id
})


// Il footer del drawer (BB useFooterDocumento, 2026-10-03): Annulla/Salva in
// creazione e, in modifica, sulla scheda Dati — fino a quel giorno stava
// dentro quei due pannelli —; «Chiudi» sulle altre schede, che un footer non
// l'avevano e si chiudevano solo dalla X.
const footerDrawer = useFooterDocumento({
  modificabile: () => !isEdit.value || activeTab.value === 'dati',
  presente: () => detail.value != null,
})
</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="props.visible"
    :title="t('pratiche.pratica')"
    :icon="NAV_ICONS.PRATICHE"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.COMPLEX"
    :readonly="effectiveReadonly"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="footerDrawer"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="onSave"
  >

  <!-- === CREAZIONE: form con soggetto/ruolo opzionali === -->
  <template v-if="!isEdit">
    <div class="form-grid">

      <!-- Contesto anagrafico (opzionale — pratica interna se vuoto):
           lookup ricco a una riga per soggetto+ruolo, incl. riga
           "senza ruolo" per i prospect puri. -->
      <h4>{{ t('pratiche.section_soggetto') }}</h4>
      <div class="form-field">
        <label>{{ t('pratiche.field_contesto') }}</label>
        <SoggettoRuoloLookup v-model="contestoSelezionato" />
        <small class="app-text-muted">{{ t('pratiche.soggetto_opzionale') }}</small>
      </div>
      <div>
        <Button :label="t('pratiche.nuovo_soggetto')" :icon="MANAGE_ICONS.ADD"
          text size="small" @click="resolverVisible = true" />
      </div>

      <!-- Fornitura (il BA): visibile solo quando la scelta e' dell'operatore
           (cliente con piu' BA). Cliente con un BA solo -> auto-derivato con
           hint; ruoli non-CL e riga "senza ruolo" -> nessuna fornitura. -->
      <div v-if="mostraCampoFornitura" class="form-field">
        <label>{{ t('pratiche.field_fornitura') }}</label>
        <!-- La combo e' ristretta alle forniture del ruolo selezionato: una
             riga per BA, cioe' per coppia istanza+utility. -->
        <IstanzaUtilityLookup
          v-model="fornituraSelezionata"
          :soggetto-id="contestoSelezionato.soggetto_id"
          :soggetto-ruolo-id="contestoSelezionato.soggetto_ruolo_id"
        />
        <!-- Hint contestuale: con piu' forniture la scelta e' il punto, non
             un opzionale generico. -->
        <small class="app-text-muted">
          {{ t('pratiche.fornitura_scegli', { n: contestoSelezionato.n_billing_account }) }}
        </small>
      </div>
      <div v-else-if="baDerivato" class="form-field">
        <label>{{ t('pratiche.field_fornitura') }}</label>
        <div class="app-field-hint">
          <i :class="MANAGE_ICONS.DERIVATO" style="margin-right: 0.4rem;"></i>
          {{ t('pratiche.fornitura_derivata', { codice: contestoSelezionato.billing_account_unico_codice }) }}
        </div>
      </div>

      <!-- Dati pratica -->
      <h4>{{ t('pratiche.section_dati') }}</h4>
      <div class="form-field">
        <label>{{ t('pratiche.col_tipo_prestazione') }} *</label>
        <LookupSelect
          v-model="form.tipo_prestazione_id"
          rel="pratiche.tipi_prestazione"
          :includi-obsoleti="false"
          :placeholder="t('pratiche.select_tipo_prestazione')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('pratiche.col_priorita') }}</label>
        <LookupSelect
          v-model="form.priorita_id"
          rel="config.priorita_pratiche"
          :placeholder="t('pratiche.select_priorita')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('pratiche.field_descrizione') }}</label>
        <Textarea v-model="form.descrizione" rows="3" auto-resize
          :invalid="campiErrati.includes('descrizione')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('pratiche.col_data_scadenza') }}</label>
        <DatePicker v-model="form.data_scadenza" :date-format="DATE_FORMAT" show-icon />
      </div>
    </div>

    <!-- Sotto-drawer: SoggettoResolver -->
    <SoggettoResolver
      :visible="resolverVisible"
      tipo-ruolo-codice=""
      @update:visible="v => resolverVisible = v"
      @soggetto-selezionato="onSoggettoRicevuto"
      @soggetto-creato="onSoggettoRicevuto"
      @annullato="resolverVisible = false"
    />
  </template>

  <!-- === EDIT: header + azioni in alto, poi Tabs con Dati + Flussi + Giornale === -->
  <template v-if="isEdit && detail">
    <!-- Refactor UI drawer 2026-05-22 (Fase 3.A): header info + barra
         azioni state in alto al drawer (sopra i Tabs), simmetrici a
         contratti/preventivi. Tag stato + Tag priorita' in #status,
         codice come identificativo a sinistra. -->
    <DrawerEntityHeader>
      <Tag :value="detail.codice" severity="secondary" />
      <template #status>
        <Tag
          :value="detail.stato_descrizione"
          :severity="statoPraticaSeverity(detail.stato_codice_interno)"
        />
        <Tag
          v-if="detail.priorita_descrizione"
          :value="detail.priorita_descrizione"
          :severity="prioritaPraticaSeverity(detail.priorita_codice_interno)"
        />
      </template>
    </DrawerEntityHeader>

    <DrawerActionsBar :actions="drawerActions" />

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="dati">{{ t('pratiche.tab_dati') }}</Tab>
        <Tab value="flussi">{{ t('pratiche.tab_flussi') }}</Tab>
        <Tab value="note">{{ t('pratiche.tab_note') }}</Tab>
        <Tab value="allegati">{{ t('pratiche.tab_allegati') }}</Tab>
        <Tab value="sospensioni">{{ t('pratiche.tab_sospensioni') }}</Tab>
        <Tab value="giornale">{{ t('pratiche.tab_giornale') }}</Tab>
      </TabList>
      <TabPanels>

      <!-- Tab Dati -->
      <TabPanel value="dati">
        <!-- Soggetto (se presente) -->
        <div v-if="detail.soggetto_display" class="form-field">
          <label>{{ t('pratiche.col_soggetto') }}</label>
          <InputText :model-value="detail.soggetto_display" disabled />
        </div>

        <!-- Form dati editabili -->
        <div class="form-grid">
          <div class="form-field">
            <label>{{ t('pratiche.col_tipo_prestazione') }}</label>
            <InputText :model-value="detail.tipo_prestazione_descrizione" disabled />
          </div>
          <div class="form-field">
            <label>{{ t('pratiche.col_priorita') }}</label>
            <LookupSelect
              v-model="form.priorita_id"
              rel="config.priorita_pratiche"
              :placeholder="t('pratiche.select_priorita')" show-clear
            />
          </div>
          <div class="form-field">
            <label>{{ t('pratiche.field_descrizione') }}</label>
            <Textarea v-model="form.descrizione" rows="3" auto-resize
              :invalid="campiErrati.includes('descrizione')"
            />
          </div>
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('pratiche.col_data_scadenza') }}</label>
              <DatePicker v-model="form.data_scadenza" :date-format="DATE_FORMAT" show-icon />
            </div>
            <div class="form-field">
              <label>{{ t('pratiche.col_data_apertura') }}</label>
              <InputText :model-value="displayDate(detail.data_apertura)" disabled />
            </div>
          </div>
          <div v-if="detail.risorsa_umana_display" class="form-field">
            <label>{{ t('pratiche.col_assegnata_a') }}</label>
            <InputText :model-value="detail.risorsa_umana_display" disabled />
          </div>
        </div>
      </TabPanel>

      <!-- Tab Flussi -->
      <TabPanel value="flussi">
        <!-- L'emittente della pratica scioglie il cancello di perimetro
             della lista `pratiche.flussi` (non `multi_emittente`). -->
        <PraticaFlussiTab
          :pratica-id="props.praticaId"
          :emittente-fiscale-id="detail?.emittente_fiscale_id ?? null"
        />
      </TabPanel>

      <!-- Tab Note -->
      <TabPanel value="note">
        <PraticaNoteTab :pratica-id="props.praticaId" />
      </TabPanel>

      <!-- Tab Allegati -->
      <TabPanel value="allegati">
        <PraticaAllegatiTab :pratica-id="props.praticaId" />
      </TabPanel>

      <!-- Tab Sospensioni -->
      <TabPanel value="sospensioni">
        <PraticaSospensioniTab :pratica-id="props.praticaId" />
      </TabPanel>

      <!-- Tab Giornale -->
      <TabPanel value="giornale">
        <PraticaGiornaleTab :pratica-id="props.praticaId" />
      </TabPanel>

      </TabPanels>
    </Tabs>

    <!-- Dialog condiviso sospendi/riattiva (data/ora manuale) aperto dai
         pulsanti della DrawerActionsBar. -->
    <SospensionePraticaDialog
      :visible="sospDialogVisible"
      :mode="sospDialogMode"
      :pratica-id="props.praticaId"
      @update:visible="v => sospDialogVisible = v"
      @saved="onSospensioneSaved"
    />
  </template>
  </AppDrawer>
</template>


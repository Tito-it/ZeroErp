<script setup>
// Scopo: Sezione master-detail inline delle versioni di un template
//        documentale (Tranche L). Visualizza lista versioni della
//        testata + form inline editabile per creazione/modifica
//        (memoria feedback_master_detail_inline).
//
// ⭐ DAL 2026-09-27 LA LISTA E' `documenti.template_versioni` (88), montata con
//    lo scaffolding dei tab-lista (`useDrawerTabLista` + `<DrawerTabLista>`):
//    pagine, ordinamento, ricerca sul titolo, «Personalizza colonne». Era una
//    `DataTable` grezza senza paginazione.
// ⏳ DEBITO DICHIARATO (brief-db-liste-datatable-grezze §4 riga 6): il form
//    della versione resta SOTTO la lista, al posto della lista, invece di un
//    drawer autonomo della versione (`feedback_drawer_autonomi`). Non e' di
//    questo giro: la conversione tocca la lista, non il master-detail.
//
//        Comandi versione (RowActionsMenu):
//         - Pubblica  (solo BOZZA, dialog DatePicker valido_dal/al)
//         - Clona     (qualunque stato, crea nuova BOZZA)
//         - Elimina   (solo BOZZA, confirm dialog)
//
//        Editor HTML/CSS/markdown: textarea base. v1 senza editor
//        visuale (Decisione 9 esplicita: fuori scope).
//
// ⭐ LA FORMA DEI DATI (2026-09-30, brief-db-documenti-versione-contesto-
//    template): ogni versione dichiara la forma che legge
//    (`versione_contesto`, obbligatoria, modificabile solo in BOZZA). La forma
//    che il sistema produce oggi la dice il backend nel dettaglio del template
//    (`versione_contesto_builder`): qui si MOSTRA e precompila la nuova
//    versione, non si confronta — chi rifiuta pubblicazione e stampa e' il
//    database, con la sua frase.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useTemplateVersioniStore } from '../stores/templateVersioni'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useDrawerTabLista } from '../../core/composables/useDrawerTabLista'
// `useConfirmAction` espone `confirmAction` (signature object con
// `onAccept` callback). Memoria feedback_useconfirmaction_destructuring:
// usare destructured + nome callback `onAccept` (non `accept`) per
// evitare dialog silente.
import { MANAGE_ICONS } from '../../core/constants'
import { parseIsoDate, toDateString } from '../../core/utils/date'
import {
  FORMATI_TEMPLATE,
  PAGE_FORMATS,
  PAGE_ORIENTATIONS,
} from '../constants/documentiVersioniWhitelists'
import DrawerTabLista from '../../core/components/DrawerTabLista.vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Textarea from 'primevue/textarea'
import Select from 'primevue/select'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'
import Button from 'primevue/button'
import AppDialog from '../../core/components/AppDialog.vue'
import Message from 'primevue/message'
import LookupSelect from '../../core/components/LookupSelect.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'

const props = defineProps({
  templateId: { type: Number, required: true },
  // L'emittente del template (PK `emittenti_fiscali`, NOT NULL a modello):
  // la lista lo gira al cancello di perimetro, perche' il super admin su
  // «Tutti» non debba scegliere l'emittente del template che ha gia' aperto.
  emittenteFiscaleId: { type: [Number, null], default: null },
  // La forma dei dati che il builder del template produce oggi
  // (`versione_contesto_builder` del dettaglio). `null` = builder non
  // registrato, o dettaglio non ancora letto.
  versioneContestoBuilder: { type: [Number, null], default: null },
  readonly: { type: Boolean, default: false },
})

// `form-aperto` segnala al drawer padre se il form inline di versione e'
// attivo (create/edit). Il padre nasconde la propria FormFooter per
// evitare doppi pulsanti di Salva/Annulla — pattern di
// `PreventiviRigheTable`/`PreventiviDrawer` (memoria
// feedback_master_detail_inline).
const emit = defineEmits(['form-aperto'])

const { t } = useI18n()
const store = useTemplateVersioniStore()
const { execute, loading, campiErrati } = useApiHandler()
const { confirmAction } = useConfirmAction()

const formatOptions = computed(() => PAGE_FORMATS.map(v => ({ label: v, value: v })))
const orientationOptions = computed(() =>
  PAGE_ORIENTATIONS.map(v => ({
    label: t(`config.modelli_documenti.versioni.orientation_${v.toLowerCase()}`),
    value: v,
  })),
)
const formatoTemplateOptions = computed(() =>
  FORMATI_TEMPLATE.map(v => ({ label: v, value: v })),
)

// Stato form inline.
const editing = ref(false)
const editingVersioneId = ref(null)
const isNew = computed(() => editing.value && editingVersioneId.value === null)

// Propaga al drawer padre l'apertura del form (per nascondere la sua
// FormFooter durante create/edit versione).
watch(editing, (v) => emit('form-aperto', v))

const form = ref(emptyForm())
// Modifiche non salvate del form versione. La sezione vive solo dentro il
// drawer aperto (il Drawer la smonta alla chiusura): basta il form aperto.
// `modificato` e `chiudiConConferma` vanno al drawer padre, che possiede la
// chiusura (X/ESC/clic fuori).
const { fissa, modificato, chiudiConConferma } =
  useDrawerFormPreserve(form, { visibile: () => editing.value })
defineExpose({ modificato, chiudiConConferma })
function emptyForm() {
  return {
    titolo: '',
    formato_template: 'HTML',
    html_template: '',
    css_template: '',
    markdown_template: '',
    render_engine_id: null,
    // Precompilata con la forma di oggi: e' una proposta a video, l'operatore
    // la vede e la conferma col salvataggio (il backend non ha default).
    versione_contesto: props.versioneContestoBuilder,
    page_format: 'A4',
    page_orientation: 'PORTRAIT',
    margin_top_mm: 15,
    margin_right_mm: 15,
    margin_bottom_mm: 15,
    margin_left_mm: 15,
    valido_dal: null,
    valido_al: null,
    attivo: true,
  }
}

// Pubblica dialog state.
const pubblicaDialog = ref(false)
const pubblicaTargetId = ref(null)
const pubblicaForm = ref({ valido_dal: null, valido_al: null })
// La forma letta dalla versione che si sta pubblicando, per mostrarla accanto
// a quella del sistema nel dialog.
const pubblicaFormaVersione = ref(null)

// Il padre e' il template: al cambio, lo scaffolding scrive l'id nello store,
// azzera pagina e ricerca e ricarica. Il «Nuovo» sta nella barra della lista,
// spento in sola lettura e mentre il form e' aperto.
const {
  searchText, onPage, onSort, paginatorProps, tablePage,
  listaRef, dirty, onConfigLoaded, pageActions, perimetroBloccato, reloadAll,
} = useDrawerTabLista(store, {
  // Il padre composto: il template e il suo emittente (vedi lo store).
  parentId: {
    templateId: () => props.templateId,
    emittenteId: () => props.emittenteFiscaleId,
  },
  searchTableOptions: { defaultSortField: 'versione', defaultSortOrder: 'desc' },
  extraActions: () => [{
    key: 'new-versione',
    kind: 'primary',
    label: t('common.new'),
    tooltip: t('config.modelli_documenti.versioni.new'),
    icon: MANAGE_ICONS.ADD,
    visible: !props.readonly && !editing.value,
    command: openCreate,
  }],
})

// Al cambio template il form aperto sul template precedente si chiude.
watch(() => props.templateId, () => closeForm())

async function reload() {
  await reloadAll()
}

function statoSeverity(stato) {
  if (stato === 'PUBBLICATA') return 'success'
  if (stato === 'OBSOLETA') return 'secondary'
  return 'info'  // BOZZA
}

function buildRowActions(row) {
  if (props.readonly) return []
  const actions = []
  if (row.stato === 'BOZZA') {
    actions.push({
      key: 'pubblica',
      label: t('config.modelli_documenti.versioni.action_pubblica'),
      icon: MANAGE_ICONS.PUBLISH,
      severity: 'primary',
      command: () => openPubblicaDialog(row),
    })
  }
  actions.push({
    key: 'clona',
    label: t('config.modelli_documenti.versioni.action_clona'),
    icon: MANAGE_ICONS.CLONE,
    severity: 'info',
    command: () => clonaVersione(row),
  })
  if (row.stato === 'BOZZA') {
    actions.push({
      key: 'delete',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      command: () => confirmDeleteVersione(row),
    })
  }
  return actions
}

async function openCreate() {
  editingVersioneId.value = null
  form.value = emptyForm()
  editing.value = true
  fissa()
}

async function openEdit(row) {
  if (row.stato !== 'BOZZA') return
  const data = await store.fetchDetail(props.templateId, row.id)
  editingVersioneId.value = row.id
  form.value = {
    titolo: data.titolo ?? '',
    formato_template: data.formato_template ?? 'HTML',
    html_template: data.html_template ?? '',
    css_template: data.css_template ?? '',
    markdown_template: data.markdown_template ?? '',
    render_engine_id: data.render_engine_id ?? null,
    versione_contesto: data.versione_contesto ?? null,
    page_format: data.page_format ?? 'A4',
    page_orientation: data.page_orientation ?? 'PORTRAIT',
    margin_top_mm: data.margin_top_mm ?? 15,
    margin_right_mm: data.margin_right_mm ?? 15,
    margin_bottom_mm: data.margin_bottom_mm ?? 15,
    margin_left_mm: data.margin_left_mm ?? 15,
    // Helper condivisi `date.js` (parseIsoDate) per evitare timezone shift
    // su stringhe ISO date-only.
    valido_dal: parseIsoDate(data.valido_dal),
    valido_al: parseIsoDate(data.valido_al),
    attivo: data.attivo ?? true,
  }
  editing.value = true
  fissa()
}

function closeForm() {
  editing.value = false
  editingVersioneId.value = null
  form.value = emptyForm()
}

function toNumberOrNull(value) {
  if (value === null || value === undefined || value === '') return null
  const n = Number(value)
  return Number.isFinite(n) ? n : value
}

const canSaveForm = computed(() => {
  if (props.readonly) return false
  const f = form.value
  if (!f.titolo?.trim()) return false
  if (!f.render_engine_id) return false
  if (!f.versione_contesto) return false
  return true
})

async function saveForm() {
  const f = form.value
  const payload = {
    titolo: f.titolo.trim(),
    formato_template: f.formato_template,
    html_template: f.html_template || null,
    css_template: f.css_template || null,
    markdown_template: f.markdown_template || null,
    render_engine_id: f.render_engine_id,
    versione_contesto: f.versione_contesto,
    page_format: f.page_format,
    page_orientation: f.page_orientation,
    margin_top_mm: toNumberOrNull(f.margin_top_mm),
    margin_right_mm: toNumberOrNull(f.margin_right_mm),
    margin_bottom_mm: toNumberOrNull(f.margin_bottom_mm),
    margin_left_mm: toNumberOrNull(f.margin_left_mm),
    valido_dal: toDateString(f.valido_dal),
    valido_al: toDateString(f.valido_al),
    attivo: f.attivo,
  }
  const result = await execute(
    () => isNew.value
      ? store.create(props.templateId, payload)
      : store.update(props.templateId, editingVersioneId.value, payload),
    { successMessage: t('config.modelli_documenti.versioni.saved') },
  )
  if (result !== null) {
    await reload()
    closeForm()
  }
}

async function clonaVersione(row) {
  const result = await execute(
    () => store.clona(props.templateId, row.id, {}),
    { successMessage: t('config.modelli_documenti.versioni.cloned') },
  )
  if (result !== null) {
    await reload()
  }
}

function confirmDeleteVersione(row) {
  confirmAction({
    header: t('common.delete'),
    message: t('config.modelli_documenti.versioni.confirm_delete', {
      versione: row.versione,
    }),
    danger: true,
    onAccept: async () => {
      await execute(
        () => store.destroy(props.templateId, row.id),
        { successMessage: t('config.modelli_documenti.versioni.deleted') },
      )
      await reload()
    },
  })
}

function openPubblicaDialog(row) {
  pubblicaTargetId.value = row.id
  pubblicaFormaVersione.value = row.versione_contesto ?? null
  pubblicaForm.value = {
    valido_dal: parseIsoDate(row.valido_dal) || new Date(),
    valido_al: parseIsoDate(row.valido_al),
  }
  pubblicaDialog.value = true
}

async function confirmPubblica() {
  if (!pubblicaForm.value.valido_dal) return
  const payload = {
    valido_dal: toDateString(pubblicaForm.value.valido_dal),
    valido_al: toDateString(pubblicaForm.value.valido_al),
  }
  const result = await execute(
    () => store.pubblica(props.templateId, pubblicaTargetId.value, payload),
    { successMessage: t('config.modelli_documenti.versioni.published') },
  )
  if (result !== null) {
    pubblicaDialog.value = false
    await reload()
  }
}
</script>

<template>
  <div class="template-versioni-section">
    <div class="section-header">
      <h3>{{ t('config.modelli_documenti.versioni.title') }}</h3>
    </div>

    <!-- `v-show` e non `v-if`: col form aperto la lista si nasconde ma resta
         montata — configurazione, pagina e ricerca non si rileggono a ogni
         apertura del form. -->
    <DrawerTabLista
      v-show="!editing"
      ref="listaRef"
      codice="documenti.template_versioni"
      :emittente-esplicito="emittenteFiscaleId"
      :store="store"
      :rows="store.items"
      :total="store.totalRecords"
      :loading="store.loading"
      :paginator-options="paginatorProps"
      :page="tablePage"
      :sort-field="paginatorProps.sortField"
      :sort-order="paginatorProps.sortOrder"
      :page-actions="pageActions"
      :dirty="dirty"
      :perimetro-bloccato="perimetroBloccato"
      @page="onPage"
      @sort="onSort"
      @row-click="openEdit"
      @config-loaded="onConfigLoaded"
    >
      <template #filtri-sempre>
        <InputText
          v-model="searchText"
          class="app-filter-w-lg"
          :placeholder="t('config.modelli_documenti.versioni.search_placeholder')"
        />
      </template>
      <template #cell-stato="{ data }">
        <Tag :value="data.stato" :severity="statoSeverity(data.stato)" />
      </template>
      <template #cell-attivo="{ data }">
        <AttivoTag :active="data.attivo" />
      </template>
      <template v-if="!props.readonly" #actions="{ data }">
        <RowActionsMenu :row="data" :actions="buildRowActions(data)" />
      </template>
    </DrawerTabLista>

    <div v-if="editing" class="form-grid mt-1">
      <Message severity="info" :closable="false">
        {{ isNew
          ? t('config.modelli_documenti.versioni.creating_hint')
          : t('config.modelli_documenti.versioni.editing_hint') }}
      </Message>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_titolo') }} *</label>
        <InputText v-model="form.titolo" :disabled="props.readonly" maxlength="255"
          :invalid="campiErrati.includes('titolo')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_render_engine') }} *</label>
        <LookupSelect
          v-model="form.render_engine_id"
          rel="documenti.render_engine_documento"
          :placeholder="t('config.modelli_documenti.versioni.field_render_engine_placeholder')"
          :disabled="props.readonly"
        />
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_versione_contesto') }} *</label>
        <InputNumber v-model="form.versione_contesto" :disabled="props.readonly"
          :min="1" :use-grouping="false"
          :invalid="campiErrati.includes('versione_contesto')"
        />
        <small v-if="props.versioneContestoBuilder" class="app-text-muted">
          {{ t('config.modelli_documenti.versioni.versione_contesto_hint', {
            forma: props.versioneContestoBuilder,
          }) }}
        </small>
        <small v-else class="app-text-muted">
          {{ t('config.modelli_documenti.versioni.versione_contesto_builder_assente') }}
        </small>
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_formato') }}</label>
        <Select
          v-model="form.formato_template"
          :options="formatoTemplateOptions"
          option-label="label"
          option-value="value"
          :disabled="props.readonly"
          :invalid="campiErrati.includes('formato_template')"
        />
      </div>
      <div class="form-field form-field-wide">
        <label>{{ t('config.modelli_documenti.versioni.field_html') }}</label>
        <Textarea v-model="form.html_template" :disabled="props.readonly" rows="10" auto-resize
          :invalid="campiErrati.includes('html_template')"
        />
      </div>
      <div class="form-field form-field-wide">
        <label>{{ t('config.modelli_documenti.versioni.field_css') }}</label>
        <Textarea v-model="form.css_template" :disabled="props.readonly" rows="6" auto-resize
          :invalid="campiErrati.includes('css_template')"
        />
      </div>
      <div class="form-field form-field-wide">
        <label>{{ t('config.modelli_documenti.versioni.field_markdown') }}</label>
        <Textarea v-model="form.markdown_template" :disabled="props.readonly" rows="6" auto-resize
          :invalid="campiErrati.includes('markdown_template')"
        />
      </div>

      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_page_format') }}</label>
        <Select
          v-model="form.page_format"
          :options="formatOptions"
          option-label="label"
          option-value="value"
          :disabled="props.readonly"
          :invalid="campiErrati.includes('page_format')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_page_orientation') }}</label>
        <Select
          v-model="form.page_orientation"
          :options="orientationOptions"
          option-label="label"
          option-value="value"
          :disabled="props.readonly"
          :invalid="campiErrati.includes('page_orientation')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_margin_top') }}</label>
        <InputNumber v-model="form.margin_top_mm" :disabled="props.readonly" :min="0" :max="100" />
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_margin_right') }}</label>
        <InputNumber v-model="form.margin_right_mm" :disabled="props.readonly" :min="0" :max="100" />
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_margin_bottom') }}</label>
        <InputNumber v-model="form.margin_bottom_mm" :disabled="props.readonly" :min="0" :max="100" />
      </div>
      <div class="form-field">
        <label>{{ t('config.modelli_documenti.versioni.field_margin_left') }}</label>
        <InputNumber v-model="form.margin_left_mm" :disabled="props.readonly" :min="0" :max="100" />
      </div>
      <div class="form-field">
        <label>{{ t('common.attivo') }}</label>
        <ToggleSwitch v-model="form.attivo" :disabled="props.readonly"
          :invalid="campiErrati.includes('attivo')"
        />
      </div>

      <div class="form-actions">
        <Button
          :label="t('common.cancel')"
          severity="secondary"
          @click="chiudiConConferma(closeForm)"
          :disabled="loading"
        />
        <Button
          :label="t('common.save')"
          :icon="MANAGE_ICONS.CONFIRM"
          :disabled="!canSaveForm"
          :loading="loading"
          @click="saveForm"
        />
      </div>
    </div>

    <AppDialog
      v-model:visible="pubblicaDialog"
      :header="t('config.modelli_documenti.versioni.publish_title')"
      width="sm"
      :loading="loading"
      :save-disabled="!pubblicaForm.valido_dal"
      :save-label="t('config.modelli_documenti.versioni.action_pubblica')"
      @save="confirmPubblica"
    >
      <div class="form-grid">
        <Message severity="warn" :closable="false">
          {{ t('config.modelli_documenti.versioni.publish_hint') }}
        </Message>
        <Message v-if="pubblicaFormaVersione && props.versioneContestoBuilder"
          severity="info" :closable="false">
          {{ t('config.modelli_documenti.versioni.publish_forma', {
            versione: pubblicaFormaVersione,
            builder: props.versioneContestoBuilder,
          }) }}
        </Message>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_valido_dal') }} *</label>
          <DatePicker v-model="pubblicaForm.valido_dal" date-format="dd/mm/yy"
            :invalid="campiErrati.includes('valido_dal')" />
        </div>
        <div class="form-field">
          <label>{{ t('config.modelli_documenti.versioni.field_valido_al') }}</label>
          <DatePicker v-model="pubblicaForm.valido_al" date-format="dd/mm/yy" show-icon
            :invalid="campiErrati.includes('valido_al')" />
        </div>
      </div>
    </AppDialog>
  </div>
</template>

<style scoped>
.template-versioni-section .section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}
.template-versioni-section .form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
}
</style>

<script setup>
// Scopo: Sub-drawer gestione righe contratto — pattern master-detail inline.
//        Lista paginata sopra (10 righe/pagina), form dettaglio sotto.
//        Click riga = edit, pulsante Nuovo = create, Salva/Annulla sempre in basso.
//        Modalita' C: prezzo_unitario obbligatorio su tutte le righe.
//        Modalita' B: opzionale (solo se serve override).
//        Modalita' A: di norma non necessarie (solo override puntuali).
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContrattiStore } from '../stores/contratti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { DRAWER_WIDTH } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { statoContrattoSeverity } from '../../core/utils/severity'
import { useArticoloUomOptions } from '../../core/composables/useArticoloUomOptions'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import Drawer from 'primevue/drawer'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Select from 'primevue/select'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import Message from 'primevue/message'
import NewButton from '../../core/components/NewButton.vue'
import ReloadButton from '../../core/components/ReloadButton.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'

const { t } = useI18n()
const store = useContrattiStore()
const { execute, loading } = useApiHandler()
const { confirmDelete } = useConfirmAction()
const isReadonly = useInjectReadonly()

const props = defineProps({
  visible: Boolean,
  contrattoId: { type: Number, required: true },
  contrattoModalita: { type: String, default: 'B' },
  righeIniziali: { type: Array, default: () => [] },
  // Contesto contratto (per intestazione riepilogativa)
  contrattoNumero: { type: String, default: '' },
  contrattoCliente: { type: String, default: '' },
  contrattoValidoDal: { type: String, default: '' },
  contrattoValidoAl: { type: String, default: null },
  contrattoStatoCodice: { type: String, default: '' },
  contrattoStatoDescrizione: { type: String, default: '' },
})
const emit = defineEmits(['update:visible', 'changed'])

const righe = ref([])

// === Preview righe applicate (modalita' A/B) ===
// previewMeta: testata sintetica (modalita derivata, listino, variazione)
// previewRighe: lista preview (origine='DA_LISTINO' o 'OVERRIDE')
const previewMeta = ref(null)
const previewRighe = ref([])
const previewLoading = ref(false)

// In modalita' A/B la lista visualizzata e' la preview (combinata override
// + da_listino), in modalita' C resta la lista contratti_righe diretta.
// La modalita' usata per le decisioni di rendering e` quella derivata dal
// BE (previewMeta.modalita) se disponibile, altrimenti la prop
// contrattoModalita di fallback.
const modalitaEffettiva = computed(() => previewMeta.value?.modalita || props.contrattoModalita)
const isModalitaC = computed(() => modalitaEffettiva.value === 'C')

// Filtro full-text articolo (codice + descrizione, case-insensitive).
// Applicato client-side: la lista preview e' gia' paginata nel DataTable
// e tipicamente sotto le 100-200 righe per listino. Per liste massive
// si potrebbe muovere il filtro server-side (param query string) — per
// ora MVP client.
const filtroArticolo = ref('')

// Lista renderizzata. In A/B arricchiamo con `_row_key` sintetico univoco
// (articolo_id + uom_id): un articolo con piu' UoM nel listino genera
// piu' righe preview con stesso articolo_id, quindi articolo_id da solo
// non e' un dataKey valido per il DataTable (PrimeVue v-model:selection
// confonderebbe le righe). In C il dataKey resta `id` (PK contratti_righe).
const righeView = computed(() => {
  const filtro = (filtroArticolo.value || '').trim().toLowerCase()
  const matchFiltro = (r) => {
    if (!filtro) return true
    const codice = (r.articolo_codice || '').toLowerCase()
    const desc = (r.articolo_descrizione || '').toLowerCase()
    return codice.includes(filtro) || desc.includes(filtro)
  }
  if (isModalitaC.value) {
    return righe.value.filter(matchFiltro)
  }
  return (previewRighe.value || [])
    .filter(matchFiltro)
    .map(r => ({
      ...r,
      _row_key: `${r.articolo_id}__${r.uom_id ?? 'null'}`,
    }))
})

// Scopo: classe CSS sulla riga DataTable. In readonly (permessi LETTURA o
// contratto post-DRAFT) tutte le righe sono visualmente readonly. In edit
// le righe con origine='DA_LISTINO' restano readonly perche' preview pure
// senza record contratti_righe dietro. Coerente col guard BE Profilo A.
function rowClass(data) {
  if (isReadonly.value) return 'app-row-readonly'
  if (data?.origine === 'DA_LISTINO') return 'app-row-readonly'
  return null
}

async function loadPreview() {
  if (!props.contrattoId) return
  if (props.contrattoModalita === 'C') {
    previewMeta.value = { modalita: 'C', righe: [] }
    previewRighe.value = []
    return
  }
  previewLoading.value = true
  try {
    const data = await store.fetchRighePreview(props.contrattoId)
    previewMeta.value = data
    previewRighe.value = data?.righe || []
  } catch {
    previewMeta.value = null
    previewRighe.value = []
  } finally {
    previewLoading.value = false
  }
}

// Reload completo: in modalita' A/B ricarica la preview dal BE; in modalita'
// C la lista contratti_righe viene rinfrescata dal parent (emit changed).
// Usato sia dal pulsante Ricarica sia dallo shortcut F5 globale.
async function reloadList() {
  if (!props.visible) return
  if (isModalitaC.value) {
    emit('changed')
  } else {
    await loadPreview()
  }
}

// Shortcut F5: ricarica la lista senza reload del browser. Coerente con
// il pattern useSearchTable usato dalle liste main. Attivo solo quando
// il drawer e' visibile (registrato in onMounted, deregistrato in onUnmounted
// — il drawer e' un componente persistente, non viene smontato a chiusura).
function onKeydown(e) {
  if (e.key === 'F5' && props.visible) {
    e.preventDefault()
    reloadList()
  }
}
onMounted(() => { window.addEventListener('keydown', onKeydown) })
onUnmounted(() => { window.removeEventListener('keydown', onKeydown) })

// === Form state ===
// formMode: null (nessun form), 'create', 'edit'
const formMode = ref(null)
const rigaEditId = ref(null)
const form = ref({})
const selectedRow = ref(null)

// === UoM operative dell'articolo selezionato ===
// Composable centralizzato (Fase 4.F1). Autopick base se il form e' attivo
// (create OR edit con UoM mancante) — replica l'esatto criterio originale.
const {
  uomOptions, uomLoading, loadUomPerArticolo, pickBaseUomId, resetUomOptions,
} = useArticoloUomOptions()

function uomLabel(item) {
  return item.is_base ? `${item.uom_codice} (base)` : item.uom_codice
}

async function caricaUomConPickBase(articoloId) {
  const list = await loadUomPerArticolo(articoloId)
  if (formMode.value && !form.value.uom_operativa_id) {
    form.value.uom_operativa_id = pickBaseUomId(list)
  }
}

// === Options ===
const tipoErogazioneOptions = computed(() => [
  { value: 'CANONE', label: t('contratti.tipo_erogazione_canone') },
  { value: 'CONSUMO', label: t('contratti.tipo_erogazione_consumo') },
  { value: 'UNA_TANTUM', label: t('contratti.tipo_erogazione_una_tantum') },
])

function defaultForm() {
  return {
    articolo_id: null,
    articolo_obj: null,
    tipo_erogazione: 'CANONE',
    prezzo_unitario: null,
    qta_operativa: 1,
    uom_operativa_id: null,
    ordine: 10,
  }
}

// === Lifecycle ===
watch(() => props.visible, (v) => {
  if (v) {
    righe.value = [...(props.righeIniziali || [])]
    closeForm()
    loadPreview()
  }
})

watch(() => props.righeIniziali, (v) => {
  righe.value = [...(v || [])]
}, { deep: true })

// === Azioni ===
function onNew() {
  form.value = defaultForm()
  formMode.value = 'create'
  rigaEditId.value = null
  selectedRow.value = null
  resetUomOptions()
}

function onRowSelect(event) {
  const r = event.data
  // In readonly (permessi area LETTURA o contratto post-DRAFT) il click su
  // una riga NON apre il form di modifica. La selezione resta consultabile
  // visivamente solo per evidenziare la riga letta. Coerente con il guard
  // BE Profilo A che rifiuta update_riga su contratti non-DRAFT.
  if (isReadonly.value) {
    selectedRow.value = null
    return
  }
  // In modalita' A/B la lista mostra la preview combinata: le righe con
  // origine='DA_LISTINO' sono readonly (preview puro) e non aprono il form.
  // Solo le righe 'OVERRIDE' (con id contratti_righe) sono editabili.
  if (r.origine === 'DA_LISTINO') {
    // Reset selezione e form: evita evidenziamento residuo PrimeVue e
    // disallinea form-mode aperto su altra riga.
    selectedRow.value = null
    if (formMode.value) closeForm()
    return
  }
  // ID dipende dalla modalita': in A/B usa override_riga_id (preview),
  // in C usa r.id (riga contratto persistita).
  const rigaId = r.id ?? r.override_riga_id
  form.value = {
    articolo_id: r.articolo_id,
    articolo_obj: { id: r.articolo_id, codice: r.articolo_codice, descrizione: r.articolo_descrizione, _display: `${r.articolo_codice} — ${r.articolo_descrizione}` },
    tipo_erogazione: r.tipo_erogazione || 'CANONE',
    prezzo_unitario: (r.prezzo_unitario ?? r.override_prezzo) != null
      ? Number(r.prezzo_unitario ?? r.override_prezzo)
      : null,
    qta_operativa: r.qta_operativa != null ? Number(r.qta_operativa) : 1,
    uom_operativa_id: r.uom_operativa_id ?? r.uom_id,
    ordine: r.ordine || 10,
  }
  formMode.value = 'edit'
  rigaEditId.value = rigaId
  // Edit con UoM pre-popolata dalla riga: niente autopick, solo fetch.
  loadUomPerArticolo(r.articolo_id)
}

function onArticoloSelected(item) {
  form.value.articolo_id = item?.id || null
  form.value.uom_operativa_id = null
  // Cambio articolo in form aperto: autopick base.
  caricaUomConPickBase(item?.id)
}

function closeForm() {
  formMode.value = null
  rigaEditId.value = null
  form.value = {}
  selectedRow.value = null
  resetUomOptions()
}

// === Validazione ===
const canSave = computed(() => {
  if (isReadonly.value) return false
  if (!formMode.value) return false
  if (!form.value.articolo_id) return false
  if (!form.value.uom_operativa_id) return false
  if (props.contrattoModalita === 'C' && (form.value.prezzo_unitario == null || form.value.prezzo_unitario === '')) return false
  return true
})

const formTitle = computed(() => {
  if (formMode.value === 'create') return t('contratti.nuova_riga')
  if (formMode.value === 'edit') return t('contratti.modifica_riga')
  return ''
})

// === Salvataggio ===
async function onSave() {
  const f = form.value
  const payload = {
    tipo_erogazione: f.tipo_erogazione || null,
    prezzo_unitario: f.prezzo_unitario != null ? String(f.prezzo_unitario) : null,
    qta_operativa: f.qta_operativa != null ? String(f.qta_operativa) : '1',
    uom_operativa_id: f.uom_operativa_id || null,
    ordine: f.ordine != null ? Number(f.ordine) : null,
  }
  if (formMode.value === 'create') {
    payload.articolo_id = f.articolo_id
    const result = await execute(
      () => store.addRiga(props.contrattoId, payload),
      { successMessage: t('contratti.riga_creata') }
    )
    if (result !== null) {
      if (!isModalitaC.value) await loadPreview()
      emit('changed')
      closeForm()
    }
  } else {
    const result = await execute(
      () => store.updateRiga(props.contrattoId, rigaEditId.value, payload),
      { successMessage: t('contratti.riga_salvata') }
    )
    if (result !== null) {
      if (!isModalitaC.value) await loadPreview()
      emit('changed')
      closeForm()
    }
  }
}

function onDelete(r) {
  // ID contratti_righe: in C sta in r.id, in B (preview) sta in r.override_riga_id.
  const rigaId = r.id ?? r.override_riga_id
  const label = r.articolo_codice || r.articolo_descrizione || `#${rigaId}`
  confirmDelete(label, async () => {
    const result = await execute(
      () => store.deleteRiga(props.contrattoId, rigaId),
      { successMessage: t('contratti.riga_eliminata') }
    )
    if (result !== null) {
      // Se stavo editando questa riga, chiudi il form.
      if (rigaEditId.value === rigaId) closeForm()
      // In A/B la preview va ricaricata; in C il parent rilegge dalle righe.
      if (!isModalitaC.value) await loadPreview()
      emit('changed')
    }
  })
}

function onClose() {
  emit('update:visible', false)
}

// Scopo: azioni di riga per il master-detail righe contratto.
//        Le righe con origine='DA_LISTINO' (preview puro, no contratti_righe)
//        non hanno azioni: sono readonly. Le OVERRIDE (B) e le righe puro
//        contratto (C) ammettono delete in non-readonly.
function buildRigaActions(data) {
  if (data.origine === 'DA_LISTINO') return []
  return [
    {
      key: 'elimina-riga',
      label: t('common.delete'),
      icon: 'pi pi-trash',
      severity: 'danger',
      visible: !isReadonly.value,
      command: () => onDelete(data),
    },
  ]
}

// Scopo: severity Tag per origine riga (DA_LISTINO=neutra, OVERRIDE=primary).
function origineSeverity(origine) {
  if (origine === 'OVERRIDE') return 'info'
  if (origine === 'DA_LISTINO') return 'secondary'
  return null
}
</script>

<template>
  <Drawer
    :visible="props.visible"
    @update:visible="val => emit('update:visible', val)"
    position="right"
    :style="{ width: DRAWER_WIDTH.WIDE }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle :title="t('contratti.drawer_righe_titolo')" icon="pi pi-list" />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- === Intestazione contesto contratto === -->
      <div v-if="contrattoStatoCodice" style="text-align: right;" class="mb-2">
        <Tag :value="contrattoStatoDescrizione"
          :severity="statoContrattoSeverity(contrattoStatoCodice)" />
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('contratti.field_numero') }}</label>
          <span class="font-bold">{{ contrattoNumero }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('contratti.col_ba') }}</label>
          <span>{{ contrattoCliente }}</span>
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('contratti.col_valido_dal') }}</label>
          <span>{{ displayDate(contrattoValidoDal) }}</span>
        </div>
        <div class="form-field">
          <label>{{ t('contratti.col_valido_al') }}</label>
          <span>{{ contrattoValidoAl ? displayDate(contrattoValidoAl) : '—' }}</span>
        </div>
      </div>

      <!-- Avviso modalita' C: tutte le righe sono custom, prezzo obbligatorio -->
      <Message v-if="modalitaEffettiva === 'C'" severity="warn" :closable="false" size="small">
        {{ t('contratti.righe_c_warn') }}
      </Message>

      <!-- Banner contesto preview modalita' A/B: riassume listino + variazione -->
      <Message v-else-if="previewMeta?.listino_codice"
        severity="info" :closable="false" size="small">
        <div>
          <strong>{{ t('contratti.preview_modalita', { mod: previewMeta.modalita }) }}</strong>:
          {{ t('contratti.preview_listino', { codice: previewMeta.listino_codice }) }}
          <span v-if="previewMeta.tipo_variazione_globale">
            — {{ t('contratti.preview_variazione', {
              tipo: previewMeta.tipo_variazione_globale,
              valore: previewMeta.valore_variazione_globale,
            }) }}
          </span>
        </div>
        <div class="text-sm">{{ t('contratti.preview_hint') }}</div>
      </Message>

      <!-- Avviso: listino associato ma senza versione operativa oggi.
           La preview e` vuota legittimamente, l'operatore deve attivare
           una versione del listino prima che il pricing sia calcolato. -->
      <Message v-if="previewMeta?.listino_senza_versione_oggi"
        severity="warn" :closable="false" size="small">
        {{ t('contratti.preview_listino_senza_versione', {
          codice: previewMeta.listino_codice || ''
        }) }}
      </Message>

      <!-- === MASTER: toolbar + lista paginata === -->
      <div class="app-page-toolbar">
        <div class="app-page-filters">
          <InputText v-model="filtroArticolo"
            :placeholder="t('contratti.filtro_articolo_placeholder')"
            style="min-width: 240px;" />
        </div>
        <div class="app-page-actions">
          <ReloadButton @click="reloadList" />
          <NewButton :tooltip="t('contratti.aggiungi_riga')"
            @click="onNew" :disabled="formMode === 'create' || isReadonly" />
        </div>
      </div>

      <DataTable
        :value="righeView"
        v-model:selection="selectedRow"
        :loading="previewLoading"
        selection-mode="single"
        :data-key="isModalitaC ? 'id' : '_row_key'"
        :row-class="rowClass"
        class="app-datatable"
        striped-rows
        paginator
        :rows="10"
        :rows-per-page-options="[10, 25, 50]"
        paginator-position="top"
        sort-field="articolo_descrizione"
        :sort-order="1"
        removable-sort
        @row-select="onRowSelect"
      >
        <Column field="articolo_codice" :header="t('contratti.col_articolo')" sortable style="width: 150px;" />
        <Column field="articolo_descrizione" :header="t('contratti.col_descrizione')" sortable />
        <Column :header="t('contratti.col_uom')" style="width: 80px;">
          <template #body="{ data }">{{ data.uom_codice ?? '—' }}</template>
        </Column>
        <!-- Modalita' C: prezzo singolo. A/B: prezzo listino + prezzo finale + origine. -->
        <template v-if="isModalitaC">
          <Column field="prezzo_unitario" :header="t('contratti.col_prezzo')" style="width: 90px;">
            <template #body="{ data }">{{ data.prezzo_unitario ?? '—' }}</template>
          </Column>
          <Column field="qta_operativa" :header="t('contratti.col_qta')" style="width: 70px;" />
          <Column field="tipo_erogazione" :header="t('contratti.col_tipo_erogazione')" style="width: 100px;" />
        </template>
        <template v-else>
          <Column :header="t('contratti.col_prezzo_listino')" style="width: 110px;">
            <template #body="{ data }">{{ data.prezzo_listino ?? '—' }}</template>
          </Column>
          <Column :header="t('contratti.col_prezzo_finale')" style="width: 110px;">
            <template #body="{ data }">
              <span class="font-bold">{{ data.prezzo_finale ?? '—' }}</span>
            </template>
          </Column>
          <Column :header="t('contratti.col_origine')" style="width: 110px;">
            <template #body="{ data }">
              <Tag :value="t(`contratti.origine_${data.origine?.toLowerCase()}`)"
                :severity="origineSeverity(data.origine)" />
            </template>
          </Column>
        </template>
        <Column :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
          <template #body="{ data }">
            <RowActionsMenu :row="data" :actions="buildRigaActions(data)" />
          </template>
        </Column>
      </DataTable>

      <!-- === DETAIL: form inserimento/modifica === -->
      <template v-if="formMode">
        <div class="app-drawer-section">
          <h4>{{ formTitle }}</h4>
        </div>

        <div class="form-field">
          <label>{{ t('contratti.field_articolo') }} *</label>
          <ArticoloLookup
            v-model="form.articolo_obj"
            @update:modelValue="onArticoloSelected"
            :disabled="formMode === 'edit'"
            :placeholder="t('contratti.select_articolo')"
          />
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('contratti.field_uom') }} *</label>
            <Select v-model="form.uom_operativa_id"
              :options="uomOptions"
              option-value="uom_id"
              :option-label="uomLabel"
              :placeholder="form.articolo_id ? t('contratti.select_uom') : t('contratti.uom_select_articolo_first')"
              :disabled="!form.articolo_id || uomLoading"
              :loading="uomLoading"
              class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('contratti.field_tipo_erogazione') }}</label>
            <Select v-model="form.tipo_erogazione" :options="tipoErogazioneOptions"
              option-label="label" option-value="value" class="w-full" />
          </div>
        </div>

        <div class="form-grid-2col">
          <div class="form-field">
            <label>
              {{ t('contratti.field_prezzo_unitario') }}
              <span v-if="contrattoModalita === 'C'">*</span>
            </label>
            <InputNumber v-model="form.prezzo_unitario" class="w-full"
              :min-fraction-digits="2" :max-fraction-digits="4" showButtons />
          </div>
          <div class="form-field">
            <label>{{ t('contratti.field_qta_operativa') }} *</label>
            <InputNumber v-model="form.qta_operativa" class="w-full"
              :min="0.0001" :min-fraction-digits="0" :max-fraction-digits="4" showButtons />
          </div>
        </div>

        <div class="form-field">
          <label>{{ t('contratti.field_ordine') }}</label>
          <InputNumber v-model="form.ordine" class="w-full" :min="0" />
        </div>

        <div class="app-drawer-footer">
          <Button :label="t('common.cancel')" severity="secondary" @click="closeForm" />
          <Button :label="t('common.save')" :disabled="!canSave || loading" :loading="loading" @click="onSave" />
        </div>
      </template>

      <DrawerFooter close-only @cancel="onClose" />
    </div>
  </Drawer>
</template>

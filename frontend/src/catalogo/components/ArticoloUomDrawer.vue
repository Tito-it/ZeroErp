<script setup>
// Scopo: Sub-drawer per gestione UoM operative articolo.
// Pattern: formMode (null=lista DataTable, 'create'=aggiungi, 'edit'=modifica),
// dal BB core `useFormInline` (sede unica, ok Tid 2026-09-28): qui restano i
// verbi che ci aggiungono il form della UoM. Fino a quel giorno «aggiungi» era 'new'.
// Campi completi: is_base, factor_to_base, flags vendita/acquisto/logistica,
// qty_step, max_decimals, rounding_mode, forbid_fraction, require_lot, gtin,
// valido_dal/al, attivo.

import { ref, watch, computed, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useFormInline } from '../../core/composables/useFormInline'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { paramBool, paramNumber } from '../../core/utils/parameterCast'
import { listArticoloUom, createArticoloUom, updateArticoloUom, deleteArticoloUom } from '../api/catalogo'
import { toDateString } from '../../core/utils/date'
import { DRAWER_WIDTH, DATE_FORMAT, MANAGE_ICONS, STATUS_ICONS } from '../../core/constants'
import LookupSelect from '../../core/components/LookupSelect.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import RowActionsMenu from '../../core/components/RowActionsMenu.vue'
import PageActionsBar from '../../core/components/PageActionsBar.vue'
import RoundingModeSelect from './RoundingModeSelect.vue'
// eslint-disable-next-line no-restricted-imports -- eccezione nel registro DataTable (scripts/datatable.baseline.json)
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'
import AttivoTag from '../../core/components/AttivoTag.vue'
import { labelOrCode } from '../../core/utils/i18nLabel'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import DatePicker from 'primevue/datepicker'

const { t, te } = useI18n()
const isReadonly = useInjectReadonly()
const { execute, loading, campiErrati } = useApiHandler()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null }
})

const emit = defineEmits(['update:visible', 'saved'])

const uomList = ref([])
const listLoading = ref(false)
// ⚠️ Il click apre la modifica solo in scrittura: il getter e' letto al click.
const {
  formMode, formAperto, rigaInModifica, nuovaRiga, apriRiga, chiudiForm, ancoraForm, azioneNuovaRiga,
} = useFormInline({
  puoModificare: () => !isReadonly.value,
  // D-8: cambiare riga col form modificato chiede (il getter e' letto al clic).
  confermaCambio: (p) => chiudiConConferma(p),
})
const form = ref({})

// Modifiche non salvate del form inline (nuova/modifica UoM): la fotografia
// vive finche' il form e' aperto, e si azzera da sola quando torna la lista.
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, {
  visibile: () => props.visible && formAperto.value,
})

// Fase 5: campi immutabili dopo create per UoM operativa (envelope-level
// dalla lista, fonte = `dbops.vw_non_editable_fields` + gap Python).
const nonEditableFields = ref([])
function isFieldLocked(name) {
  return formMode.value === 'edit' && nonEditableFields.value.includes(name)
}

// Defaults UoM operativa via config.parameters (override per emittente).
// Pre-fetch al setup: quando il drawer apre i valori sono di solito gia' in
// cache. La watch su `props.visible` await-a comunque `loadDefaults()` prima
// di costruire il form, per evitare race in cui il drawer apre prima che la
// fetch finisca (form costruito con fallback hardcoded e mai piu' aggiornato).
// Se i parametri sono assenti lato DB (pre-seed), il fallback e' identico ai
// vecchi defaults hardcoded — nessuna regressione.
const { defaults: paramDefaults, load: loadDefaults } = useParameterDefaults([
  'CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE',
  'CATALOGO_UOM_OP_DEFAULT_QTY_STEP',
  'CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE',
  'CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS',
  'CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION',
])
loadDefaults()

function defaultForm() {
  const p = paramDefaults.value
  return {
    uom_id: null,
    is_base: false,
    factor_to_base: paramNumber(p.CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE, 1),
    is_sell_uom: false,
    is_purchase_uom: false,
    is_logistic_uom: false,
    qty_step: paramNumber(p.CATALOGO_UOM_OP_DEFAULT_QTY_STEP, 1),
    rounding_mode: p.CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE || 'HALF_UP',
    max_decimals: paramNumber(p.CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS, 6),
    forbid_fraction: paramBool(p.CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION, false),
    require_lot: false,
    gtin: '',
    valido_dal: null,
    valido_al: null,
    attivo: true,
  }
}

// Scopo: Sincronizza is_base con factor_to_base.
//        factor=1 → base=true, factor≠1 → base=false.
watch(() => form.value.factor_to_base, (val) => {
  form.value.is_base = val === 1
})

// Scopo: Carica lista UoM operative dell'articolo.
async function loadUom() {
  if (!props.articoloId) return
  listLoading.value = true
  try {
    const res = await listArticoloUom(props.articoloId)
    const payload = res.data?.data
    uomList.value = payload?.results || payload || []
    // Fase 5: cattura i campi non editabili a livello envelope dalla lista.
    // La lista e' la prima chiamata API quando il drawer apre, quindi i
    // metadata sono disponibili prima del primo edit.
    nonEditableFields.value = payload?.non_editable_fields || []
  } catch {
    uomList.value = []
    nonEditableFields.value = []
  } finally {
    listLoading.value = false
  }
}

// Scopo: Verifica se esiste gia' una UoM base nella lista.

watch(() => props.visible, async (val) => {
  if (!val) return
  // Attendi i parameters prima di costruire il form: evita race "drawer aperto
  // con fallback hardcoded mentre la fetch e' ancora in volo". `useParameterDefaults`
  // e' error-safe (silent fail), `loadDefaults` resta no-op se gia' caricato.
  await loadDefaults()
  chiudiForm()
  form.value = defaultForm()
  loadUom()
})

function onStartNew() {
  nuovaRiga()
  form.value = defaultForm()
  // Dopo il giro di watch: `is_base` e' riscritto da `factor_to_base`.
  nextTick(fissa)
}

function onStartEdit(row) {
  apriRiga(row, () => {
    form.value = {
      uom_id: row.uom_id,
      is_base: row.is_base || false,
      factor_to_base: row.factor_to_base ?? 1,
      is_sell_uom: row.is_sell_uom || false,
      is_purchase_uom: row.is_purchase_uom || false,
      is_logistic_uom: row.is_logistic_uom || false,
      qty_step: row.qty_step ?? 1,
      rounding_mode: row.rounding_mode || 'HALF_UP',
      max_decimals: row.max_decimals ?? 6,
      forbid_fraction: row.forbid_fraction || false,
      require_lot: row.require_lot || false,
      gtin: row.gtin || '',
      valido_dal: row.valido_dal ? new Date(row.valido_dal + 'T00:00:00') : null,
      valido_al: row.valido_al ? new Date(row.valido_al + 'T00:00:00') : null,
      attivo: row.attivo ?? true,
    }
    // Dopo il giro di watch: `is_base` e' riscritto da `factor_to_base`.
    nextTick(fissa)
  })
}

function onCancelForm() {
  chiudiForm()
  form.value = defaultForm()
}

// Annulla del form inline: con modifiche chiede conferma.
const annullaForm = () => chiudiConConferma(onCancelForm)

const canSaveForm = computed(() => {
  return form.value.uom_id != null && form.value.factor_to_base > 0
})

// Scopo: Salva UoM operativa (create o update). Ricarica lista e notifica il parent.
async function onSaveForm() {
  const f = form.value
  const payload = {
    is_base: f.is_base,
    factor_to_base: f.factor_to_base,
    is_sell_uom: f.is_sell_uom,
    is_purchase_uom: f.is_purchase_uom,
    is_logistic_uom: f.is_logistic_uom,
    qty_step: f.qty_step,
    rounding_mode: f.rounding_mode,
    max_decimals: f.max_decimals,
    forbid_fraction: f.forbid_fraction,
    require_lot: f.require_lot,
    gtin: f.gtin?.trim() || null,
    valido_dal: toDateString(f.valido_dal),
    valido_al: toDateString(f.valido_al),
    attivo: f.attivo,
  }

  const editId = rigaInModifica.value?.id
  if (formMode.value === 'edit' && editId) {
    const result = await execute(
      () => updateArticoloUom(props.articoloId, editId, payload),
      { successMessage: t('catalogo.uom_salvata') }
    )
    if (result === null) return
  } else {
    payload.uom_id = f.uom_id
    const result = await execute(
      () => createArticoloUom(props.articoloId, payload),
      { successMessage: t('catalogo.uom_aggiunta') }
    )
    if (result === null) return
  }

  chiudiForm()
  form.value = defaultForm()
  await loadUom()
  emit('saved')
}

// Scopo: Elimina UoM operativa. Ricarica lista e notifica il parent.
async function onDelete(row) {
  const result = await execute(
    () => deleteArticoloUom(props.articoloId, row.id),
    { successMessage: t('catalogo.uom_eliminata') }
  )
  if (result !== null) {
    await loadUom()
    emit('saved')
  }
}

// Scopo: azioni di riga UoM operativa (modifica + elimina).
// Capability eliminazione (Fase 6) letta dalla vista DB:
// row.puo_eliminarsi + row.motivo_non_eliminabile (solo is_base blocca).
// L'azione resta visibile anche quando non eseguibile per mantenere la
// affordance e mostrare il motivo via tooltip.
function deleteUomTooltip(row) {
  if (row.puo_eliminarsi) return t('common.delete')
  const motivo = row.motivo_non_eliminabile
  if (!motivo) return t('common.delete')
  // Difensivo: motivo nuovo non mappato i18n -> label generica.
  const key = `catalogo.motivo_${motivo.toLowerCase()}`
  return labelOrCode(t, te, key, t('common.delete'))
}

// Pattern master-detail inline (memo `feedback_master_detail_inline` +
// frontend-standards "Click riga → apre drawer in edit"): la modifica si
// attiva via @row-select sulla DataTable, non dal kebab. Il menu mantiene
// solo le azioni secondarie (elimina).
function buildRigaActions(row) {
  return [
    {
      key: 'elimina-uom',
      label: t('common.delete'),
      icon: MANAGE_ICONS.DELETE,
      severity: 'danger',
      disabled: !row.puo_eliminarsi,
      tooltip: deleteUomTooltip(row),
      command: () => onDelete(row),
    },
  ]
}

// Toolbar pagina: pulsante "Nuovo" prima della lista (pattern standard
// frontend-standards "Azioni Pagina — PageActionsBar"). Nascosto in readonly
// via prop hideWhenReadonly.
// ⚠️ A form aperto «Nuovo» sparisce (regola del BB), non si spegne: era
//    l'unica delle dieci sedi a tenerlo a video disabilitato.
const pageActions = computed(() => [
  azioneNuovaRiga({
    key: 'new',
    label: t('common.new'),
    tooltip: t('catalogo.nuova_uom_operativa'),
    command: onStartNew,
  }),
])

// Click riga DataTable → entra in modifica (modifica = interazione principale,
// non azione del menu). Pattern master-detail inline.
function onRowSelect(event) {
  if (formAperto.value) return
  onStartEdit(event.data)
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('catalogo.tab_uom')"
    :icon="MANAGE_ICONS.UOM"
    :action="t('common.edit')"
    :width="DRAWER_WIDTH.COMPLEX"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :footer="formMode ? 'nessuno' : 'chiudi'"
    @update:visible="(v) => emit('update:visible', v)"
  >
    <div v-if="listLoading" class="app-loading">
      <i :class="STATUS_ICONS.CARICAMENTO" />
    </div>

    <template v-if="!listLoading && !formMode">
      <!-- Toolbar pagina standard: filtri (vuoti qui) + azione primaria
           "Nuovo" prima della lista. Pattern frontend-standards lista
           "PageActionsBar". -->
      <div class="app-page-toolbar">
        <PageActionsBar :actions="pageActions" />
      </div>

      <div v-if="uomList.length === 0" class="app-empty-state">
        <i :class="MANAGE_ICONS.UOM" />
        <p>{{ t('catalogo.nessuna_uom') }}</p>
      </div>

      <DataTable
        v-else
        :value="uomList"
        class="app-datatable app-datatable--inner"
        striped-rows
        selection-mode="single"
        data-key="id"
        @row-select="onRowSelect"
      >
        <Column field="uom_codice" :header="t('catalogo.col_codice')" style="width: 80px;" />
        <Column field="uom_descrizione" :header="t('catalogo.col_descrizione')" style="width: 180px;" />
        <Column :header="t('catalogo.col_base')" style="width: 50px;">
          <template #body="{ data }">
            <Tag v-if="data.is_base" :value="t('catalogo.tag_base')" severity="info" />
          </template>
        </Column>
        <Column field="factor_to_base" :header="t('catalogo.col_fattore')" style="width: 70px;">
          <template #body="{ data }">
            <span class="app-mono">{{ data.factor_to_base }}</span>
          </template>
        </Column>
        <Column :header="t('catalogo.field_logistica')" style="width: 40px;">
          <template #body="{ data }">
            <Tag v-if="data.is_logistic_uom" value="L" severity="success" />
          </template>
        </Column>
        <Column :header="t('catalogo.col_attivo')" style="width: 50px;">
          <template #body="{ data }">
            <AttivoTag :active="data.attivo" />
          </template>
        </Column>
        <Column v-if="!isReadonly" :header="t('common.col_azioni')" class="app-col-actions" :exportable="false">
          <template #body="{ data }">
            <RowActionsMenu :row="data" :actions="buildRigaActions(data)" />
          </template>
        </Column>
      </DataTable>
    </template>

    <template v-if="formMode">
      <div :ref="ancoraForm" class="app-drawer-section">
        <h4>{{ formMode === 'edit' ? t('catalogo.modifica_uom_operativa') : t('catalogo.nuova_uom_operativa') }}</h4>
      </div>

      <!-- UoM + Base + Fattore -->
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('catalogo.field_uom') }} *</label>
          <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura"
            :placeholder="t('catalogo.select_uom')" :disabled="isFieldLocked('uom_id')" />
        </div>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('catalogo.col_base') }}</label>
          <ToggleSwitch v-model="form.is_base" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_fattore') }} *</label>
          <InputNumber v-model="form.factor_to_base" :min="0" :min-fraction-digits="2"
            :max-fraction-digits="6" :disabled="form.is_base"
            :invalid="campiErrati.includes('factor_to_base')"
          />
        </div>
      </div>

      <!-- Flags uso -->
      <div class="app-drawer-section"><h4>{{ t('catalogo.section_uso') }}</h4></div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('catalogo.field_vendita') }}</label>
          <ToggleSwitch v-model="form.is_sell_uom" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_acquisto') }}</label>
          <ToggleSwitch v-model="form.is_purchase_uom" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_logistica') }}</label>
          <ToggleSwitch v-model="form.is_logistic_uom" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_require_lot') }}</label>
          <ToggleSwitch v-model="form.require_lot" />
        </div>
      </div>

      <!-- Regole input -->
      <div class="app-drawer-section"><h4>{{ t('catalogo.section_regole_input') }}</h4></div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('catalogo.field_forbid_fraction') }}</label>
          <ToggleSwitch v-model="form.forbid_fraction" />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_qty_step') }}</label>
          <InputNumber v-model="form.qty_step" :min="0.000001" :min-fraction-digits="0"
            :max-fraction-digits="6" :disabled="form.forbid_fraction"
            :invalid="campiErrati.includes('qty_step')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_max_decimals') }}</label>
          <InputNumber v-model="form.max_decimals" :min="0" :max="6"
            :disabled="form.forbid_fraction"
            :invalid="campiErrati.includes('max_decimals')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_rounding_mode') }}</label>
          <RoundingModeSelect v-model="form.rounding_mode" />
        </div>
      </div>

      <!-- GTIN + Validita' + Attivo -->
      <div class="app-drawer-section"><h4>{{ t('catalogo.section_extra') }}</h4></div>
      <div class="form-grid">
        <div class="form-field">
          <label>{{ t('catalogo.field_gtin') }}</label>
          <InputText v-model="form.gtin" />
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('catalogo.field_valido_dal') }}</label>
          <DatePicker v-model="form.valido_dal" :dateFormat="DATE_FORMAT" showIcon showButtonBar
            :invalid="campiErrati.includes('valido_dal')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('catalogo.field_valido_al') }}</label>
          <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar
            :invalid="campiErrati.includes('valido_al')"
          />
        </div>
      </div>
      <div v-if="formMode === 'edit'" class="form-grid">
        <div class="form-field">
          <label>{{ t('indirizzi.campo_attivo') }}</label>
          <ToggleSwitch v-model="form.attivo"
            :invalid="campiErrati.includes('attivo')"
          />
        </div>
      </div>

      <FormFooter
        :loading="loading"
        :disabled="!canSaveForm"
        @save="onSaveForm"
        @cancel="annullaForm"
      />
    </template>
  </AppDrawer>
</template>

<style scoped>
.app-drawer-section {
  margin-top: 1rem;
  padding-bottom: 0.25rem;
  border-bottom: 1px solid var(--app-border-color);
}
.app-drawer-section h4 {
  margin: 0;
  font-size: 0.9rem;
  font-weight: 600;
}
</style>

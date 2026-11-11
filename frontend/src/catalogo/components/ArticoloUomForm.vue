<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il form di UNA unita' di misura operativa dell'articolo (aggiungi /
//        modifica), montato da `ArticoloUomDrawer` nello slot `#form` di
//        `ListaConFormInline`. Estratto dal corpo del drawer il 2026-10-31,
//        quando la lista e' passata al BB (brief-db-liste-datatable-grezze-
//        secondo-giro riga 4): campi, default e salvataggio sono quelli di
//        prima, spostati.
// Campi: factor_to_base, flags vendita/acquisto/logistica, qty_step,
// max_decimals, forbid_fraction, gtin, valido_dal/al, attivo.
// ⛔ `is_base` NON si scrive (2026-11-09, giro 2 di brief-db-revisione-catalogo):
//    la riga base nasce con l'articolo e non cambia piu' (guard
//    `trgfn_articoli_uom_operativa_guard_base`). Qui si mostra soltanto.
//    Fino a quel giorno un `watch` la ricavava dal fattore (`fattore 1 → base`):
//    un'unita' con fattore 1 che base non e' finiva marcata base.
// ⛔ `rounding_mode` e `require_lot` sono ritirate dal DB (Q4, BE16).
// ⛔ Unita', fattore e inizio di una mappatura scritta non si cambiano
//    (2026-11-11, BE21 di brief-db-revisione-catalogo: guard della storia,
//    `E_UOM_STORIA_IMMUTABILE`). Si spengono da `nonEditableFields`, che il
//    backend riempie: si cambia la FINE, e per valori nuovi si chiude e si
//    inserisce una mappatura nuova. ⛔ In modifica i campi fermi NON si
//    rimandano (BB `senzaCampiFermi`, regola del 2 col drawer delle
//    conversioni): un valore riletto e convertito puo' non essere quello
//    scritto, e il guard lo giudicherebbe un cambiamento.
// ⭐ Interruttore «attivo» e data di fine seguono la capability della riga
//    (2026-11-11, BE21-b/f: la vista `vw_articoli_uom_operativa_dettaglio`
//    dal BB del DB `fn_uom_conversione_capability`), letta dall'helper
//    `capabilityConversioneUom` (regola del 2 col drawer delle conversioni):
//    spenti col motivo, la fine dalla prima data ammessa, e non rimandati.
//    Sulla riga base tutti e due fermi (Q34: la base non si spegne).
// ⭐ Espone la sua fotografia (`modificato`, `chiudiConConferma`): il BB la
//    registra (D-13).
import { computed, nextTick, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { paramBool, paramNumber } from '../../core/utils/parameterCast'
import { toDateString, parseIsoDate } from '../../core/utils/date'
import { senzaCampiFermi } from '../../core/utils/senzaCampiFermi'
import {
  capabilityConversioneUom, fermoDallaCapability, fraseMotivoUom,
} from '../utils/capabilityConversioneUom'
import { DATE_FORMAT } from '../../core/constants'
import { createArticoloUom, updateArticoloUom } from '../api/catalogo'
import LookupSelect from '../../core/components/LookupSelect.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import Tag from 'primevue/tag'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import ToggleSwitch from 'primevue/toggleswitch'
import DatePicker from 'primevue/datepicker'

const props = defineProps({
  // La UoM in modifica; `null` in creazione.
  riga: { type: Object, default: null },
  articoloId: { type: String, required: true },
  // I campi che dopo la creazione non si cambiano (dalla busta della lista).
  nonEditableFields: { type: Array, default: () => [] },
})
const emit = defineEmits(['saved', 'cancel'])

const { t, te } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()

const inModifica = computed(() => props.riga != null)
// La riga base ha sempre fattore 1 e nessuna data (CHECK
// `chk_articoli_uom_operativa_base_fissa`): i tre campi non si toccano.
const isBase = computed(() => props.riga?.is_base === true)
function isFieldLocked(name) {
  return inModifica.value && props.nonEditableFields.includes(name)
}

// Che cosa la riga ammette oggi (la capability della vista): in creazione tutto.
const cap = computed(() => capabilityConversioneUom(props.riga))
// Fermo per il PATCH: i campi del lock e quelli che la capability spegne.
function fermoNelPatch(name) {
  return isFieldLocked(name) || fermoDallaCapability(cap.value, name)
}

// Defaults UoM operativa via config.parameters (override per emittente). Il
// form si costruisce DOPO il loro arrivo: senza, nascerebbe coi ripieghi e
// non si aggiornerebbe piu'. Parametri assenti → gli stessi ripieghi di prima.
const { defaults: paramDefaults, load: loadDefaults } = useParameterDefaults([
  'CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE',
  'CATALOGO_UOM_OP_DEFAULT_QTY_STEP',
  'CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS',
  'CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION',
])

function defaultForm() {
  const p = paramDefaults.value
  return {
    uom_id: null,
    factor_to_base: paramNumber(p.CATALOGO_UOM_OP_DEFAULT_FACTOR_TO_BASE, 1),
    is_sell_uom: false,
    is_purchase_uom: false,
    is_logistic_uom: false,
    qty_step: paramNumber(p.CATALOGO_UOM_OP_DEFAULT_QTY_STEP, 1),
    max_decimals: paramNumber(p.CATALOGO_UOM_OP_DEFAULT_MAX_DECIMALS, 6),
    forbid_fraction: paramBool(p.CATALOGO_UOM_OP_DEFAULT_FORBID_FRACTION, false),
    gtin: '',
    valido_dal: null,
    valido_al: null,
    attivo: true,
  }
}

function formDa(row) {
  return {
    uom_id: row.uom_id,
    factor_to_base: row.factor_to_base ?? 1,
    is_sell_uom: row.is_sell_uom || false,
    is_purchase_uom: row.is_purchase_uom || false,
    is_logistic_uom: row.is_logistic_uom || false,
    qty_step: row.qty_step ?? 1,
    max_decimals: row.max_decimals ?? 6,
    forbid_fraction: row.forbid_fraction || false,
    gtin: row.gtin || '',
    valido_dal: parseIsoDate(row.valido_dal),
    valido_al: parseIsoDate(row.valido_al),
    attivo: row.attivo ?? true,
  }
}

const form = ref(props.riga ? formDa(props.riga) : defaultForm())
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => true })

onMounted(async () => {
  if (!inModifica.value) {
    await loadDefaults()
    form.value = defaultForm()
  }
  await nextTick()
  fissa()
})

const canSave = computed(() => form.value.uom_id != null && form.value.factor_to_base > 0)

// Scopo: Salva UoM operativa (create o update).
async function onSave() {
  const f = form.value
  const payload = {
    factor_to_base: f.factor_to_base,
    is_sell_uom: f.is_sell_uom,
    is_purchase_uom: f.is_purchase_uom,
    is_logistic_uom: f.is_logistic_uom,
    qty_step: f.qty_step,
    max_decimals: f.max_decimals,
    forbid_fraction: f.forbid_fraction,
    gtin: f.gtin?.trim() || null,
    attivo: f.attivo,
  }
  // La riga base non porta date (CHECK): non si mandano nemmeno vuote.
  if (!isBase.value) {
    payload.valido_dal = toDateString(f.valido_dal)
    payload.valido_al = toDateString(f.valido_al)
  }
  const result = inModifica.value
    ? await execute(
      () => updateArticoloUom(props.articoloId, props.riga.id, senzaCampiFermi(payload, fermoNelPatch)),
      { successMessage: t('catalogo.uom_salvata') },
    )
    : await execute(
      () => createArticoloUom(props.articoloId, { ...payload, uom_id: f.uom_id }),
      { successMessage: t('catalogo.uom_aggiunta') },
    )
  if (result === null) return
  fissa()
  emit('saved', result)
}

// Annulla: con modifiche chiede conferma.
const annulla = () => chiudiConConferma(() => emit('cancel'))

defineExpose({ modificato, chiudiConConferma })
</script>

<template>
  <!-- UoM + Base + Fattore -->
  <div class="form-grid">
    <div class="form-field">
      <label>{{ t('catalogo.field_uom') }} *</label>
      <LookupSelect v-model="form.uom_id" rel="catalogo.unita_misura"
        :placeholder="t('catalogo.select_uom')" :disabled="isFieldLocked('uom_id')" />
    </div>
  </div>

  <div class="form-grid-2col">
    <div v-if="isBase" class="form-field">
      <label>{{ t('catalogo.col_base') }}</label>
      <Tag :value="t('catalogo.tag_base')" severity="info" />
      <small>{{ t('catalogo.hint_uom_base_fissa') }}</small>
    </div>
    <div class="form-field">
      <label>{{ t('catalogo.field_fattore') }} *</label>
      <InputNumber v-model="form.factor_to_base" :min="0" :min-fraction-digits="2"
        :max-fraction-digits="6" :disabled="isBase || isFieldLocked('factor_to_base')"
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
        :disabled="isBase || isFieldLocked('valido_dal')"
        :invalid="campiErrati.includes('valido_dal')"
      />
    </div>
    <div class="form-field">
      <label>{{ t('catalogo.field_valido_al') }}</label>
      <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar
        :disabled="isBase || cap.fineFerma"
        :min-date="cap.primaFine ?? undefined"
        :invalid="campiErrati.includes('valido_al')"
      />
      <small v-if="cap.motivoFine && !isBase" data-testid="motivo-fine">{{ fraseMotivoUom(t, te, cap.motivoFine) }}</small>
    </div>
  </div>
  <div v-if="inModifica" class="form-grid">
    <div class="form-field">
      <label>{{ t('indirizzi.campo_attivo') }}</label>
      <ToggleSwitch v-model="form.attivo"
        :disabled="cap.attivoFermo"
        :invalid="campiErrati.includes('attivo')"
      />
      <small v-if="cap.motivoAttivo" data-testid="motivo-attivo">{{ fraseMotivoUom(t, te, cap.motivoAttivo) }}</small>
    </div>
  </div>

  <FormFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="annulla" />
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

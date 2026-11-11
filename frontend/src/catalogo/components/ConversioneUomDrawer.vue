<script setup>
// Scopo: Drawer crea/modifica conversione UoM.
//        In create: seleziona UoM Da, UoM A, fattore, date validita'.
//        In edit: unita' Da/A, fattore e inizio immutabili (dal 2026-11-11,
//        BE21: guard della storia, dai `non_editable_fields`) e non rimandati;
//        si cambia la fine. ⭐ Interruttore «attivo» e data di fine seguono la
//        capability del dettaglio (dal 2026-11-11, BE21-e: la vista
//        `vw_unita_misura_conversioni_dettaglio`, BB del DB
//        `fn_uom_conversione_capability`), letta dall'helper comune
//        `capabilityConversioneUom`: spenti col motivo, la fine dalla prima
//        data ammessa, e non rimandati. Fino a quel giorno il toggle restava
//        acceso e il DB rifiutava dopo il clic.
//        Contenuto deferito a dopo l'animazione per evitare rimbalzi visivi.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useConversioniUomStore } from '../stores/conversioniUom'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookupCodici } from '../../core/composables/useLookupCodici'
import { DRAWER_WIDTH, DATE_FORMAT } from '../../core/constants'
import { parseIsoDate, toDateString, oggiAziendale } from '../../core/utils/date'
import { senzaCampiFermi } from '../../core/utils/senzaCampiFermi'
import {
  capabilityConversioneUom, fermoDallaCapability, fraseMotivoUom,
} from '../utils/capabilityConversioneUom'
import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'

const ALWAYS_VALID_FROM = '1900-01-01'

const { t, te } = useI18n()
const store = useConversioniUomStore()
const { execute, loading, campiErrati } = useApiHandler()
const uomLookup = useLookupCodici('catalogo.unita_misura', { immediate: true })

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  convId: { type: [Number, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const form = ref({
  uom_from_id: null, uom_to_id: null, fattore: null,
  valido_dal: parseIsoDate(ALWAYS_VALID_FROM), valido_dal_sempre: true,
  valido_al: null, attivo: true
})
// Modifiche non salvate: fotografia all'apertura (anche in creazione) e
// conferma se si chiude con modifiche (BB useDrawerFormPreserve).
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(form, { visibile: () => props.visible })

// Campi immutabili dopo create per conversioni UoM. Vengono dal detail
// (`detail.non_editable_fields`, fonte = `dbops.vw_non_editable_fields`: dal
// 2026-11-11 il lock di colonna di unita', fattore e inizio, BE21-a).
const nonEditableFields = ref([])
function isFieldLocked(name) {
  return isEdit.value && nonEditableFields.value.includes(name)
}

// La capability del dettaglio (in creazione nessuna riga: tutto libero).
const dettaglio = ref(null)
const cap = computed(() => capabilityConversioneUom(isEdit.value ? dettaglio.value : null))
// Fermo per il PATCH: i campi del lock e quelli che la capability spegne.
function fermoNelPatch(name) {
  return isFieldLocked(name) || fermoDallaCapability(cap.value, name)
}

const selectedFromTipoId = computed(() => {
  const selected = uomLookup.items.value.find(item => item.id === form.value.uom_from_id)
  return selected?.tipo_uom_id ?? null
})

function resetForm() {
  form.value = {
    uom_from_id: null, uom_to_id: null, fattore: null,
    valido_dal: parseIsoDate(ALWAYS_VALID_FROM),
    valido_dal_sempre: true,
    valido_al: null,
    attivo: true
  }
  fissa()
}


async function loadDetail() {
  if (!props.convId) return
  // Fail-closed mentre il dettaglio arriva: niente capability di un'altra riga.
  dettaglio.value = {}
  const data = await store.fetchDetail(props.convId)
  if (!data) return
  dettaglio.value = data
  form.value = {
    uom_from_id: data.uom_from_id,
    uom_to_id: data.uom_to_id,
    fattore: Number(data.fattore),
    valido_dal: parseIsoDate(data.valido_dal),
    valido_dal_sempre: data.valido_dal === ALWAYS_VALID_FROM,
    valido_al: parseIsoDate(data.valido_al),
    attivo: data.attivo ?? true
  }
  fissa()
  nonEditableFields.value = data.non_editable_fields || []
}

watch(() => props.visible, (v) => {
  if (!v) return  // contentReady reset gestito da useDrawerContentReady
  if (isEdit.value) {
    loadDetail()
  } else {
    resetForm()
  }
})

watch(selectedFromTipoId, (tipoId) => {
  if (tipoId == null || form.value.uom_to_id == null) return
  const selectedTo = uomLookup.items.value.find(item => item.id === form.value.uom_to_id)
  if (selectedTo && selectedTo.tipo_uom_id !== tipoId) {
    form.value.uom_to_id = null
  }
})

watch(() => form.value.valido_dal_sempre, (sempre) => {
  if (isEdit.value) return
  form.value.valido_dal = sempre ? parseIsoDate(ALWAYS_VALID_FROM) : oggiAziendale()
})

const canSave = computed(() =>
  form.value.uom_from_id != null &&
  form.value.uom_to_id != null &&
  form.value.fattore != null && form.value.fattore > 0
)

async function handleSave() {
  const f = form.value
  if (isEdit.value) {
    // ⛔ I campi fermi NON si rimandano (2026-11-11, BE21; BB
    //    `senzaCampiFermi`). Il fattore arriva come stringa numeric(18,6) e il
    //    form lo tiene come Number (`loadDetail`): oltre ~15 cifre
    //    significative il valore rimandato non e' piu' quello scritto, e il
    //    guard della storia rifiuterebbe una semplice chiusura.
    const payload = senzaCampiFermi({
      fattore: f.fattore,
      valido_dal: toDateString(f.valido_dal),
      valido_al: toDateString(f.valido_al),
      attivo: f.attivo,
    }, fermoNelPatch)
    const result = await execute(
      () => store.update(props.convId, payload),
      { successMessage: t('catalogo.conv_salvata') }
    )
    if (result !== null) { emit('saved', result); close() }
  } else {
    const payload = {
      uom_from_id: f.uom_from_id,
      uom_to_id: f.uom_to_id,
      fattore: f.fattore,
      valido_dal: f.valido_dal_sempre ? ALWAYS_VALID_FROM : toDateString(f.valido_dal),
      valido_al: toDateString(f.valido_al),
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('catalogo.conv_creata') }
    )
    if (result !== null) { emit('saved', result); close() }
  }
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="visible"
    :title="t('catalogo.conversione_uom')"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="handleSave"
  >
    <div class="form-grid">
      <div class="form-field">
        <label>{{ t('catalogo.field_uom_da') }} *</label>
        <LookupSelect v-model="form.uom_from_id" rel="catalogo.unita_misura"
          :placeholder="t('catalogo.select_uom')" :disabled="isFieldLocked('uom_from_id')" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_uom_a') }} *</label>
        <LookupSelect v-model="form.uom_to_id" rel="catalogo.unita_misura"
          :placeholder="t('catalogo.select_uom')" filter-field="tipo_uom_id"
          :filter-value="selectedFromTipoId" :disabled="isFieldLocked('uom_to_id')" />
      </div>
      <div class="form-field">
        <label>{{ t('catalogo.field_fattore') }} *</label>
        <InputNumber v-model="form.fattore" :min-fraction-digits="2" :max-fraction-digits="6" :min="0" mode="decimal"
          :disabled="isFieldLocked('fattore')" :invalid="campiErrati.includes('fattore')" />
      </div>
    </div>

    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('common.data_da') }}</label>
        <DatePicker
          v-model="form.valido_dal"
          :dateFormat="DATE_FORMAT"
          showIcon
          showButtonBar
          :disabled="isFieldLocked('valido_dal') || (!isEdit && form.valido_dal_sempre)"
          :invalid="campiErrati.includes('valido_dal')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('common.data_a') }}</label>
        <DatePicker v-model="form.valido_al" :dateFormat="DATE_FORMAT" showIcon showButtonBar
          :disabled="cap.fineFerma"
          :min-date="cap.primaFine ?? undefined"
          :invalid="campiErrati.includes('valido_al')"
        />
        <small v-if="cap.motivoFine" data-testid="motivo-fine">{{ fraseMotivoUom(t, te, cap.motivoFine) }}</small>
      </div>
    </div>
    <div v-if="!isEdit" class="form-grid">
      <div class="form-field">
        <label>{{ t('catalogo.validita_sempre') }}</label>
        <ToggleSwitch v-model="form.valido_dal_sempre" />
      </div>
    </div>

    <div v-if="isEdit" class="form-grid">
      <div class="form-field">
        <label>{{ t('indirizzi.campo_attivo') }}</label>
        <ToggleSwitch v-model="form.attivo"
          :disabled="cap.attivoFermo"
          :invalid="campiErrati.includes('attivo')"
        />
        <small v-if="cap.motivoAttivo" data-testid="motivo-attivo">{{ fraseMotivoUom(t, te, cap.motivoAttivo) }}</small>
      </div>
    </div>
  </AppDrawer>
</template>

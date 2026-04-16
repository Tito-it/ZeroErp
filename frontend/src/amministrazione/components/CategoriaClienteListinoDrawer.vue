<script setup>
// Scopo: Drawer crea/modifica riga matrice anagrafiche.categorie_clienti_listini.
//        - In create: categoria/utility/emittente/classe_utenza abilitati.
//        - In edit:   dimensioni immutabili (BE rifiuta con E_ANAG_VALIDAZIONE).
//                     Listino/variazione/date/attivo mutabili.
//        - Sola lettura: prop `readonly` cumulativa con useInjectReadonly.
// Pattern: copia 1:1 di UtilityTipoRuoloDrawer con campi pricing v5 extra.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCategorieClientiListiniStore } from '../stores/categorieClientiListini'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useLookup } from '../../core/composables/useLookup'
import { listEmittentiFiscali } from '../api/amministrazione'
import { DRAWER_WIDTH } from '../../core/constants'
import { isoToLocalDate, localDateToIso } from '../../core/utils/dateHelpers'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useCategorieClientiListiniStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()
const emittentiLookup = useLookup(listEmittentiFiscali, { immediate: true })

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  recordId: { type: [Number, null], default: null },
  // Prop esplicita: si combina con inject readonly del parent.
  readonly: { type: Boolean, default: false }
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const isReadOnlyEffective = computed(() => props.readonly || isReadonly.value)

const tipoVariazioneOptions = [
  { value: null, label: t('amministrazione.matrice_categorie_listini.variazione_nessuna') },
  { value: 'PERCENTUALE', label: 'PERCENTUALE' },
  { value: 'VALORE_FISSO', label: 'VALORE_FISSO' }
]

const form = ref({
  categoria_cliente_id: null,
  utility_id: null,
  emittente_soggetto_ruolo_id: null,
  classe_utenza_id: null,
  listino_id: null,
  tipo_variazione: null,
  valore_variazione: null,
  valido_dal: null,
  valido_al: null,
  attivo: true
})

function resetForm() {
  form.value = {
    categoria_cliente_id: null,
    utility_id: null,
    emittente_soggetto_ruolo_id: null,
    classe_utenza_id: null,
    listino_id: null,
    tipo_variazione: null,
    valore_variazione: null,
    valido_dal: null,
    valido_al: null,
    attivo: true
  }
}

async function loadDetail() {
  if (!props.recordId) return
  const data = await store.fetchDetail(props.recordId)
  if (!data) return
  form.value = {
    categoria_cliente_id: data.categoria_cliente_id ?? null,
    utility_id: data.utility_id ?? null,
    emittente_soggetto_ruolo_id: data.emittente_soggetto_ruolo_id ?? null,
    classe_utenza_id: data.classe_utenza_id ?? null,
    listino_id: data.listino_id ?? null,
    tipo_variazione: data.tipo_variazione ?? null,
    valore_variazione: data.valore_variazione != null
      ? Number(data.valore_variazione)
      : null,
    valido_dal: isoToLocalDate(data.valido_dal),
    valido_al: isoToLocalDate(data.valido_al),
    attivo: data.attivo ?? true
  }
}

// Watch combinato su visible+recordId.
watch(
  [() => props.visible, () => props.recordId],
  ([visible]) => {
    if (!visible) return
    if (isEdit.value) {
      loadDetail()
    } else {
      resetForm()
    }
  }
)

// Scopo: Coerenza tipo_variazione <-> valore_variazione (anticipo UI del
//        CHECK DB). Svuota valore quando tipo viene annullato; forza valore
//        se tipo e' scelto ma valore vuoto -> disabled save.
function onTipoVariazioneChange(event) {
  if (event.value == null) {
    form.value.valore_variazione = null
  }
}

const canSave = computed(() => {
  if (isReadOnlyEffective.value) return false
  // Dimensioni + listino + valido_dal sono minimi per create.
  if (!isEdit.value) {
    if (form.value.categoria_cliente_id == null) return false
    if (form.value.utility_id == null) return false
    if (form.value.emittente_soggetto_ruolo_id == null) return false
    if (form.value.listino_id == null) return false
    if (form.value.valido_dal == null) return false
  }
  // Coerenza variazione (coppia): tipo presente -> valore richiesto e viceversa.
  const hasTipo = form.value.tipo_variazione != null
  const hasValore = form.value.valore_variazione != null
  if (hasTipo !== hasValore) return false
  return true
})

// Scopo: Salva e delega chiusura al parent (pattern PraticaDrawer: no auto-close
//        per evitare jitter tra animazione drawer e re-render DataTable).
async function handleSave() {
  const payload = {
    listino_id: form.value.listino_id,
    tipo_variazione: form.value.tipo_variazione,
    valore_variazione: form.value.valore_variazione != null
      ? String(form.value.valore_variazione)
      : null,
    valido_dal: localDateToIso(form.value.valido_dal),
    valido_al: localDateToIso(form.value.valido_al),
    attivo: form.value.attivo
  }
  if (!isEdit.value) {
    // Dimensioni solo in create: BE rifiuta in PATCH.
    payload.categoria_cliente_id = form.value.categoria_cliente_id
    payload.utility_id = form.value.utility_id
    payload.emittente_soggetto_ruolo_id = form.value.emittente_soggetto_ruolo_id
    payload.classe_utenza_id = form.value.classe_utenza_id
  }
  const result = await execute(
    () => isEdit.value
      ? store.update(props.recordId, payload)
      : store.create(payload),
    {
      successMessage: isEdit.value
        ? t('amministrazione.matrice_categorie_listini.saved')
        : t('amministrazione.matrice_categorie_listini.created')
    }
  )
  if (result !== null) emit('saved', result)
}

function close() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="v => emit('update:visible', v)"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :dismissable="true"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('amministrazione.matrice_categorie_listini.drawer_title')"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadOnlyEffective }">
      <div class="form-grid">
        <!-- === Dimensioni (immutabili in edit) === -->
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_categoria') }} <span v-if="!isEdit">*</span></label>
          <LookupSelect
            v-model="form.categoria_cliente_id"
            rel="anagrafiche.categorie_clienti"
            :placeholder="t('amministrazione.matrice_categorie_listini.field_categoria_placeholder')"
            :disabled="isEdit || isReadOnlyEffective"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_utility') }} <span v-if="!isEdit">*</span></label>
          <LookupSelect
            v-model="form.utility_id"
            rel="config.utilities"
            :placeholder="t('amministrazione.matrice_categorie_listini.field_utility_placeholder')"
            :disabled="isEdit || isReadOnlyEffective"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_emittente') }} <span v-if="!isEdit">*</span></label>
          <Select
            v-model="form.emittente_soggetto_ruolo_id"
            :options="emittentiLookup.items.value"
            option-label="ragione_sociale"
            option-value="soggetto_ruolo_id"
            :placeholder="t('amministrazione.matrice_categorie_listini.field_emittente_placeholder')"
            filter
            :disabled="isEdit || isReadOnlyEffective"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_classe_utenza') }}</label>
          <LookupSelect
            v-model="form.classe_utenza_id"
            rel="config.classi_utenze"
            :placeholder="t('amministrazione.matrice_categorie_listini.field_classe_utenza_placeholder')"
            showClear
            :disabled="isEdit || isReadOnlyEffective"
          />
        </div>

        <Message v-if="isEdit" severity="info" :closable="false">
          {{ t('amministrazione.matrice_categorie_listini.fk_immutable_hint') }}
        </Message>

        <!-- === Listino + variazione === -->
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_listino') }} *</label>
          <LookupSelect
            v-model="form.listino_id"
            rel="vendite.listini"
            :placeholder="t('amministrazione.matrice_categorie_listini.field_listino_placeholder')"
            :disabled="isReadOnlyEffective"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_tipo_variazione') }}</label>
          <Select
            v-model="form.tipo_variazione"
            :options="tipoVariazioneOptions"
            option-label="label"
            option-value="value"
            @change="onTipoVariazioneChange"
            :disabled="isReadOnlyEffective"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_valore_variazione') }}</label>
          <InputNumber
            v-model="form.valore_variazione"
            :max-fraction-digits="4"
            :disabled="form.tipo_variazione == null || isReadOnlyEffective"
            showButtons
          />
          <small class="text-color-secondary">
            {{ t('amministrazione.matrice_categorie_listini.field_valore_variazione_hint') }}
          </small>
        </div>

        <!-- === Validita' === -->
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_valido_dal') }} *</label>
          <DatePicker
            v-model="form.valido_dal"
            date-format="dd/mm/yy"
            show-icon
            :disabled="isReadOnlyEffective"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_valido_al') }}</label>
          <DatePicker
            v-model="form.valido_al"
            date-format="dd/mm/yy"
            show-icon
            show-button-bar
            :disabled="isReadOnlyEffective"
          />
        </div>

        <!-- === Attivo === -->
        <div class="form-field">
          <label>{{ t('common.attivo') }}</label>
          <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective" />
        </div>
      </div>

      <DrawerFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="close"
      />
    </div>
  </Drawer>
</template>

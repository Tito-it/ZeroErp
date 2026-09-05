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
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useNotify } from '../../core/composables/useNotify'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useLookup } from '../../core/composables/useLookup'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { listEmittentiFiscali } from '../api/amministrazione'
import { lookupCategorieListiniTipiVariazione } from '../api/categorieClientiListini'
import { DRAWER_WIDTH } from '../../core/constants'
import { parseIsoDate, toDateString } from '../../core/utils/date'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
import Select from 'primevue/select'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import ToggleSwitch from 'primevue/toggleswitch'
import Message from 'primevue/message'



const { t } = useI18n()
const store = useCategorieClientiListiniStore()
const { execute, loading, campiErrati } = useApiHandler()
const notify = useNotify()
const isReadonly = useInjectReadonly()
const emittentiLookup = useLookup(listEmittentiFiscali, { immediate: true })

// Fase 4 — Lookup statico tipi di variazione dal BE (PERCENTUALE/VALORE_FISSO).
// Cache modulo-level: primo consumer fa la fetch, successivi riusano la lista.
// Single source of truth lato BE. Display "descrizione (codice)" allineato a
// EmittenteRoundingModeSelect. Stessa shape: data e' lista nuda, transform
// `(r) => r.data.data` evita il default `r.data.data.results` dell'envelope paginato.
const tipoVariazioneLookup = useGlobalLookup(
  'anag.categorie_listini_tipi_variazione',
  lookupCategorieListiniTipiVariazione,
  { immediate: true, transform: (r) => r.data.data },
)

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  recordId: { type: [Number, null], default: null },
  // Prop esplicita: si combina con inject readonly del parent.
  readonly: { type: Boolean, default: false }
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')
const isReadOnlyEffective = computed(() => props.readonly || isReadonly.value)

// Fase 4 — Campi non editabili letti dal BE detail (non hardcoded).
// In create resta vuoto (tutti i campi modificabili). In edit popolato dal
// detail con la lista delle dimensioni immutabili. La UI usa
// `isFieldImmutable(name)` per gating dei Select dimensionali.
const nonEditableFields = ref([])

function isFieldImmutable(field) {
  return nonEditableFields.value.includes(field)
}

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
  nonEditableFields.value = []
}

async function loadDetail() {
  if (!props.recordId) return
  const data = await store.fetchDetail(props.recordId)
  // Race cancellation: se l'utente chiude e riapre in create prima che
  // la fetch completi, la mutazione post-await sovrascriverebbe il form
  // gia' resettato (incluso nonEditableFields). Pattern allineato a
  // EmittenteFiscaleDrawer Fase 3.
  if (!props.visible || !isEdit.value) return
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
    valido_dal: parseIsoDate(data.valido_dal),
    valido_al: parseIsoDate(data.valido_al),
    attivo: data.attivo ?? true
  }
  // Fase 4: popola lista campi immutabili dal BE detail (data-driven).
  nonEditableFields.value = Array.isArray(data.non_editable_fields)
    ? data.non_editable_fields
    : []
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
//        CHECK DB). Svuota valore quando tipo viene annullato oppure cambia
//        (la semantica del valore e' diversa tra PERCENTUALE e VALORE_FISSO,
//        tenere 10 da % a fisso e' fonte d'errore). Toast info per segnalare.
function onTipoVariazioneChange(event) {
  const hadValue = form.value.valore_variazione != null
  if (event.value == null) {
    form.value.valore_variazione = null
    return
  }
  if (hadValue) {
    form.value.valore_variazione = null
    notify.warn(t('common.tipo_variazione_reset'))
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
    valido_dal: toDateString(form.value.valido_dal),
    valido_al: toDateString(form.value.valido_al),
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
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('amministrazione.matrice_categorie_listini.drawer_title')"
      />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadOnlyEffective }">
      <div class="form-grid">
        <!-- === Dimensioni (Fase 4: immutabilita' data-driven da BE non_editable_fields) === -->
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_categoria') }} *</label>
          <LookupSelect
            v-model="form.categoria_cliente_id"
            rel="anagrafiche.categorie_clienti"
            :placeholder="t('amministrazione.matrice_categorie_listini.field_categoria_placeholder')"
            :disabled="isFieldImmutable('categoria_cliente_id') || isReadOnlyEffective"
          />
        </div>
        <div class="form-field">
          <label>{{ t('amministrazione.matrice_categorie_listini.field_emittente') }} *</label>
          <Select
            v-model="form.emittente_soggetto_ruolo_id"
            :options="emittentiLookup.items.value"
            option-label="ragione_sociale"
            option-value="soggetto_ruolo_id"
            :placeholder="t('amministrazione.matrice_categorie_listini.field_emittente_placeholder')"
            filter
            :disabled="isFieldImmutable('emittente_soggetto_ruolo_id') || isReadOnlyEffective"
            :invalid="campiErrati.includes('emittente_soggetto_ruolo_id')"
          />
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('amministrazione.matrice_categorie_listini.field_utility') }} *</label>
            <LookupSelect
              v-model="form.utility_id"
              rel="config.utilities"
              :placeholder="t('amministrazione.matrice_categorie_listini.field_utility_placeholder')"
              :disabled="isFieldImmutable('utility_id') || isReadOnlyEffective"
            />
          </div>
          <div class="form-field">
            <label>{{ t('amministrazione.matrice_categorie_listini.field_classe_utenza') }}</label>
            <LookupSelect
              v-model="form.classe_utenza_id"
              rel="config.classi_utenze"
              :placeholder="t('amministrazione.matrice_categorie_listini.field_classe_utenza_placeholder')"
              showClear
              :disabled="isFieldImmutable('classe_utenza_id') || isReadOnlyEffective"
            />
          </div>
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
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('amministrazione.matrice_categorie_listini.field_tipo_variazione') }}</label>
            <Select
              v-model="form.tipo_variazione"
              :options="tipoVariazioneLookup.items.value"
              :loading="tipoVariazioneLookup.loading.value"
              option-label="descrizione"
              option-value="codice"
              :placeholder="t('amministrazione.matrice_categorie_listini.variazione_nessuna')"
              show-clear
              @change="onTipoVariazioneChange"
              :disabled="isReadOnlyEffective"
              :invalid="campiErrati.includes('tipo_variazione')"
            />
          </div>
          <div class="form-field">
            <label>{{ t('amministrazione.matrice_categorie_listini.field_valore_variazione') }}</label>
            <InputNumber
              v-model="form.valore_variazione"
              :max-fraction-digits="4"
              :disabled="form.tipo_variazione == null || isReadOnlyEffective"
              showButtons
              :invalid="campiErrati.includes('valore_variazione')"
            />
            <small class="text-color-secondary">
              {{ t('amministrazione.matrice_categorie_listini.field_valore_variazione_hint') }}
            </small>
          </div>
        </div>

        <!-- === Validita' === -->
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('amministrazione.matrice_categorie_listini.field_valido_dal') }} *</label>
            <DatePicker
              v-model="form.valido_dal"
              date-format="dd/mm/yy"
              show-icon
              :disabled="isReadOnlyEffective"
              :invalid="campiErrati.includes('valido_dal')"
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
              :invalid="campiErrati.includes('valido_al')"
            />
          </div>
        </div>

        <!-- === Attivo === -->
        <div class="form-field">
          <label>{{ t('common.attivo') }}</label>
          <ToggleSwitch v-model="form.attivo" :disabled="isReadOnlyEffective"
            :invalid="campiErrati.includes('attivo')"
          />
        </div>
      </div>

      <FormFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="close"
      />
    </div>
  </Drawer>
</template>

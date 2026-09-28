<script setup>
// Scopo: drawer CRUD generico per tabelle config (i VOCABOLARI: codice,
//        descrizione, attivo, qualche flag). Renderizza i campi dinamicamente
//        dai metadata backend (information_schema + pg_catalog): text, number,
//        boolean, json, date, e le FK come `LookupSelect` quando la tabella
//        nominata e' ammessa al lookup generico — altrimenti numero, dichiarato.
//        Esclude id e colonne di sistema (audit, tx_id, uid).
// Note: ⭐ Metadata-driven, nessuna riga per tabella: il widget lo decide
//       `widgetPerColonna` (core/utils/campoConfig.js) dal MODELLO, l'etichetta
//       e' `config_panel.campi.<colonna>` con ripiego fail-visible sul nome.
//       Fino al 2026-09-21 l'etichetta ERA il nome della colonna, le FK erano
//       id grezzi e le date caselle di testo (piano-be-fe-magazzino-anagrafiche-
//       fuori-dal-pannello-config §1). ⛔ Le entita' con FK «vere» (anagrafiche)
//       non stanno qui: hanno il loro drawer (`EntityFormDrawer` o dedicato).
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useInjectReadonly } from '../composables/useReadonlyMode'
import { useApiHandler } from '../composables/useApiHandler'
import { DATE_FORMAT, DRAWER_WIDTH } from '../constants'
import { NAV_ICONS } from '../navigation'
import { labelOrCode } from '../utils/i18nLabel'
import { WIDGET, chiaveEtichettaCampo, widgetPerColonna } from '../utils/campoConfig'
import { parseIsoDate, toDateStringOrNull } from '../utils/date'
import FormFooter from './FormFooter.vue'
import DrawerTitle from './DrawerTitle.vue'
import LookupSelect from './LookupSelect.vue'
import Drawer from 'primevue/drawer'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import ToggleSwitch from 'primevue/toggleswitch'
import Textarea from 'primevue/textarea'
import DatePicker from 'primevue/datepicker'
import {
  getConfigTableMetadata, getConfigRecord, createConfigRecord, updateConfigRecord,
} from '../api/configTables'
import { useDrawerContentReady } from '../composables/useDrawerContentReady'
import { useDrawerFormPreserve, gestoreVisibile } from '../composables/useDrawerFormPreserve'



const props = defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  rel: { type: String, required: true },
  label: { type: String, default: '' },
  recordId: { type: Number, default: null }
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const emit = defineEmits(['update:visible', 'saved'])

const { t, te } = useI18n()
const isReadonly = useInjectReadonly()
// `campiErrati`: il BE nomina la colonna da correggere (vincolo a una colonna,
// NOT NULL, trigger) e qui si accende l'input — e' l'unico consumatore del
// campo che il service spedisce, senza questo binding il canale finiva nel toast.
const { execute, loading, campiErrati } = useApiHandler()

const columns = ref([])
const form = ref({})
// La fotografia del form all'apertura (BB useDrawerFormPreserve): serve al
// DELTA dell'edit (si manda solo cio' che e' cambiato) e alle modifiche non
// salvate — conferma alla chiusura, «Modifica» arancio. Prima il drawer ne
// teneva una copia propria.
const {
  fissa, modificato, chiudiConConferma, fotografia,
} = useDrawerFormPreserve(form, { visibile: () => props.visible })
const chiudi = () => chiudiConConferma(() => emit('update:visible', false))

// ⛔ Il drawer e' UNO per il pannello e cambia tabella con `rel`: il metadata
// va azzerato, o la seconda tabella si apre col form della prima (e il verbo
// del pannello rifiuta le colonne che la tabella non ha,
// `E_PANNELLO_CAMPO_NON_AMMESSO` — fino al 2026-09-25 le scartava in silenzio).
watch(() => props.rel, () => { columns.value = [] })

// Colonne editabili (esclude id), ciascuna col suo widget, la sua etichetta e
// se e' OBBLIGATORIA per l'operatore: NOT NULL senza default del DB (un
// `attivo NOT NULL DEFAULT true` non lo e'; un boolean mai, ha sempre un valore).
const editableColumns = computed(() =>
  columns.value
    .filter(c => !c.is_pk)
    .map(c => {
      const widget = widgetPerColonna(c)
      return {
        ...c,
        widget,
        etichetta: labelOrCode(t, te, chiaveEtichettaCampo(c), c.name),
        obbligatoria: !c.nullable && !c.has_default && widget !== WIDGET.BOOLEAN,
      }
    }),
)

// Scopo: il valore come lo vuole il form — le date come `Date` (il DatePicker
//        non legge una stringa ISO), il json come testo, il resto com'e'.
function versoForm(col, val) {
  if (col.widget === WIDGET.JSON) return JSON.stringify(val, null, 2)
  if (col.widget === WIDGET.DATE) return parseIsoDate(val)
  return val
}

// Scopo: il valore come lo vuole il payload — le date in `YYYY-MM-DD`
//        (`toDateStringOrNull`: una data invalida diventa `null`, non «Invalid Date»).
function versoPayload(col, val) {
  if (col.widget === WIDGET.JSON && typeof val === 'string') {
    try { return JSON.parse(val) } catch { return {} }
  }
  if (col.widget === WIDGET.DATE) return toDateStringOrNull(val)
  return val
}

// Scopo: confronto per il delta del PATCH (json e date si confrontano
//        normalizzati, non per identita' di oggetto).
function uguali(col, a, b) {
  if (col.widget === WIDGET.JSON) return JSON.stringify(versoPayload(col, a)) === JSON.stringify(versoPayload(col, b))
  if (col.widget === WIDGET.DATE) return toDateStringOrNull(a) === toDateStringOrNull(b)
  return a === b
}

// Carica metadata + dati al primo open
watch(() => props.visible, async (val) => {
  if (!val) return

  // Carica metadata se non gia' presenti per questa rel
  if (columns.value.length === 0) {
    // Metadata non letto: il toast dice perche', e il drawer si richiude
    // (senza colonne non c'e' un form da mostrare).
    const meta = await execute(() => getConfigTableMetadata(props.rel))
    if (meta === null) {
      emit('update:visible', false)
      return
    }
    columns.value = meta.columns
  }

  // Reset form: inizializza ogni campo dal default DB (col.default) quando noto,
  // così i boolean rispettano il default reale della colonna (es. chiude_pratica
  // / obbligatorio = false) invece di forzare true. Fallback al neutro per tipo
  // se il default non e' un literal riconoscibile lato backend.
  const newForm = {}
  for (const col of editableColumns.value) {
    if (col.default !== null && col.default !== undefined) {
      newForm[col.name] = versoForm(col, col.default)
    } else if (col.widget === WIDGET.BOOLEAN) newForm[col.name] = true
    else if (col.widget === WIDGET.TEXT) newForm[col.name] = ''
    else newForm[col.name] = null
  }

  // Se edit, carica dati esistenti
  if (props.mode === 'edit' && props.recordId) {
    const data = await execute(() => getConfigRecord(props.rel, props.recordId))
    if (data === null) {
      emit('update:visible', false)
      return
    }
    for (const col of editableColumns.value) {
      if (data[col.name] !== undefined) newForm[col.name] = versoForm(col, data[col.name])
    }
  }

  form.value = newForm
  fissa()
})

// Il payload del salvataggio, calcolato dal form: lo legge `canSave` per
// sapere se in modifica c'e' qualcosa da mandare, e `handleSave` lo spedisce.
const payload = computed(() => {
  const dati = {}
  const isCreate = props.mode === 'create'

  for (const col of editableColumns.value) {
    const val = versoPayload(col, form.value[col.name])

    if (isCreate) {
      // Create: manda i campi con un valore; un campo vuoto NON viaggia, cosi'
      // vale il default del DB (un `null` esplicito lo scavalcherebbe). Il
      // boolean viaggia sempre: `false` e' un valore.
      if (col.widget === WIDGET.BOOLEAN || (val !== undefined && val !== null && val !== '')) dati[col.name] = val
    } else if (!uguali(col, form.value[col.name], fotografia.value?.[col.name])) {
      // Edit: manda SOLO i campi modificati (delta) — un trigger di lock su una
      // colonna non toccata non deve scattare.
      dati[col.name] = val
    }
  }
  return dati
})

// Validazione minima: almeno descrizione non vuota (se presente); in modifica
// serve anche un campo cambiato.
// ⛔ Un delta vuoto non parte: il verbo lo rifiuta (`E_PANNELLO_DATI_VUOTI`,
// dal 2026-09-25; prima era «Record non trovato»). Il confronto e' quello del
// delta (`uguali`), non `modificato` del BB: un json riformattato o una data
// ricreata uguale non sono una modifica da mandare.
const canSave = computed(() => {
  if (props.mode !== 'create' && Object.keys(payload.value).length === 0) return false
  const desc = form.value.descrizione
  if (desc !== undefined && typeof desc === 'string') return desc.trim().length > 0
  return true
})

async function handleSave() {
  if (!canSave.value) return
  const isCreate = props.mode === 'create'
  const dati = payload.value
  const msg = isCreate ? t('config_panel.record_creato') : t('config_panel.record_salvato')

  const result = await execute(
    () => isCreate
      ? createConfigRecord(props.rel, dati)
      : updateConfigRecord(props.rel, props.recordId, dati),
    { successMessage: msg }
  )

  if (result !== null) {
    emit('saved')
    emit('update:visible', false)
  }
}
const suVisibile = gestoreVisibile(emit, chiudi)
</script>

<template>
  <Drawer
    :visible="visible"
    @update:visible="suVisibile"
    position="right"
    :style="{ width: DRAWER_WIDTH.SIMPLE }"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :modificato="modificato"
        :action="mode === 'create' ? t('common.new') : t('common.edit')"
        :title="label"
        :icon="NAV_ICONS.TABELLE"
      />
    </template>
    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">
        <template v-for="col in editableColumns" :key="col.name">
          <div class="form-field">
            <label>{{ col.etichetta }}{{ col.obbligatoria ? ' *' : '' }}</label>

            <!-- FK verso una tabella ammessa al lookup generico. ⚠️ `value-field`
                 dalla FK: non tutte puntano a `id` (`esito` → `codice_interno`). -->
            <LookupSelect
              v-if="col.widget === WIDGET.LOOKUP"
              v-model="form[col.name]"
              :rel="col.references"
              :value-field="col.references_column"
              :invalid="campiErrati.includes(col.name)"
              show-clear
            />

            <!-- FK verso una tabella che il lookup non serve: valore a mano,
                 dichiarato — numero o testo secondo la colonna -->
            <template v-else-if="col.widget === WIDGET.FK_ID">
              <InputNumber v-if="col.type === 'number'" v-model="form[col.name]" :use-grouping="false" :invalid="campiErrati.includes(col.name)" />
              <InputText v-else v-model="form[col.name]" :invalid="campiErrati.includes(col.name)" />
              <small class="app-text-muted">{{ t('config_panel.hint_fk_id', { tabella: col.references, colonna: col.references_column }) }}</small>
            </template>

            <DatePicker
              v-else-if="col.widget === WIDGET.DATE"
              v-model="form[col.name]"
              :date-format="DATE_FORMAT"
              :invalid="campiErrati.includes(col.name)"
              show-icon
            />

            <InputNumber v-else-if="col.widget === WIDGET.NUMBER" v-model="form[col.name]" :use-grouping="false" :invalid="campiErrati.includes(col.name)" />

            <ToggleSwitch v-else-if="col.widget === WIDGET.BOOLEAN" v-model="form[col.name]" :invalid="campiErrati.includes(col.name)" />

            <Textarea v-else-if="col.widget === WIDGET.JSON" v-model="form[col.name]" rows="4" auto-resize :invalid="campiErrati.includes(col.name)" />

            <InputText v-else v-model="form[col.name]" :invalid="campiErrati.includes(col.name)" />
          </div>
        </template>
      </div>

      <FormFooter
        :loading="loading"
        :disabled="!canSave"
        @save="handleSave"
        @cancel="chiudi"
      />
    </div>
  </Drawer>
</template>

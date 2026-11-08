<script setup>
// Scopo: Drawer unico creazione/modifica fornitore.
// In creazione: SoggettoResolver + campi editabili + contatto/indirizzo inline.
// In edit: banner soggetto readonly + campi editabili + badge contatti/indirizzi/conti.
// Pattern analogo a SoggettoDrawer: payload unificato al backend in transazione atomica.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFornitoriStore } from '../stores/fornitori'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { useContattoForm } from '../composables/useContattoForm'
import { useIndirizzoSoggettoForm } from '../composables/useIndirizzoSoggettoForm'
import { raccogliFormInline } from '../composables/raccogliFormInline'
import { useCodiceField } from '../../core/composables/useCodiceField'
import { DRAWER_WIDTH, TIPO_RUOLO, MANAGE_ICONS, DATE_FORMAT } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { statoFornitoreSeverity } from '../../core/utils/severity'
import { toDateString, parseIsoDate } from '../../core/utils/date'
import SoggettoResolver from './SoggettoResolver.vue'
import SoggettoMessageBanner from '../../core/components/SoggettoMessageBanner.vue'
import SoggettoPreviewBadges from './SoggettoPreviewBadges.vue'
import ContattoForm from './ContattoForm.vue'
import IndirizzoSoggettoForm from './IndirizzoSoggettoForm.vue'
import AppDrawer from '../../core/components/AppDrawer.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'
import DatePicker from 'primevue/datepicker'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const { t } = useI18n()
const store = useFornitoriStore()
const { execute, loading, campiErrati } = useApiHandler()
const contatto = useContattoForm()
const contattoErrors = ref([])
const indirizzo = useIndirizzoSoggettoForm()
const codiceField = useCodiceField('anagrafiche', 'fornitori')

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  fornitoreId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

// Form unificato
const form = ref({})
const detail = ref(null)

// SoggettoResolver (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)

// Modifiche non salvate (BB useDrawerFormPreserve): il form, il soggetto
// scelto in creazione, e contatto e indirizzo inline (il Salva della creazione
// li manda insieme al fornitore).
// ⚠️ Senza condizione su `isEdit`: dopo la creazione il padre porta `mode` a
//    'edit' a drawer aperto, e togliere le chiavi farebbe sembrare «modificato»
//    un form appena salvato. In modifica i due form non si vedono e non cambiano.
const formSalvato = computed(() => ({
  ...form.value,
  soggetto_id: soggettoSelezionato.value?.id ?? null,
  ...raccogliFormInline({ contatto, indirizzo }),
}))
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(formSalvato, { visibile: () => props.visible })

function defaultForm() {
  return {
    codice: null,
    valuta_id: null, modalita_pagamento_id: null, termine_pagamento_id: null,
    giorni_pagamento: null, fine_mese: false,
    split_payment: false, ritenuta_acconto: false, ritenuta_aliquota: null,
    regime_fiscale: null, bollo_esente: false,
    canale_fe: null, pec_email: null,
    rating: null, qualifica_scadenza: null,
    note: null, stato_fornitore_id: null
  }
}

function resetForm() {
  soggettoSelezionato.value = null
  detail.value = null
  form.value = defaultForm()
  contatto.reset()
  contattoErrors.value = []
  indirizzo.reset()
}

// Scopo: Popola form dai dati dettaglio (edit mode).
function populateFormFromDetail(d) {
  form.value = {
    valuta_id: d.valuta_id,
    modalita_pagamento_id: d.modalita_pagamento_id,
    termine_pagamento_id: d.termine_pagamento_id,
    giorni_pagamento: d.giorni_pagamento,
    fine_mese: d.fine_mese ?? false,
    split_payment: d.split_payment ?? false,
    ritenuta_acconto: d.ritenuta_acconto ?? false,
    ritenuta_aliquota: d.ritenuta_aliquota,
    regime_fiscale: d.regime_fiscale,
    bollo_esente: d.bollo_esente ?? false,
    canale_fe: d.canale_fe,
    pec_email: d.pec_email,
    rating: d.rating,
    qualifica_scadenza: parseIsoDate(d.qualifica_scadenza),
    note: d.note,
    stato_fornitore_id: d.stato_fornitore_id
  }
}

function onSoggettoSelezionato(data) { soggettoSelezionato.value = data }
function onSoggettoCreato(data) { soggettoSelezionato.value = data }
function clearSoggetto() { soggettoSelezionato.value = null }

// Carica dati. ⚠️ Anche su `mode` e id: dopo la CREATE il padre riapre in
// modifica (`useDrawerSavedListRefresh` → `editRow`) col drawer GIA' visibile,
// e col solo `visible` il dettaglio non si rileggeva (codice e stato assenti,
// form ancora quello della creazione).
watch([() => props.visible, () => props.mode, () => props.fornitoreId], async ([val]) => {
  if (!val) return
  if (!codiceField.loaded.value) codiceField.load()
  if (isEdit.value && props.fornitoreId) {
    const d = await store.fetchDetail(props.fornitoreId)
    detail.value = d
    populateFormFromDetail(d)
  } else {
    resetForm()
    // Carica matrice indirizzi obbligatori per ruolo FO
    indirizzo.loadMatriceRuolo(TIPO_RUOLO.FORNITORE)
  }
  fissa()
})

// Scopo: Costruisce il payload dei campi editabili.
function buildEditablePayload() {
  const f = form.value
  const payload = {
    valuta_id: f.valuta_id || null,
    modalita_pagamento_id: f.modalita_pagamento_id || null,
    termine_pagamento_id: f.termine_pagamento_id || null,
    giorni_pagamento: f.giorni_pagamento || null,
    fine_mese: f.fine_mese,
    split_payment: f.split_payment,
    ritenuta_acconto: f.ritenuta_acconto,
    ritenuta_aliquota: f.ritenuta_aliquota,
    regime_fiscale: f.regime_fiscale || null,
    bollo_esente: f.bollo_esente,
    canale_fe: f.canale_fe || null,
    pec_email: f.pec_email || null,
    rating: f.rating,
    // ⛔ Mai `toISOString()` su una data: il DatePicker da' la mezzanotte
    //    LOCALE, e in UTC diventa il giorno prima — fino al 2026-10-04 la
    //    scadenza si salvava un giorno prima di quella scelta.
    qualifica_scadenza: toDateString(f.qualifica_scadenza),
    note: f.note || null,
  }
  if (isEdit.value) {
    payload.stato_fornitore_id = f.stato_fornitore_id
  }
  return payload
}

// Scopo: Salva fornitore (create o update).
async function onSave() {
  if (isEdit.value) {
    const result = await execute(
      () => store.update(props.fornitoreId, buildEditablePayload()),
      { successMessage: t('anagrafiche.fornitori.fornitore_salvato') }
    )
    // Salvato: la fotografia e' il form di adesso (il parent decide se chiudere o riaprire in edit).
    if (result !== null) { fissa(); emit('saved', result) }
  } else {
    // Validazione contatto inline (Fase 5): regola unificata via composable
    // useContattoForm.classify() — mirror della regola backend.
    // EMPTY → skip; PARTIAL → blocca con messaggio; VALID → invia.
    // (Bug fix: prima si guardava solo nominativo, scartando email/telefono
    // se compilati senza nominativo — ora il composable cattura il caso.)
    if (contatto.isFilled()) {
      contattoErrors.value = contatto.validate()
      if (contattoErrors.value.length > 0) return
    } else {
      contattoErrors.value = []
    }

    const sogg = soggettoSelezionato.value
    if (!sogg) return
    const payload = {
      soggetto_id: sogg.id,
      ...buildEditablePayload(),
    }
    // Codice manuale (solo se non auto-generato e compilato)
    if (codiceField.isEditable.value && form.value.codice) {
      payload.codice = form.value.codice.trim()
    }
    // Contatto solo se compilato
    if (contatto.isFilled()) {
      payload.contatto = { ...contatto.form }
    }
    // Indirizzi inline (se compilati)
    if (indirizzo.hasIndirizzi.value) {
      payload.indirizzi = indirizzo.toPayloadArray()
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('anagrafiche.fornitori.fornitore_creato') }
    )
    // Salvato: la fotografia e' il form di adesso (il parent decide se chiudere o riaprire in edit).
    if (result !== null) { fissa(); emit('saved', result) }
  }
}

const canSave = computed(() => isEdit.value || !!soggettoSelezionato.value)

</script>

<template>
  <!-- Il chrome e' di AppDrawer dal 2026-10-03
       (work-done/analisi-fe-chrome-drawer.md). -->
  <AppDrawer
    :visible="props.visible"
    :title="t('anagrafiche.fornitori.fornitore')"
    :icon="NAV_ICONS.FORNITORI"
    :action="isEdit ? t('common.edit') : t('common.new')"
    :width="DRAWER_WIDTH.STANDARD"
    :modificato="modificato"
    :conferma-uscita="chiudiConConferma"
    :loading="loading"
    :save-disabled="!canSave"
    @update:visible="(v) => emit('update:visible', v)"
    @cancel="emit('cancelled')"
    @save="onSave"
  >
    <div class="form-grid">

      <!-- === Soggetto === -->
      <h4>{{ t('anagrafiche.fornitori.section_soggetto') }}</h4>
      <template v-if="!isEdit">
        <div v-if="soggettoSelezionato">
          <SoggettoMessageBanner
            :ragione-sociale="soggettoSelezionato.ragione_sociale"
            :id-fiscale="soggettoSelezionato.cf || soggettoSelezionato.piva"
          />
          <Button :label="t('resolver.change')" :icon="MANAGE_ICONS.EDIT"
            text size="small" class="mt-1" @click="clearSoggetto" />
        </div>
        <div v-else>
          <Button :label="t('resolver.open')" :icon="MANAGE_ICONS.RICERCA"
            outlined @click="resolverVisible = true" />
        </div>
      </template>
      <div v-if="isEdit && detail">
        <SoggettoMessageBanner
          :ragione-sociale="detail.ragione_sociale_completa"
          :id-fiscale="detail.codice_fiscale || detail.partita_iva"
        />
      </div>

      <!-- === Codice manuale (solo create, se non auto-generato) === -->
      <div v-if="!isEdit && codiceField.isEditable.value" class="form-field">
        <label>{{ t('anagrafiche.fornitori.col_codice') }}</label>
        <InputText v-model="form.codice" class="app-codice-input" :placeholder="t('anagrafiche.fornitori.placeholder_codice')"
          :invalid="campiErrati.includes('codice')"
        />
      </div>

      <!-- === Identificativo (solo edit) === -->
      <template v-if="isEdit && detail">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.col_codice') }}</label>
            <InputText :model-value="detail.codice" disabled />
          </div>
          <div class="form-field" style="align-self: flex-end;">
            <Tag :value="detail.stato_descrizione" :severity="statoFornitoreSeverity(detail.stato_codice_interno)"
              style="font-size: 0.95rem; padding: 0.5rem 1rem;" />
          </div>
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_stato') }}</label>
          <LookupSelect v-model="form.stato_fornitore_id" rel="config.stati_fornitore" />
        </div>
      </template>

      <!-- Sezioni dati fornitore: visibili solo dopo selezione soggetto (create) o sempre (edit) -->
      <template v-if="isEdit || soggettoSelezionato">

      <!-- === Pagamento === -->
      <h4>{{ t('anagrafiche.fornitori.section_pagamento') }}</h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_modalita_pagamento') }}</label>
          <LookupSelect v-model="form.modalita_pagamento_id" rel="config.modalita_pagamento"
            :placeholder="t('anagrafiche.fornitori.select_modalita')" show-clear />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_valuta') }}</label>
          <LookupSelect v-model="form.valuta_id" rel="config.valute"
            :placeholder="t('anagrafiche.fornitori.select_valuta')" show-clear />
        </div>
      </div>
      <div class="form-grid-3col">
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_termine_pagamento') }}</label>
          <LookupSelect v-model="form.termine_pagamento_id" rel="config.termini_pagamento"
            :placeholder="t('anagrafiche.fornitori.select_termine')" show-clear />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_giorni_pagamento') }}</label>
          <InputNumber v-model="form.giorni_pagamento" :min="0" :max="999" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_fine_mese') }}</label>
          <Checkbox v-model="form.fine_mese" :binary="true" input-id="fine_mese" />
        </div>
      </div>

      <!-- === Fiscale === -->
      <h4>{{ t('anagrafiche.fornitori.section_fiscale') }}</h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_regime_fiscale') }}</label>
          <InputText v-model="form.regime_fiscale" :placeholder="t('anagrafiche.fornitori.placeholder_regime')" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_split_payment') }}</label>
          <Checkbox v-model="form.split_payment" :binary="true" input-id="split_payment" />
        </div>
      </div>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_bollo_esente') }}</label>
          <Checkbox v-model="form.bollo_esente" :binary="true" input-id="bollo_esente" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_ritenuta_acconto') }}</label>
          <Checkbox v-model="form.ritenuta_acconto" :binary="true" input-id="ritenuta_acconto" />
        </div>
      </div>
      <div v-if="form.ritenuta_acconto" class="form-field">
        <label>{{ t('anagrafiche.fornitori.field_ritenuta_aliquota') }}</label>
        <InputNumber v-model="form.ritenuta_aliquota" :min="0" :max="100"
          suffix="%" mode="decimal" :min-fraction-digits="2" />
      </div>

      <!-- === FE / SDI === -->
      <h4>{{ t('anagrafiche.fornitori.section_fe_sdi') }}</h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_canale_fe') }}</label>
          <InputText v-model="form.canale_fe" maxlength="7" :placeholder="t('anagrafiche.fornitori.placeholder_canale_fe')" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_pec_email') }}</label>
          <InputText v-model="form.pec_email" :placeholder="t('anagrafiche.fornitori.placeholder_pec')" />
        </div>
      </div>

      <!-- === Rating === -->
      <h4>{{ t('anagrafiche.fornitori.section_rating') }}</h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_rating') }}</label>
          <InputNumber v-model="form.rating" :min="0" :max="100" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.fornitori.field_qualifica_scadenza') }}</label>
          <DatePicker v-model="form.qualifica_scadenza" :date-format="DATE_FORMAT" show-icon />
        </div>
      </div>

      <!-- === Note === -->
      <h4>{{ t('anagrafiche.fornitori.section_note') }}</h4>
      <div class="form-field">
        <Textarea v-model="form.note" rows="3" auto-resize
          :invalid="campiErrati.includes('note')"
        />
      </div>

      <!-- === Contatto inline (solo creazione) === -->
      <template v-if="!isEdit">
        <div class="app-drawer-section">
          <h4>{{ t('anagrafiche.soggetti.section_contatto') }}</h4>
        </div>
        <ContattoForm
          :campi-errati="campiErrati"
          :form="contatto.form"
          :tipi-contatto="contatto.tipiContatto"
          :unita-organizzative="contatto.unitaOrganizzative"
          :errors="contattoErrors"
          :show-u-o="false"
          :disabled="false"
        />
      </template>

      <!-- === Indirizzo inline (solo creazione) === -->
      <template v-if="!isEdit">
        <div class="app-drawer-section">
          <h4>{{ t('anagrafiche.soggetti.section_indirizzo') }}</h4>
        </div>
        <IndirizzoSoggettoForm
          :campi-errati="campiErrati"
          :form="indirizzo.form"
          :is-libera="indirizzo.isLibera.value"
          @update:is-libera="v => indirizzo.isLibera.value = v"
          :tipi-stato="indirizzo.tipiStato.value"
          :stati-lookup="indirizzo.statiLookup"
          :cap-options="indirizzo.capOptions.value"
          :loading-cap="indirizzo.loadingCap.value"
          :auto-clone="indirizzo.autoClone.value"
          @update:auto-clone="v => indirizzo.autoClone.value = v"
          @switch-tipo="indirizzo.switchTipo"
          :indirizzo-warnings="indirizzo.indirizzoWarnings.value"
          :address-not-found="indirizzo.addressNotFound.value"
          :disabled="false"
        />
      </template>

      </template><!-- fine v-if="isEdit || soggettoSelezionato" -->

    </div>

    <!-- Badge indirizzi/contatti/conti — creazione: soggetto preview, edit: ruolo editabile -->
    <SoggettoPreviewBadges v-if="!isEdit && soggettoSelezionato"
      :soggetto-id="soggettoSelezionato.id"
      :tipo-ruolo-codice="TIPO_RUOLO.FORNITORE"
      preview />
    <!-- §1.6: accessi web (solo portale per fornitori, no shop B2C)
         tramite pulsante Web in SoggettoPreviewBadges, apre
         WebAccessiDrawer autonomo. -->
    <SoggettoPreviewBadges v-else-if="isEdit && detail"
      :soggetto-ruolo-id="detail.soggetto_ruolo_id"
      :tipo-ruolo-codice="TIPO_RUOLO.FORNITORE"
      entita-tipo-web="fornitore"
      :entita-id-web="props.fornitoreId"
      :email-iniziale-web="detail?.pec_email || ''" />

    <!-- Sotto-drawer: SoggettoResolver (solo creazione) -->
    <SoggettoResolver
      v-if="!isEdit"
      :visible="resolverVisible"
      :tipo-ruolo-codice="TIPO_RUOLO.FORNITORE"
      @update:visible="v => resolverVisible = v"
      @soggetto-selezionato="onSoggettoSelezionato"
      @soggetto-creato="onSoggettoCreato"
      @annullato="resolverVisible = false"
    />
  </AppDrawer>
</template>

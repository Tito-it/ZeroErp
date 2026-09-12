<script setup>
// Scopo: Drawer unico creazione/modifica fornitore.
// In creazione: SoggettoResolver + campi editabili + contatto/indirizzo inline.
// In edit: banner soggetto readonly + campi editabili + badge contatti/indirizzi/conti.
// Pattern analogo a SoggettoDrawer: payload unificato al backend in transazione atomica.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFornitoriStore } from '../stores/fornitori'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useContattoForm } from '../../core/composables/useContattoForm'
import { useIndirizzoSoggettoForm } from '../../core/composables/useIndirizzoSoggettoForm'
import { useCodiceField } from '../../core/composables/useCodiceField'
import { DRAWER_WIDTH, TIPO_RUOLO, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { statoFornitoreSeverity } from '../../core/utils/severity'
import SoggettoResolver from '../../core/components/SoggettoResolver.vue'
import SoggettoMessageBanner from '../../core/components/SoggettoMessageBanner.vue'
import SoggettoPreviewBadges from '../../core/components/SoggettoPreviewBadges.vue'
import ContattoForm from '../../core/components/ContattoForm.vue'
import IndirizzoSoggettoForm from '../../core/components/IndirizzoSoggettoForm.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import Drawer from 'primevue/drawer'
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
const isReadonly = useInjectReadonly()
const contatto = useContattoForm()
const contattoErrors = ref([])
const indirizzo = useIndirizzoSoggettoForm()
const codiceField = useCodiceField('anagrafiche', 'fornitori')

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  fornitoreId: { type: Number, default: null }
})

// Contenuto deferito a fine animazione: senza, i figli pesanti si montano
// durante lo slide-in e il drawer «rimbalza» (`feedback_content_ready_after_show`).
// ⛔ Il reset alla chiusura lo fa il composable: NON aggiungerlo nel watch.
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

// Form unificato
const form = ref({})
const detail = ref(null)

// SoggettoResolver (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)

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
    qualifica_scadenza: d.qualifica_scadenza ? new Date(d.qualifica_scadenza) : null,
    note: d.note,
    stato_fornitore_id: d.stato_fornitore_id
  }
}

function onSoggettoSelezionato(data) { soggettoSelezionato.value = data }
function onSoggettoCreato(data) { soggettoSelezionato.value = data }
function clearSoggetto() { soggettoSelezionato.value = null }

// Carica dati
watch(() => props.visible, async (val) => {
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
    qualifica_scadenza: f.qualifica_scadenza
      ? (f.qualifica_scadenza instanceof Date ? f.qualifica_scadenza.toISOString().slice(0, 10) : f.qualifica_scadenza)
      : null,
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
    if (result !== null) emit('saved', result)
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
    if (result !== null) emit('saved', result)
  }
}

const canSave = computed(() => isEdit.value || !!soggettoSelezionato.value)

const onClose = useDrawerClose(emit, 'cancelled')
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    :dismissable="true"
    @update:visible="val => emit('update:visible', val)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('anagrafiche.fornitori.fornitore')"
        :icon="NAV_ICONS.FORNITORI"
      />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">

        <!-- === Soggetto === -->
        <h4>{{ t('anagrafiche.fornitori.section_soggetto') }}</h4>
        <template v-if="!isEdit">
          <div v-if="soggettoSelezionato" class="mb-3">
            <SoggettoMessageBanner
              :ragione-sociale="soggettoSelezionato.ragione_sociale"
              :id-fiscale="soggettoSelezionato.cf || soggettoSelezionato.piva"
            />
            <Button :label="t('resolver.change')" :icon="MANAGE_ICONS.EDIT"
              text size="small" class="mt-1" @click="clearSoggetto" />
          </div>
          <div v-else>
            <Button :label="t('resolver.open')" icon="pi pi-search"
              outlined class="w-full" @click="resolverVisible = true" />
          </div>
        </template>
        <div v-if="isEdit && detail" class="mb-3">
          <SoggettoMessageBanner
            :ragione-sociale="detail.ragione_sociale_completa"
            :id-fiscale="detail.codice_fiscale || detail.partita_iva"
          />
        </div>

        <!-- === Codice manuale (solo create, se non auto-generato) === -->
        <div v-if="!isEdit && codiceField.isEditable.value" class="form-field">
          <label>{{ t('anagrafiche.fornitori.col_codice') }}</label>
          <InputText v-model="form.codice" class="w-full" :placeholder="t('anagrafiche.fornitori.placeholder_codice')"
            :invalid="campiErrati.includes('codice')"
          />
        </div>

        <!-- === Identificativo (solo edit) === -->
        <template v-if="isEdit && detail">
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('anagrafiche.fornitori.col_codice') }}</label>
              <InputText :model-value="detail.codice" disabled class="w-full" />
            </div>
            <div class="form-field" style="align-self: flex-end;">
              <Tag :value="detail.stato_descrizione" :severity="statoFornitoreSeverity(detail.stato_codice_interno)"
                style="font-size: 0.95rem; padding: 0.5rem 1rem;" />
            </div>
          </div>
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_stato') }}</label>
            <LookupSelect v-model="form.stato_fornitore_id" rel="config.stati_fornitore" class="w-full" />
          </div>
        </template>

        <!-- Sezioni dati fornitore: visibili solo dopo selezione soggetto (create) o sempre (edit) -->
        <template v-if="isEdit || soggettoSelezionato">

        <!-- === Pagamento === -->
        <h4 class="mt-3">{{ t('anagrafiche.fornitori.section_pagamento') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_modalita_pagamento') }}</label>
            <LookupSelect v-model="form.modalita_pagamento_id" rel="config.modalita_pagamento" class="w-full"
              :placeholder="t('anagrafiche.fornitori.select_modalita')" show-clear />
          </div>
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_valuta') }}</label>
            <LookupSelect v-model="form.valuta_id" rel="config.valute" class="w-full"
              :placeholder="t('anagrafiche.fornitori.select_valuta')" show-clear />
          </div>
        </div>
        <div class="form-grid-3col">
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_termine_pagamento') }}</label>
            <LookupSelect v-model="form.termine_pagamento_id" rel="config.termini_pagamento" class="w-full"
              :placeholder="t('anagrafiche.fornitori.select_termine')" show-clear />
          </div>
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_giorni_pagamento') }}</label>
            <InputNumber v-model="form.giorni_pagamento" :min="0" :max="999" class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_fine_mese') }}</label>
            <Checkbox v-model="form.fine_mese" :binary="true" input-id="fine_mese" />
          </div>
        </div>

        <!-- === Fiscale === -->
        <h4 class="mt-3">{{ t('anagrafiche.fornitori.section_fiscale') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_regime_fiscale') }}</label>
            <InputText v-model="form.regime_fiscale" class="w-full" :placeholder="t('anagrafiche.fornitori.placeholder_regime')" />
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
          <InputNumber v-model="form.ritenuta_aliquota" class="w-full" :min="0" :max="100"
            suffix="%" mode="decimal" :min-fraction-digits="2" />
        </div>

        <!-- === FE / SDI === -->
        <h4 class="mt-3">{{ t('anagrafiche.fornitori.section_fe_sdi') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_canale_fe') }}</label>
            <InputText v-model="form.canale_fe" class="w-full" maxlength="7" :placeholder="t('anagrafiche.fornitori.placeholder_canale_fe')" />
          </div>
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_pec_email') }}</label>
            <InputText v-model="form.pec_email" class="w-full" :placeholder="t('anagrafiche.fornitori.placeholder_pec')" />
          </div>
        </div>

        <!-- === Rating === -->
        <h4 class="mt-3">{{ t('anagrafiche.fornitori.section_rating') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_rating') }}</label>
            <InputNumber v-model="form.rating" class="w-full" :min="0" :max="100" />
          </div>
          <div class="form-field">
            <label>{{ t('anagrafiche.fornitori.field_qualifica_scadenza') }}</label>
            <DatePicker v-model="form.qualifica_scadenza" class="w-full" dateFormat="dd/mm/yy" show-icon />
          </div>
        </div>

        <!-- === Note === -->
        <h4 class="mt-3">{{ t('anagrafiche.fornitori.section_note') }}</h4>
        <div class="form-field">
          <Textarea v-model="form.note" class="w-full" rows="3" auto-resize
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

      <FormFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="onClose" />
    </div>

    <!-- Sotto-drawer: SoggettoResolver (solo creazione) -->
    <SoggettoResolver
      v-if="!isEdit"
      :visible="resolverVisible"
      tipo-ruolo-codice="FO"
      @update:visible="v => resolverVisible = v"
      @soggetto-selezionato="onSoggettoSelezionato"
      @soggetto-creato="onSoggettoCreato"
      @annullato="resolverVisible = false"
    />

  </Drawer>
</template>

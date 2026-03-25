<script setup>
// Scopo: Drawer unico creazione/modifica fornitore.
// In creazione: SoggettoResolver + campi editabili.
// In edit: banner soggetto readonly + campi editabili + gestione contatti/indirizzi/conti.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFornitoriStore } from '../stores/fornitori'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookup } from '../../core/composables/useLookup'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { lookupCodici } from '../../core/apiCore'
import { DRAWER_WIDTH } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { statoFornitoreSeverity } from '../../core/utils/severity'
import SoggettoResolver from '../../core/components/SoggettoResolver.vue'
import SoggettoMessageBanner from '../../core/components/SoggettoMessageBanner.vue'
import ContattiSoggettoDrawer from '../../core/components/ContattiSoggettoDrawer.vue'
import IndirizziSoggettoDrawer from '../../core/components/IndirizziSoggettoDrawer.vue'
import ContiBancariDrawer from '../../core/components/ContiBancariDrawer.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import Drawer from 'primevue/drawer'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'
import DatePicker from 'primevue/datepicker'
import Textarea from 'primevue/textarea'
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const { t } = useI18n()
const store = useFornitoriStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

// Lookup
const modalitaPagamento = useLookup(() => lookupCodici('config.modalita_pagamento'), { immediate: true })
const terminiPagamento = useLookup(() => lookupCodici('config.termini_pagamento'), { immediate: true })
const valute = useLookup(() => lookupCodici('config.valute'), { immediate: true })
const statiFornitore = useLookup(() => lookupCodici('config.stati_fornitore'), { immediate: true })

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

function defaultForm() {
  return {
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
  if (isEdit.value && props.fornitoreId) {
    const d = await store.fetchDetail(props.fornitoreId)
    detail.value = d
    populateFormFromDetail(d)
  } else {
    resetForm()
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
    ritenuta_aliquota: f.ritenuta_acconto ? f.ritenuta_aliquota : null,
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
      { successMessage: t('fornitori.fornitore_salvato') }
    )
    if (result !== null) emit('saved', result)
  } else {
    const sogg = soggettoSelezionato.value
    if (!sogg) return
    const payload = {
      soggetto_id: sogg.id,
      ...buildEditablePayload(),
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('fornitori.fornitore_creato') }
    )
    if (result !== null) emit('saved', result)
  }
}

const canSave = computed(() => isEdit.value || !!soggettoSelezionato.value)

// Sotto-drawer
const contattiDrawer = ref({ visible: false })
const indirizziDrawer = ref({ visible: false })
const contiBancariDrawer = ref({ visible: false })
const indirizziSoggettoDrawer = ref({ visible: false })
function openContatti() { contattiDrawer.value = { visible: true } }
function openIndirizzi() { indirizziDrawer.value = { visible: true } }
function openContiBancari() { contiBancariDrawer.value = { visible: true } }
// Scopo: Apre sotto-drawer indirizzi a livello soggetto (create mode).
function openIndirizziSoggetto() { indirizziSoggettoDrawer.value = { visible: true } }

function onClose() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.STANDARD }"
    @update:visible="val => emit('update:visible', val)"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('fornitori.fornitore')"
        icon="pi pi-clipboard"
      />
    </template>

    <div :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">

        <!-- === Soggetto === -->
        <h4>{{ t('fornitori.section_soggetto') }}</h4>
        <template v-if="!isEdit">
          <div v-if="soggettoSelezionato" class="mb-3">
            <SoggettoMessageBanner
              :ragione-sociale="soggettoSelezionato.ragione_sociale"
              :codice-fiscale="soggettoSelezionato.cf"
            />
            <Button :label="t('resolver.change')" icon="pi pi-pencil"
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
            :codice-fiscale="detail.codice_fiscale"
          />
        </div>

        <!-- === Identificativo (solo edit) === -->
        <template v-if="isEdit && detail">
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('fornitori.col_codice') }}</label>
              <InputText :model-value="detail.codice" disabled class="w-full" />
            </div>
            <div class="form-field" style="align-self: flex-end;">
              <Tag :value="detail.stato_descrizione" :severity="statoFornitoreSeverity(detail.stato_codice)"
                style="font-size: 0.95rem; padding: 0.5rem 1rem;" />
            </div>
          </div>
          <div class="form-field">
            <label>{{ t('fornitori.field_stato') }}</label>
            <Select v-model="form.stato_fornitore_id" :options="statiFornitore.items.value" :loading="statiFornitore.loading.value"
              option-label="descrizione" option-value="id" class="w-full" />
          </div>
        </template>

        <!-- === Pagamento === -->
        <h4 class="mt-3">{{ t('fornitori.section_pagamento') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('fornitori.field_modalita_pagamento') }}</label>
            <Select v-model="form.modalita_pagamento_id" :options="modalitaPagamento.items.value" :loading="modalitaPagamento.loading.value"
              option-label="descrizione" option-value="id" class="w-full"
              :placeholder="t('fornitori.select_modalita')" show-clear />
          </div>
          <div class="form-field">
            <label>{{ t('fornitori.field_termine_pagamento') }}</label>
            <Select v-model="form.termine_pagamento_id" :options="terminiPagamento.items.value" :loading="terminiPagamento.loading.value"
              option-label="descrizione" option-value="id" class="w-full"
              :placeholder="t('fornitori.select_termine')" show-clear />
          </div>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('fornitori.field_valuta') }}</label>
            <Select v-model="form.valuta_id" :options="valute.items.value" :loading="valute.loading.value"
              option-label="descrizione" option-value="id" class="w-full"
              :placeholder="t('fornitori.select_valuta')" show-clear />
          </div>
          <div class="form-field">
            <label>{{ t('fornitori.field_giorni_pagamento') }}</label>
            <InputNumber v-model="form.giorni_pagamento" class="w-full" :min="0" />
          </div>
        </div>
        <div class="form-field">
          <Checkbox v-model="form.fine_mese" :binary="true" input-id="fine_mese" />
          <label for="fine_mese" class="ml-2">{{ t('fornitori.field_fine_mese') }}</label>
        </div>

        <!-- === Fiscale === -->
        <h4 class="mt-3">{{ t('fornitori.section_fiscale') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('fornitori.field_regime_fiscale') }}</label>
            <InputText v-model="form.regime_fiscale" class="w-full" :placeholder="t('fornitori.placeholder_regime')" />
          </div>
          <div class="form-field">
            <Checkbox v-model="form.split_payment" :binary="true" input-id="split_payment" />
            <label for="split_payment" class="ml-2">{{ t('fornitori.field_split_payment') }}</label>
          </div>
        </div>
        <div class="form-field">
          <Checkbox v-model="form.bollo_esente" :binary="true" input-id="bollo_esente" />
          <label for="bollo_esente" class="ml-2">{{ t('fornitori.field_bollo_esente') }}</label>
        </div>
        <div class="form-field">
          <Checkbox v-model="form.ritenuta_acconto" :binary="true" input-id="ritenuta_acconto" />
          <label for="ritenuta_acconto" class="ml-2">{{ t('fornitori.field_ritenuta_acconto') }}</label>
        </div>
        <div v-if="form.ritenuta_acconto" class="form-field">
          <label>{{ t('fornitori.field_ritenuta_aliquota') }}</label>
          <InputNumber v-model="form.ritenuta_aliquota" class="w-full" :min="0" :max="100"
            suffix="%" mode="decimal" :min-fraction-digits="2" />
        </div>

        <!-- === FE / SDI === -->
        <h4 class="mt-3">{{ t('fornitori.section_fe_sdi') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('fornitori.field_canale_fe') }}</label>
            <InputText v-model="form.canale_fe" class="w-full" maxlength="7" :placeholder="t('fornitori.placeholder_canale_fe')" />
          </div>
          <div class="form-field">
            <label>{{ t('fornitori.field_pec_email') }}</label>
            <InputText v-model="form.pec_email" class="w-full" :placeholder="t('fornitori.placeholder_pec')" />
          </div>
        </div>

        <!-- === Rating === -->
        <h4 class="mt-3">{{ t('fornitori.section_rating') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('fornitori.field_rating') }}</label>
            <InputNumber v-model="form.rating" class="w-full" :min="0" :max="100" />
          </div>
          <div class="form-field">
            <label>{{ t('fornitori.field_qualifica_scadenza') }}</label>
            <DatePicker v-model="form.qualifica_scadenza" class="w-full" dateFormat="dd/mm/yy" show-icon />
          </div>
        </div>

        <!-- === Note === -->
        <h4 class="mt-3">{{ t('fornitori.section_note') }}</h4>
        <div class="form-field">
          <Textarea v-model="form.note" class="w-full" rows="3" auto-resize />
        </div>

        <!-- === Info audit (solo edit) === -->
        <template v-if="isEdit && detail">
          <div class="form-grid-2col mt-3">
            <div class="form-field">
              <label>{{ t('common.data_insert') }}</label>
              <InputText :model-value="displayDate(detail.data_insert)" disabled class="w-full" />
            </div>
            <div class="form-field">
              <label>{{ t('common.data_update') }}</label>
              <InputText :model-value="displayDate(detail.data_update)" disabled class="w-full" />
            </div>
          </div>
        </template>

        <!-- === Indirizzi soggetto (create mode) === -->
        <!-- In creazione, il trigger DB richiede indirizzi obbligatori per il ruolo FO.
             L'utente deve poter gestire gli indirizzi del soggetto prima di salvare. -->
        <template v-if="!isEdit && soggettoSelezionato">
          <h4 class="mt-3">{{ t('fornitori.section_indirizzi_soggetto') }}</h4>
          <p class="text-color-secondary" style="font-size: 0.85rem; margin: 0 0 0.5rem 0;">
            {{ t('fornitori.hint_indirizzi_obbligatori') }}
          </p>
          <Button icon="pi pi-map-marker" :label="t('fornitori.gestisci_indirizzi')" outlined @click="openIndirizziSoggetto" />
        </template>

        <!-- === Gestione sotto-drawer (solo edit) === -->
        <template v-if="isEdit && detail">
          <h4 class="mt-3">{{ t('fornitori.section_gestione') }}</h4>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <Button icon="pi pi-id-card" :label="t('fornitori.gestisci_contatti')" outlined @click="openContatti" />
            <Button icon="pi pi-map-marker" :label="t('fornitori.gestisci_indirizzi')" outlined @click="openIndirizzi" />
            <Button icon="pi pi-wallet" :label="t('fornitori.gestisci_conti')" outlined @click="openContiBancari" />
          </div>
        </template>

      </div>

      <div class="flex justify-end mt-4">
        <DrawerFooter :loading="loading" :disabled="!canSave" @save="onSave" @cancel="onClose" />
      </div>
    </div>

    <!-- Sotto-drawer: Indirizzi soggetto (create mode — per indirizzi obbligatori ruolo FO) -->
    <IndirizziSoggettoDrawer
      v-if="!isEdit && soggettoSelezionato"
      :visible="indirizziSoggettoDrawer.visible"
      @update:visible="v => indirizziSoggettoDrawer.visible = v"
      :soggetto-id="soggettoSelezionato.id"
      context="soggetto"
    />

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

    <!-- Sotto-drawer: Contatti ruolo (solo edit) -->
    <ContattiSoggettoDrawer
      v-if="isEdit && detail"
      :visible="contattiDrawer.visible"
      @update:visible="v => contattiDrawer.visible = v"
      :soggetto-id="detail.soggetto_ruolo_id"
      context="ruolo"
    />

    <!-- Sotto-drawer: Indirizzi ruolo (solo edit) -->
    <IndirizziSoggettoDrawer
      v-if="isEdit && detail"
      :visible="indirizziDrawer.visible"
      @update:visible="v => indirizziDrawer.visible = v"
      :soggetto-id="detail.soggetto_ruolo_id"
      context="ruolo"
    />

    <!-- Sotto-drawer: Conti bancari ruolo (solo edit) -->
    <ContiBancariDrawer
      v-if="isEdit && detail"
      :visible="contiBancariDrawer.visible"
      @update:visible="v => contiBancariDrawer.visible = v"
      :owner-id="detail.soggetto_ruolo_id"
      :owner-name="detail.ragione_sociale_completa || ''"
      context="ruolo"
    />
  </Drawer>
</template>

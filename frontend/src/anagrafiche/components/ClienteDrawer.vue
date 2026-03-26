<script setup>
// Scopo: Drawer unico creazione/visualizzazione cliente.
// Form unificato: in creazione campi editabili, in visualizzazione disabled.
// Sezioni extra solo in edit: stato, codici, date, PDP, gestione contatti/indirizzi/banca.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClientiStore } from '../stores/clienti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useLookup } from '../../core/composables/useLookup'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { listUtilitiesManual, listSoggettoIndirizzi } from '../api/anagrafiche'
import { lookupCodici } from '../../core/apiCore'
import { DRAWER_WIDTH } from '../../core/constants'
import { displayDate } from '../../core/utils/date'
import { statoClienteSeverity } from '../../core/utils/severity'
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
import Tag from 'primevue/tag'
import Button from 'primevue/button'

const { t } = useI18n()
const store = useClientiStore()
const { execute, loading } = useApiHandler()
const isReadonly = useInjectReadonly()

// Lookup
const utilities = useLookup(() => listUtilitiesManual(), { immediate: true })
const modalitaPagamento = useLookup(() => lookupCodici('config.modalita_pagamento'), { immediate: true })
const terminiPagamento = useLookup(() => lookupCodici('config.termini_pagamento'), { immediate: true })
const ivaList = useLookup(() => lookupCodici('config.iva'), { immediate: true })

// Opzioni statiche (label tramite i18n)
const tipoGgOptions = computed(() => [
  { value: 'N', label: t('clienti.opt_gg_nessuno') },
  { value: 'G', label: t('clienti.opt_gg_giorni') },
  { value: 'M', label: t('clienti.opt_gg_mese') },
  { value: 'F', label: t('clienti.opt_gg_fine_mese') },
])
const paOptions = computed(() => [
  { value: 'N', label: t('common.no') },
  { value: 'S', label: t('common.yes') },
])
const garanziaTipoOptions = computed(() => [
  { value: 'D', label: t('clienti.opt_garanzia_deposito') },
  { value: 'F', label: t('clienti.opt_garanzia_fidejussione') },
])

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  clienteId: { type: Number, default: null }
})

const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

// Form unificato (usato sia in create che in edit/view)
const form = ref({})
const detail = ref(null) // dati extra solo per visualizzazione

// SoggettoResolver (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)
const indirizziSoggetto = ref([])

// Scopo: Valori default per un nuovo cliente.
function defaultForm() {
  return {
    utility_id: null, indirizzo_dettaglio_id: null,
    iva_id: null, modalita_pagamento_id: null, termine_pagamento_id: null,
    tipo_gg_scadenza_ft: 'N', nr_giorni_scadenza: 0,
    cliente_pa: 'N', split_payment: 'N',
    codice_cig: null, codice_cup: null, codice_commessa: null,
    servizio_da_fatturare: true,
    garanzia_tipo: 'D', garanzia_importo: 0
  }
}

function resetForm() {
  soggettoSelezionato.value = null
  indirizziSoggetto.value = []
  detail.value = null
  form.value = defaultForm()
}

// Scopo: Popola form dai dati dettaglio (edit mode).
function populateFormFromDetail(d) {
  form.value = {
    utility_id: d.utility_id,
    indirizzo_dettaglio_id: d.istanza_indirizzo_dettaglio_id,
    iva_id: d.iva_id,
    modalita_pagamento_id: d.modalita_pagamento_id,
    termine_pagamento_id: d.termine_pagamento_id,
    tipo_gg_scadenza_ft: (d.tipo_gg_scadenza_ft || 'N').trim(),
    nr_giorni_scadenza: d.nr_giorni_scadenza || 0,
    cliente_pa: (d.cliente_pa || 'N').trim(),
    split_payment: (d.split_payment || 'N').trim(),
    codice_cig: d.codice_cig,
    codice_cup: d.codice_cup,
    codice_commessa: d.codice_commessa,
    servizio_da_fatturare: d.servizio_da_fatturare ?? true,
    garanzia_tipo: (d.garanzia_tipo || 'D').trim(),
    garanzia_importo: d.garanzia_importo || 0
  }
}

async function loadIndirizziSoggetto(soggettoId) {
  try {
    const res = await listSoggettoIndirizzi(soggettoId)
    const results = res.data.data?.results || res.data.data || []
    indirizziSoggetto.value = results.map(r => ({
      value: r.indirizzo_dettaglio_id,
      label: `${r.tipo_indirizzo_codice} — ${r.indirizzo_normalizzato || ''} ${r.civico || ''}`
    }))
  } catch { indirizziSoggetto.value = [] }
}

function onSoggettoSelezionato(data) {
  soggettoSelezionato.value = data
  loadIndirizziSoggetto(data.id)
}
function onSoggettoCreato(data) {
  soggettoSelezionato.value = data
  loadIndirizziSoggetto(data.id)
}
function clearSoggetto() {
  soggettoSelezionato.value = null
  indirizziSoggetto.value = []
}

// Carica dati
watch(() => props.visible, async (val) => {
  if (!val) return
  if (isEdit.value && props.clienteId) {
    const d = await store.fetchDetail(props.clienteId)
    detail.value = d
    populateFormFromDetail(d)
  } else {
    resetForm()
  }
})

// Scopo: Costruisce il payload dei campi editabili (condiviso tra create e update).
function buildEditablePayload() {
  const f = form.value
  return {
    iva_id: f.iva_id || null,
    modalita_pagamento_id: f.modalita_pagamento_id || null,
    termine_pagamento_id: f.termine_pagamento_id || null,
    tipo_gg_scadenza_ft: f.tipo_gg_scadenza_ft,
    nr_giorni_scadenza: ['G', 'F'].includes(f.tipo_gg_scadenza_ft) ? (f.nr_giorni_scadenza || 0) : null,
    cliente_pa: f.cliente_pa,
    split_payment: f.split_payment,
    codice_cig: f.codice_cig || null,
    codice_cup: f.codice_cup || null,
    codice_commessa: f.codice_commessa || null,
    servizio_da_fatturare: f.servizio_da_fatturare,
    garanzia_tipo: f.garanzia_tipo,
    garanzia_importo: f.garanzia_importo || 0,
  }
}

// Scopo: Salva cliente (create o update).
async function onSave() {
  if (isEdit.value) {
    // Update: solo campi editabili
    const result = await execute(
      () => store.update(props.clienteId, buildEditablePayload()),
      { successMessage: t('clienti.cliente_salvato') }
    )
    if (result !== null) emit('saved', result)
  } else {
    // Create: campi editabili + soggetto + utility + indirizzo
    const sogg = soggettoSelezionato.value
    if (!sogg || !form.value.utility_id) return
    const payload = {
      soggetto_id: sogg.id,
      utility_id: form.value.utility_id,
      indirizzo_dettaglio_id: form.value.indirizzo_dettaglio_id || null,
      ...buildEditablePayload(),
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('clienti.cliente_creato') }
    )
    if (result !== null) emit('saved', result)
  }
}

const canSave = computed(() => !!soggettoSelezionato.value && !!form.value.utility_id)

// Scopo: Calcola data sospensione/riattivazione da mostrare.
const dataSospRiattDetail = computed(() => {
  if (!detail.value) return null
  const sosp = detail.value.data_sospensione
  const riatt = detail.value.data_riattivazione
  if (!sosp && !riatt) return null
  if (sosp && !riatt) return { label: t('clienti.col_sospeso_il'), date: sosp }
  if (!sosp && riatt) return { label: t('clienti.col_riattivato_il'), date: riatt }
  return sosp > riatt
    ? { label: t('clienti.col_sospeso_il'), date: sosp }
    : { label: t('clienti.col_riattivato_il'), date: riatt }
})

// Sotto-drawer
const contattiDrawer = ref({ visible: false })
const indirizziDrawer = ref({ visible: false })
const contiBancariDrawer = ref({ visible: false })
function openContatti() { contattiDrawer.value = { visible: true } }
function openIndirizzi() { indirizziDrawer.value = { visible: true } }
function openContiBancari() { contiBancariDrawer.value = { visible: true } }

function onClose() {
  emit('update:visible', false)
  emit('cancelled')
}
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    @update:visible="val => emit('update:visible', val)"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('clienti.cliente')"
        icon="pi pi-briefcase"
      />
    </template>

    <div :class="{ 'app-readonly': isReadonly }">
      <div class="form-grid">

        <!-- === Soggetto === -->
        <h4>{{ t('clienti.section_soggetto') }}</h4>
        <!-- Creazione: SoggettoResolver -->
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
        <!-- Visualizzazione: banner soggetto -->
        <div v-if="isEdit && detail" class="mb-3">
          <SoggettoMessageBanner
            :ragione-sociale="detail.ragione_sociale_completa"
            :codice-fiscale="detail.codice_fiscale"
          />
        </div>

        <!-- === Servizio === -->
        <h4 class="mt-3">{{ t('clienti.section_servizio') }}</h4>
        <!-- Riga: utility + servizio_da_fatturare + stato (edit) -->
        <div class="cliente-servizio-row">
          <div class="form-field" style="flex: 2;">
            <label>{{ t('clienti.field_utility') }} <span v-if="!isEdit">*</span></label>
            <Select v-model="form.utility_id" :options="utilities.items.value" :loading="utilities.loading.value"
              option-label="descrizione" option-value="id" class="w-full" :placeholder="t('clienti.select_utility')"
              :disabled="isEdit" />
          </div>
          <div class="form-field" style="flex: 1;">
            <label>{{ t('clienti.field_servizio_fatturare') }}</label>
            <Checkbox v-model="form.servizio_da_fatturare" :binary="true" />
          </div>
          <div v-if="isEdit && detail" class="form-field" style="flex: 1; align-self: flex-end;">
            <Tag :value="detail.stato_descrizione" :severity="statoClienteSeverity(detail.stato_codice)"
              style="font-size: 0.95rem; padding: 0.5rem 1rem;" />
          </div>
        </div>
        <div v-if="!isEdit && indirizziSoggetto.length > 0" class="form-field">
          <label>{{ t('clienti.field_indirizzo') }}</label>
          <Select v-model="form.indirizzo_dettaglio_id" :options="indirizziSoggetto"
            option-label="label" option-value="value" class="w-full"
            :placeholder="t('clienti.select_indirizzo')" show-clear />
        </div>

        <!-- === Riepilogo identificativo (solo edit, readonly) === -->
        <template v-if="isEdit && detail">
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('clienti.field_ba_codice') }}</label>
              <InputText :model-value="detail.ba_codice" disabled class="w-full" />
            </div>
            <div class="form-field">
              <label>{{ t('clienti.field_istanza_codice') }}</label>
              <InputText :model-value="detail.istanza_codice" disabled class="w-full" />
            </div>
          </div>
          <div class="form-grid-2col">
            <div class="form-field">
              <label>{{ t('clienti.col_data_attivazione') }}</label>
              <InputText :model-value="displayDate(detail.data_attivazione)" disabled class="w-full" />
            </div>
            <div v-if="detail.data_chiusura" class="form-field">
              <label>{{ t('clienti.field_data_chiusura') }}</label>
              <InputText :model-value="displayDate(detail.data_chiusura)" disabled class="w-full" />
            </div>
          </div>
          <div v-if="dataSospRiattDetail" class="form-field">
            <label>{{ dataSospRiattDetail.label }}</label>
            <InputText :model-value="displayDate(dataSospRiattDetail.date)" disabled class="w-full" />
          </div>
          <div v-if="detail.pdp_id" class="form-field">
            <label>{{ t('clienti.field_pdp') }}</label>
            <InputText :model-value="detail.pdp_id" disabled class="w-full" />
          </div>
        </template>

        <!-- === Pagamento === -->
        <h4 class="mt-3">{{ t('clienti.section_pagamento') }}</h4>
        <div class="form-field">
          <label>{{ t('clienti.field_iva') }}</label>
          <Select v-model="form.iva_id" :options="ivaList.items.value" :loading="ivaList.loading.value"
            option-label="descrizione" option-value="id" class="w-full"
            :placeholder="t('clienti.select_iva')" show-clear />
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('clienti.field_modalita_pagamento') }}</label>
            <Select v-model="form.modalita_pagamento_id" :options="modalitaPagamento.items.value" :loading="modalitaPagamento.loading.value"
              option-label="descrizione" option-value="id" class="w-full"
              :placeholder="t('clienti.select_modalita')" show-clear />
          </div>
          <div class="form-field">
            <label>{{ t('clienti.field_termine_pagamento') }}</label>
            <Select v-model="form.termine_pagamento_id" :options="terminiPagamento.items.value" :loading="terminiPagamento.loading.value"
              option-label="descrizione" option-value="id" class="w-full"
              :placeholder="t('clienti.select_termine')" show-clear />
          </div>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('clienti.field_tipo_gg_scadenza') }}</label>
            <Select v-model="form.tipo_gg_scadenza_ft" :options="tipoGgOptions"
              option-label="label" option-value="value" class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('clienti.field_nr_giorni') }}</label>
            <InputNumber v-model="form.nr_giorni_scadenza" class="w-full" :min="0" />
          </div>
        </div>

        <!-- === PA === -->
        <h4 class="mt-3">{{ t('clienti.section_pa') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('clienti.field_cliente_pa') }}</label>
            <Select v-model="form.cliente_pa" :options="paOptions"
              option-label="label" option-value="value" class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('clienti.field_split_payment') }}</label>
            <Select v-model="form.split_payment" :options="paOptions"
              option-label="label" option-value="value" class="w-full" />
          </div>
        </div>
        <div v-if="form.cliente_pa === 'S'" class="form-grid-3col">
          <div class="form-field">
            <label>{{ t('clienti.field_codice_cig') }}</label>
            <InputText v-model="form.codice_cig" class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('clienti.field_codice_cup') }}</label>
            <InputText v-model="form.codice_cup" class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('clienti.field_codice_commessa') }}</label>
            <InputText v-model="form.codice_commessa" class="w-full" />
          </div>
        </div>

        <!-- === Garanzia === -->
        <h4 class="mt-3">{{ t('clienti.section_garanzia') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('clienti.field_garanzia_tipo') }}</label>
            <Select v-model="form.garanzia_tipo" :options="garanziaTipoOptions"
              option-label="label" option-value="value" class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('clienti.field_garanzia_importo') }}</label>
            <InputNumber v-model="form.garanzia_importo" class="w-full" :min="0"
              mode="decimal" :min-fraction-digits="2" />
          </div>
        </div>

        <!-- === Gestione sotto-drawer (solo edit) === -->
        <template v-if="isEdit && detail">
          <h4 class="mt-3">{{ t('clienti.section_gestione') }}</h4>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
            <Button icon="pi pi-id-card" :label="t('clienti.gestisci_contatti')" outlined @click="openContatti" />
            <Button icon="pi pi-map-marker" :label="t('clienti.gestisci_indirizzi')" outlined @click="openIndirizzi" />
            <Button icon="pi pi-wallet" :label="t('clienti.gestisci_conti')" outlined @click="openContiBancari" />
          </div>
        </template>

      </div>

      <!-- Footer salva/annulla -->
      <div class="flex justify-end mt-4">
        <DrawerFooter :loading="loading" :disabled="!isEdit && !canSave" @save="onSave" @cancel="onClose" />
      </div>
    </div>

    <!-- Sotto-drawer: SoggettoResolver (solo creazione) -->
    <SoggettoResolver
      v-if="!isEdit"
      :visible="resolverVisible"
      tipo-ruolo-codice="CL"
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
      :istanza-utility-id="detail.istanza_utility_id"
      context="ruolo"
    />

    <!-- Sotto-drawer: Indirizzi ruolo (solo edit) -->
    <IndirizziSoggettoDrawer
      v-if="isEdit && detail"
      :visible="indirizziDrawer.visible"
      @update:visible="v => indirizziDrawer.visible = v"
      :soggetto-id="detail.soggetto_ruolo_id"
      :istanza-utility-id="detail.istanza_utility_id"
      context="ruolo"
    />

    <!-- Sotto-drawer: Conti bancari ruolo (solo edit) -->
    <ContiBancariDrawer
      v-if="isEdit && detail"
      :visible="contiBancariDrawer.visible"
      @update:visible="v => contiBancariDrawer.visible = v"
      :owner-id="detail.soggetto_ruolo_id"
      :owner-name="detail.ragione_sociale_completa || ''"
      :istanza-utility-id="detail.istanza_utility_id"
      context="ruolo"
    />
  </Drawer>
</template>

<style scoped>
.cliente-servizio-row {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
}
</style>

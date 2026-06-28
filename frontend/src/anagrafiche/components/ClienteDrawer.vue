<script setup>
// Scopo: Drawer unico creazione/visualizzazione cliente.
// Form unificato: in creazione campi editabili, in visualizzazione disabled.
// Sezioni extra solo in edit: stato, codici, date, PDP, gestione contatti/indirizzi/banca.
import { ref, watch, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useClientiStore } from '../stores/clienti'
import { useAuthStore } from '../../stores/auth'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useNotify } from '../../core/composables/useNotify'
import { useLookup } from '../../core/composables/useLookup'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useContattoForm } from '../../core/composables/useContattoForm'
import { useIndirizzoSoggettoForm } from '../../core/composables/useIndirizzoSoggettoForm'
import { useParameterDefaults } from '../../core/composables/useParameterDefaults'
import { useUtilityDefaultId } from '../../core/composables/useUtilityDefaultId'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { listUtilitiesPerBillingAccount } from '../api/anagrafiche'
import { lookupUtilitiesPerEmittente } from '../../core/apiCore'
import { DRAWER_WIDTH, TIPO_RUOLO, MANAGE_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import { displayDate } from '../../core/utils/date'
import { statoClienteSeverity } from '../../core/utils/severity'
import SoggettoResolver from '../../core/components/SoggettoResolver.vue'
import SoggettoMessageBanner from '../../core/components/SoggettoMessageBanner.vue'
import SoggettoPreviewBadges from '../../core/components/SoggettoPreviewBadges.vue'
import ContattoForm from '../../core/components/ContattoForm.vue'
import IndirizzoSoggettoForm from '../../core/components/IndirizzoSoggettoForm.vue'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import IvaSelect from '../../core/components/IvaSelect.vue'
import Drawer from 'primevue/drawer'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Checkbox from 'primevue/checkbox'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Message from 'primevue/message'

const { t } = useI18n()
const store = useClientiStore()
const auth = useAuthStore()
const { execute, loading } = useApiHandler()
const { warn } = useNotify()
const isReadonly = useInjectReadonly()
const contatto = useContattoForm()
const contattoErrors = ref([])
const indirizzo = useIndirizzoSoggettoForm()
// Defer: il load parte quando il drawer si apre (in watch(visible)), non
// al mount del parent. Evita fetch premature che causano flash di UI
// quando il drawer viene renderizzato ma non ancora aperto.
const { defaults: paramDefaults, load: loadDefaults } = useParameterDefaults(['DEFAULT_IVA_ID'])

// Default utility globale: il parametro DEFAULT_UTILITY stocca un codice_interno
// (framework FK-surrogata, DB 2026-05-02). Composable risolve a id locale,
// filtrato per ruolo CL (intersezione ruolo + emittente).
const { id: utilityDefaultId, load: loadUtilityDefault } = useUtilityDefaultId({
  ruolo: TIPO_RUOLO.CLIENTE,
})

// Lookup utility per creazione: filtrate per emittente dell'operatore + ruolo CL.
// In modalita' edit usiamo il nuovo endpoint BA-driven (vedi sotto).
// Lazy: load() viene chiamato in watch(visible) solo quando il drawer apre in create.
const utilities = useLookup(() => lookupUtilitiesPerEmittente(TIPO_RUOLO.CLIENTE))

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

// Lookup utility BA-driven (FE-4.5 refactor operatore-emittenti).
// In modalita' edit il BA esiste gia': chiamiamo il nuovo endpoint che
// restituisce utility ammesse per il ruolo CL del BA, intersecate con la
// matrice slot/override dell'emittente associato. Sempre singola entry
// (l'utility del BA e' immutabile) ma coerente con la semantica refactor.
const utilitiesBaDriven = ref([])
const utilitiesBaLoading = ref(false)
async function loadUtilitiesBaDriven(billingAccountId) {
  if (!billingAccountId) {
    utilitiesBaDriven.value = []
    return
  }
  utilitiesBaLoading.value = true
  try {
    const res = await listUtilitiesPerBillingAccount(billingAccountId, TIPO_RUOLO.CLIENTE)
    const results = res.data.data?.results || []
    utilitiesBaDriven.value = results.map(r => ({
      id: r.utility_id,
      codice: r.codice,
      descrizione: r.descrizione,
      is_personalizzata_per_ef: r.is_personalizzata_per_ef,
    }))
  } catch (err) {
    utilitiesBaDriven.value = []
    console.warn('ClienteDrawer: loadUtilitiesBaDriven failed', err)
  } finally {
    utilitiesBaLoading.value = false
  }
}
// Sorgente effettiva del Select utility: BA-driven in edit, manual in create.
const utilityOptions = computed(() => isEdit.value ? utilitiesBaDriven.value : utilities.items.value)
const utilityLoading = computed(() => isEdit.value ? utilitiesBaLoading.value : utilities.loading.value)

// Form unificato (usato sia in create che in edit/view)
const form = ref({})
const detail = ref(null) // dati extra solo per visualizzazione

// SoggettoResolver (solo creazione)
const resolverVisible = ref(false)
const soggettoSelezionato = ref(null)

// Scopo: Valori default per un nuovo cliente.
function defaultForm() {
  return {
    utility_id: null, indirizzo_dettaglio_id: null,
    ba_categoria_cliente_id: null,
    iva_id: null, modalita_pagamento_id: null, termine_pagamento_id: null,
    tipo_gg_scadenza_ft: 'N', nr_giorni_scadenza: 0,
    cliente_pa: 'N', split_payment: 'N',
    codice_cig: null, codice_cup: null, codice_commessa: null,
    servizio_da_fatturare: true,
    garanzia_tipo: 'D', garanzia_importo: 0,
    stato_cliente_id: null
  }
}

function resetForm() {
  soggettoSelezionato.value = null
  detail.value = null
  form.value = defaultForm()
  contatto.reset()
  contattoErrors.value = []
  indirizzo.reset()
  utilitiesBaDriven.value = []
}

// Scopo: Popola form dai dati dettaglio (edit mode).
function populateFormFromDetail(d) {
  form.value = {
    utility_id: d.utility_id,
    indirizzo_dettaglio_id: d.istanza_indirizzo_dettaglio_id,
    // Categoria cliente in sola lettura: mostrata ma NON modificabile (F3-FE-04).
    // In edit la categoria non finisce nel payload PATCH; le modifiche passano
    // per contratto (F3-FE-05) o azione dedicata con storicizzazione.
    ba_categoria_cliente_id: d.ba_categoria_cliente_id,
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
    stato_cliente_id: d.stato_cliente_id,
    garanzia_importo: d.garanzia_importo || 0
  }
}

// Scopo: estrae soggetto_ruolo_id CLIENTE dal soggetto selezionato (se ha gia il ruolo)
const previewRuoloId = computed(() => {
  const ruoli = soggettoSelezionato.value?.ruoli || []
  const cliente = ruoli.find(r => r.codice === TIPO_RUOLO.CLIENTE)
  return cliente?.soggetto_ruolo_id || null
})

function onSoggettoSelezionato(data) {
  soggettoSelezionato.value = data
}
function onSoggettoCreato(data) {
  soggettoSelezionato.value = data
}
function clearSoggetto() {
  soggettoSelezionato.value = null
}

// Versione per invalidare risposte async stantie: se il drawer si chiude
// (o si riapre) prima che fetchDetail/loadUtilities atterrino, la risposta
// vecchia viene scartata invece di popolare il form attuale.
const fgFv = useFetchVersion()

// Gate rendering: il contenuto del drawer appare solo quando i dati chiave
// sono pronti. Evita il "flash" di sezioni vuote che si popolano a tempi
// diversi durante l'animazione di apertura.
const ready = ref(false)

// Carica dati
watch(() => props.visible, async (val) => {
  if (!val) { fgFv.invalidate(); ready.value = false; return }
  const v = fgFv.tag()
  ready.value = false

  // Lazy load dei lookup: partono solo all'apertura effettiva del drawer,
  // non al mount del parent. Cache interna (loaded flag) evita rifetch.
  // loadDefaults() fire-and-forget; loadUtilityDefault e' awaitato sotto
  // (branch CREATE) per garantire utility_id risolto al primo render.
  loadDefaults()
  if (!isEdit.value) {
    utilities.load()
  }
  if (isEdit.value && props.clienteId) {
    const d = await store.fetchDetail(props.clienteId)
    if (!fgFv.isCurrent(v)) return
    detail.value = d
    // Refactor operatore-emittenti: in edit le utility vengono dal BA
    // (filtrate per emittente associato + parametri override). Attendiamo
    // il caricamento delle options PRIMA di popolare il form: altrimenti
    // PrimeVue Select riceve v-model con valore non presente in options
    // e non lo riconcilia quando le options arrivano.
    if (d.billing_account_id) {
      await loadUtilitiesBaDriven(d.billing_account_id)
      if (!fgFv.isCurrent(v)) return
    }
    // Difensivo: se la matrice BA-driven non include l'utility corrente del
    // BA (matrice/emittente variati dopo la creazione, oppure endpoint che
    // filtra piu' stretto), iniettiamo una entry dal dettaglio per garantire
    // che il Select visualizzi comunque il valore corrente. Il Select e'
    // disabled in edit, quindi non crea side-effect di selezione.
    if (d.utility_id && !utilitiesBaDriven.value.some(u => u.id === d.utility_id)) {
      utilitiesBaDriven.value = [
        {
          id: d.utility_id,
          codice: d.utility_codice || '',
          descrizione: d.utility_descrizione || '',
        },
        ...utilitiesBaDriven.value,
      ]
    }
    populateFormFromDetail(d)
  } else {
    resetForm()
    // Attendiamo paramDefaults + utilityDefault cosi' IVA/Utility default sono
    // gia' presenti al primo render → niente flash da null a valore.
    // utilityDefault risolve codice_interno -> id via lookup utilities-per-emittente.
    await Promise.all([loadDefaults(), loadUtilityDefault()])
    if (!fgFv.isCurrent(v)) return
    if (paramDefaults.value.DEFAULT_IVA_ID) {
      form.value.iva_id = Number(paramDefaults.value.DEFAULT_IVA_ID)
    }
    if (utilityDefaultId.value) {
      form.value.utility_id = utilityDefaultId.value
    }
    indirizzo.loadMatriceRuolo(TIPO_RUOLO.CLIENTE)
  }
  ready.value = true
})

// Scopo: Costruisce il payload dei campi editabili (condiviso tra create e update).
function buildEditablePayload() {
  const f = form.value
  return {
    iva_id: f.iva_id || null,
    modalita_pagamento_id: f.modalita_pagamento_id || null,
    termine_pagamento_id: f.termine_pagamento_id || null,
    tipo_gg_scadenza_ft: f.tipo_gg_scadenza_ft,
    nr_giorni_scadenza: f.nr_giorni_scadenza,
    cliente_pa: f.cliente_pa,
    split_payment: f.split_payment,
    codice_cig: f.codice_cig || null,
    codice_cup: f.codice_cup || null,
    codice_commessa: f.codice_commessa || null,
    servizio_da_fatturare: f.servizio_da_fatturare,
    garanzia_tipo: f.garanzia_tipo,
    garanzia_importo: f.garanzia_importo || 0,
    stato_cliente_id: f.stato_cliente_id || null,
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
    // Validazione contatto inline (Fase 5): regola unificata via composable
    // useContattoForm.classify() — mirror della regola backend.
    // EMPTY → skip; PARTIAL → blocca con messaggio; VALID → invia.
    if (contatto.isFilled()) {
      contattoErrors.value = contatto.validate()
      if (contattoErrors.value.length > 0) {
        warn(t('clienti.contatto_campi_obbligatori'))
        return
      }
    } else {
      contattoErrors.value = []
    }

    // Create: campi editabili + soggetto + utility + indirizzo + contatto
    const sogg = soggettoSelezionato.value
    if (!sogg || !form.value.utility_id) return
    const payload = {
      soggetto_id: sogg.id,
      utility_id: form.value.utility_id,
      indirizzo_dettaglio_id: form.value.indirizzo_dettaglio_id || null,
      ba_categoria_cliente_id: form.value.ba_categoria_cliente_id,
      ...buildEditablePayload(),
    }
    if (contatto.isFilled()) {
      payload.contatto = { ...contatto.form }
    }
    if (indirizzo.hasIndirizzi.value) {
      payload.indirizzi = indirizzo.toPayloadArray()
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('clienti.cliente_creato') }
    )
    if (result !== null) emit('saved', result)
  }
}

// canSave: in creazione richiede soggetto + utility, e non deve essere
// admin globale (refactor operatore-emittenti Q6 — defense-in-depth UI:
// il guard backend e il trigger DB sono comunque la difesa primaria).
const canSave = computed(() => {
  if (!soggettoSelezionato.value || !form.value.utility_id) return false
  // F3-FE-04: categoria cliente obbligatoria in creazione (no default implicito).
  if (!isEdit.value && !form.value.ba_categoria_cliente_id) return false
  if (auth.isAdminGlobale) return false
  return true
})

// Scopo: Mostra data + label dell'evento stato corrente del cliente.
// Logica risolta dal backend (Fase 4): la fn DB
// anagrafiche.fn_get_evento_stato_corrente_cliente confronta sosp vs
// riatt e ritorna data_evento_stato + tipo_evento_stato. Niente piu'
// computed con sosp > riatt nel frontend.
const EVENTO_LABEL_KEY = {
  SOSPENSIONE: 'clienti.col_sospeso_il',
  RIATTIVAZIONE: 'clienti.col_riattivato_il',
}
const eventoStatoDetail = computed(() => {
  if (!detail.value?.data_evento_stato || !detail.value?.tipo_evento_stato) return null
  const labelKey = EVENTO_LABEL_KEY[detail.value.tipo_evento_stato]
  if (!labelKey) return null  // tipo evento sconosciuto → niente label, no errore
  return { label: t(labelKey), date: detail.value.data_evento_stato }
})


const onClose = useDrawerClose(emit, 'cancelled')
</script>

<template>
  <Drawer
    :visible="props.visible"
    position="right"
    :style="{ width: DRAWER_WIDTH.COMPLEX }"
    :dismissable="true"
    @update:visible="val => emit('update:visible', val)"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('clienti.cliente')"
        :icon="NAV_ICONS.CLIENTI"
      />
    </template>

    <div v-if="!ready" class="app-loading">
      <i class="pi pi-spin pi-spinner" style="font-size: 1.5rem;"></i>
    </div>
    <div v-show="ready" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

        <!-- === Soggetto === -->
        <h4>{{ t('clienti.section_soggetto') }}</h4>
        <!-- Creazione: SoggettoResolver -->
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
        <!-- Visualizzazione: banner soggetto -->
        <div v-if="isEdit && detail" class="mb-3">
          <SoggettoMessageBanner
            :ragione-sociale="detail.ragione_sociale_completa"
            :id-fiscale="detail.codice_fiscale || detail.partita_iva"
          />
        </div>

        <!-- Sezioni dati cliente: visibili solo dopo selezione soggetto (create) o sempre (edit) -->
        <template v-if="isEdit || soggettoSelezionato">

        <!-- === Servizio === -->
        <h4 class="mt-3">{{ t('clienti.section_servizio') }}</h4>
        <!-- Banner refactor operatore-emittenti (solo creazione) -->
        <Message v-if="!isEdit && auth.isAdminGlobale" severity="warn" :closable="false" class="mt-05">
          {{ t('clienti.banner_admin_globale_no_create') }}
        </Message>
        <Message v-else-if="!isEdit && auth.emittenteCorrente" severity="info" :closable="false" class="mt-05">
          {{ t('clienti.banner_emittente_corrente', { nome: auth.emittenteCorrente.ragioneSociale }) }}
        </Message>
        <!-- Riga: utility + servizio_da_fatturare + stato (edit) -->
        <div class="cliente-servizio-row">
          <div class="form-field" style="flex: 2;">
            <label>{{ t('clienti.field_utility') }} <span v-if="!isEdit">*</span></label>
            <Select v-model="form.utility_id" :options="utilityOptions" :loading="utilityLoading"
              option-label="descrizione" option-value="id" class="w-full" :placeholder="t('clienti.select_utility')"
              :disabled="isEdit" />
          </div>
          <div class="form-field" style="flex: 1;">
            <label>{{ t('clienti.field_servizio_fatturare') }}</label>
            <Checkbox v-model="form.servizio_da_fatturare" :binary="true" />
          </div>
          <div v-if="isEdit && detail" class="form-field" style="flex: 1; align-self: flex-end;">
            <Tag :value="detail.stato_descrizione" :severity="statoClienteSeverity(detail.stato_codice_interno)"
              style="font-size: 0.95rem; padding: 0.5rem 1rem;" />
          </div>
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
          <div v-if="eventoStatoDetail" class="form-field">
            <label>{{ eventoStatoDetail.label }}</label>
            <InputText :model-value="displayDate(eventoStatoDetail.date)" disabled class="w-full" />
          </div>
          <div v-if="detail.pdp_id" class="form-field">
            <label>{{ t('clienti.field_pdp') }}</label>
            <InputText :model-value="detail.pdp_id" disabled class="w-full" />
          </div>
        </template>

        <!-- === Pagamento === -->
        <h4 class="mt-3">{{ t('clienti.section_pagamento') }}</h4>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('clienti.field_iva') }}</label>
            <IvaSelect v-model="form.iva_id" />
          </div>
          <div class="form-field">
            <label>
              {{ t('clienti.field_categoria_cliente') }}
              <span v-if="!isEdit">*</span>
            </label>
            <LookupSelect v-model="form.ba_categoria_cliente_id"
              rel="anagrafiche.categorie_clienti" class="w-full"
              :placeholder="t('clienti.select_categoria_cliente')"
              :disabled="isEdit" />
          </div>
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('clienti.field_modalita_pagamento') }}</label>
            <LookupSelect v-model="form.modalita_pagamento_id" rel="config.modalita_pagamento" class="w-full"
              :placeholder="t('clienti.select_modalita')" show-clear />
          </div>
          <div class="form-field">
            <label>{{ t('clienti.field_termine_pagamento') }}</label>
            <LookupSelect v-model="form.termine_pagamento_id" rel="config.termini_pagamento" class="w-full"
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

        <!-- === Contatto inline (solo creazione) === -->
        <template v-if="!isEdit">
          <div class="app-drawer-section">
            <h4>{{ t('soggetti.section_contatto') }}</h4>
          </div>
          <ContattoForm
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
            <h4>{{ t('soggetti.section_indirizzo') }}</h4>
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

      <!-- Badge indirizzi/contatti/conti — creazione: readonly preview, edit: editabile -->
      <SoggettoPreviewBadges v-if="!isEdit && previewRuoloId"
        :soggetto-ruolo-id="previewRuoloId"
        :tipo-soggetto-dettaglio-id="soggettoSelezionato?.tipo_soggetto_dettaglio_id"
        :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
        preview />
      <!-- §1.6: accessi web (portale + shop) tramite pulsante Web in
           SoggettoPreviewBadges, apre WebAccessiDrawer autonomo. Il
           pulsante compare solo in edit (richiede BA persistito e un
           clienteId valido per chiamare gli endpoint stato/invio). -->
      <SoggettoPreviewBadges v-else-if="isEdit && detail"
        :soggetto-ruolo-id="detail.soggetto_ruolo_id"
        :istanza-utility-id="detail.istanza_utility_id"
        :tipo-soggetto-dettaglio-id="detail.tipo_soggetto_dettaglio_id"
        :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
        entita-tipo-web="cliente"
        :entita-id-web="props.clienteId"
        :email-iniziale-web="detail?.soggetto_email || ''" />

      <FormFooter :loading="loading" :disabled="!isEdit && !canSave" @save="onSave" @cancel="onClose" />
    </div>

    <!-- Sotto-drawer: SoggettoResolver (solo creazione) -->
    <SoggettoResolver
      v-if="!isEdit"
      :visible="resolverVisible"
      :tipo-ruolo-codice="TIPO_RUOLO.CLIENTE"
      @update:visible="v => resolverVisible = v"
      @soggetto-selezionato="onSoggettoSelezionato"
      @soggetto-creato="onSoggettoCreato"
      @annullato="resolverVisible = false"
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

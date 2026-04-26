<script setup>
// Scopo: Drawer contratto v5 — testata + sezione Pricing modalita' A/B/C
//        + sub-drawer righe (gestione override per articolo in modalita' B/C)
//        + sub-drawer utility 1:1 (tipo/classe utenza).
//
// Modalita' pricing v5:
//  A = listino vincolante + variazione globale (PERCENTUALE opz. valore)
//  B = listino + override righe (prezzo_unitario per articoli specifici)
//  C = interamente negoziato (no listino, tutte le righe con prezzo_unitario)
import { ref, watch, computed, provide } from 'vue'
import { useI18n } from 'vue-i18n'
import { useContrattiStore } from '../stores/contratti'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useInjectReadonly, READONLY_KEY } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { DRAWER_WIDTH } from '../../core/constants'
import { toDateString, parseIsoDate } from '../../core/utils/date'
import { statoContrattoSeverity } from '../../core/utils/severity'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import DrawerFooter from '../../core/components/DrawerFooter.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import BillingAccountLookup from '../../core/components/BillingAccountLookup.vue'
import ContrattoRigheDrawer from './ContrattoRigheDrawer.vue'
import Drawer from 'primevue/drawer'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import Select from 'primevue/select'
import SelectButton from 'primevue/selectbutton'
import Tag from 'primevue/tag'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Textarea from 'primevue/textarea'

const { t } = useI18n()
const store = useContrattiStore()
const { execute, loading } = useApiHandler()
// Readonly da permessi area (LETTURA/BLOCCATO). Si combina con isContractLocked
// (stato post-DRAFT) per ottenere l'isReadonly effettivo del drawer.
const parentReadonly = useInjectReadonly()
const { confirmAction } = useConfirmAction()

const props = defineProps({
  visible: Boolean,
  mode: { type: String, default: 'create' },
  contrattoId: { type: Number, default: null },
  // Prefill opzionale per creazione da contesto cliente (ContrattiBillingAccountDrawer).
  initialBillingAccount: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'saved', 'cancelled'])

const isEdit = computed(() => props.mode === 'edit')

const detail = ref(null)
const form = ref({})

// Profilo A: contratto in stato post-DRAFT e' bloccato (eccetto cambio stato
// che ha la sua azione dedicata). isContractLocked e' true se siamo in edit
// e lo stato del contratto non e' DRAFT.
const isContractLocked = computed(() => {
  if (!isEdit.value) return false
  const stato = detail.value?.stato_codice
  return stato != null && stato !== 'DRAFT'
})

// isReadonly effettivo del drawer: OR tra permessi area e stato post-DRAFT.
// Tutti i campi/azioni del drawer principale e dei sub-drawer (righe, utility)
// devono basarsi su questo computed. Propagato via provide ai figli.
const isReadonly = computed(() => parentReadonly.value || isContractLocked.value)
provide(READONLY_KEY, isReadonly)

// Deferimento contenuto: i LookupSelect montano solo dopo l'animazione del drawer.
const contentReady = ref(false)
function onAfterShow() { contentReady.value = true }

// Sub-drawer
const righeVisible = ref(false)

// fgVersion: invalida fetch stantii su apertura/chiusura rapide.
let fgVersion = 0

// Modalita' pricing (FE-only, derivata dai campi testata).
// Puo' essere impostata esplicitamente via SelectButton; alla scrittura
// aggiorna i campi coerenti (listino_id / tipo_variazione_globale / valore).
const modalitaOptions = computed(() => [
  { value: 'A', label: t('contratti.modalita_a'), hint: t('contratti.modalita_a_hint') },
  { value: 'B', label: t('contratti.modalita_b'), hint: t('contratti.modalita_b_hint') },
  { value: 'C', label: t('contratti.modalita_c'), hint: t('contratti.modalita_c_hint') },
])

const tipoVariazioneOptions = computed(() => [
  { value: 'PERCENTUALE', label: t('contratti.tipo_variazione_percentuale') },
  { value: 'VALORE_FISSO', label: t('contratti.tipo_variazione_valore_fisso') },
])

const ambitoOptions = computed(() => [
  { value: 'COMMODITY', label: t('contratti.ambito_commodity') },
  { value: 'COMMERCIO', label: t('contratti.ambito_commercio') },
])

function defaultForm() {
  return {
    billing_account_id: null,
    billing_account_obj: null,
    istanza_utility_id: null,
    utility_id: null,
    ambito: 'COMMODITY',
    valido_dal: new Date().toISOString().slice(0, 10),
    valido_al: null,
    data: new Date().toISOString().slice(0, 10),
    parent_contratto_id: null,
    meta_note: '',
    // Categoria cliente snapshot
    categoria_cliente_id_snapshot: null,
    // Pricing
    modalita: 'A',
    listino_id: null,
    tipo_variazione_globale: null,
    valore_variazione_globale: null,
    // Utility 1:1 (create inline)
    utility_tipo_utenza_id: null,
    utility_classe_utenza_id: null,
  }
}

function resetForm() {
  form.value = defaultForm()
  detail.value = null
}

function populateFromDetail(d) {
  const modalita = deriveModalita(d)
  form.value = {
    billing_account_id: d.billing_account_id,
    billing_account_obj: d.ba_ragione_sociale ? {
      id: d.billing_account_id,
      codice: d.ba_codice,
      ragione_sociale: d.ba_ragione_sociale,
      utility_codice: d.utility_codice,
      utility_descrizione: d.utility_descrizione,
      pdp: d.pdp || null,
    } : null,
    istanza_utility_id: d.istanza_utility_id,
    utility_id: d.utility_id,
    ambito: d.ambito || 'COMMODITY',
    valido_dal: d.valido_dal,
    valido_al: d.valido_al,
    data: d.data,
    parent_contratto_id: d.parent_contratto_id,
    meta_note: d.meta?.note || '',
    categoria_cliente_id_snapshot: d.categoria_cliente_id_snapshot || null,
    modalita,
    listino_id: d.listino_id,
    tipo_variazione_globale: d.tipo_variazione_globale,
    valore_variazione_globale: d.valore_variazione_globale,
    utility_tipo_utenza_id: d.utility?.tipo_utenza_id || null,
    utility_classe_utenza_id: d.utility?.classe_utenza_id || null,
  }
}

function deriveModalita(d) {
  if (!d.listino_id) return 'C'
  if (d.tipo_variazione_globale) return 'A'
  return 'B'
}

// Quando l'utente cambia modalita', normalizza i campi coerenti.
function onModalitaChange(nuova) {
  if (nuova === 'A') {
    // Default: PERCENTUALE, valore editabile. Se mancante, suggerisce 0.
    if (!form.value.tipo_variazione_globale) form.value.tipo_variazione_globale = 'PERCENTUALE'
  } else if (nuova === 'B') {
    // listino si', variazione NO
    form.value.tipo_variazione_globale = null
    form.value.valore_variazione_globale = null
  } else if (nuova === 'C') {
    // No listino, no variazione
    form.value.listino_id = null
    form.value.tipo_variazione_globale = null
    form.value.valore_variazione_globale = null
  }
}

// Wrapper: accetta sia string che Date (DatePicker emette Date).
function toIsoDate(d) {
  return typeof d === 'string' ? d : toDateString(d)
}

// Carica dati all'apertura
watch(() => props.visible, async (val) => {
  if (!val) { fgVersion++; contentReady.value = false; return }
  const v = ++fgVersion

  if (isEdit.value && props.contrattoId) {
    const d = await store.fetchDetail(props.contrattoId)
    if (v !== fgVersion) return
    detail.value = d
    populateFromDetail(d)
  } else {
    resetForm()
    // Prefill BA se aperto da contesto cliente.
    if (props.initialBillingAccount?.id) {
      onBaSelected(props.initialBillingAccount)
    }
  }
})

// Badge sintetico: "GAS — PDP IT001E00012345" oppure solo "GAS" se senza PDP.
const baBadgeLabel = computed(() => {
  const ba = form.value.billing_account_obj
  if (!ba) return ''
  const utility = ba.utility_codice || ba.utility_descrizione || ''
  if (!utility) return ''
  const pdp = ba.pdp ? `PDP ${ba.pdp}` : ''
  return pdp ? `${utility} — ${pdp}` : utility
})

function onBaSelected(item) {
  if (!item) {
    form.value.billing_account_id = null
    form.value.billing_account_obj = null
    form.value.istanza_utility_id = null
    form.value.utility_id = null
    form.value.categoria_cliente_id_snapshot = null
    return
  }
  form.value.billing_account_id = item.id
  form.value.billing_account_obj = item
  form.value.istanza_utility_id = item.istanza_utility_id || null
  form.value.utility_id = item.utility_id || null
  // Pre-compila la categoria dal BA; l'operatore puo' cambiarla.
  form.value.categoria_cliente_id_snapshot = item.categoria_cliente_id || null
}

// Validazione FE
const canSave = computed(() => {
  if (isReadonly.value) return false
  if (isEdit.value) return true
  const f = form.value
  if (!f.billing_account_id) return false
  if (!f.valido_dal || !f.data) return false
  if (!f.ambito) return false
  if (f.modalita === 'A' && !f.listino_id) return false
  if (f.modalita === 'A' && !f.tipo_variazione_globale) return false
  if (f.modalita === 'B' && !f.listino_id) return false
  return true
})

function buildPayload() {
  const f = form.value
  // Profilo A whitelist FE: il payload PATCH va limitato ai campi che il
  // BE accetta nello stato corrente. Il BE applica una guard speculare
  // (E_CONTRATTO_NON_MODIFICABILE) — rispettiamo la stessa whitelist qui
  // per evitare round-trip e fornire UX coerente.
  // - DRAFT: tutti i campi
  // - ATTIVO/SOSPESO: solo valido_al + meta (programma cessazione + note)
  // - CESSATO: nessuno (Salva non dovrebbe nemmeno essere cliccabile)
  const stato = isEdit.value ? (detail.value?.stato_codice || null) : 'DRAFT'
  const isDraft = stato === 'DRAFT'

  if (!isDraft) {
    // Stati post-DRAFT: il pulsante Salva e' disabilitato (canSave=false
    // perche' isReadonly=true). Questo branch non dovrebbe mai essere
    // raggiunto in pratica; ritorniamo payload vuoto per safety. Le
    // operazioni post-DRAFT sono solo via cambio stato (dialog Cessa).
    return {}
  }

  const payload = {
    ambito: f.ambito,
    valido_dal: toIsoDate(f.valido_dal),
    valido_al: toIsoDate(f.valido_al),
    data: toIsoDate(f.data),
    parent_contratto_id: f.parent_contratto_id || null,
    categoria_cliente_id_snapshot: f.categoria_cliente_id_snapshot || null,
  }
  if (f.meta_note) payload.meta = { note: f.meta_note }
  // Modalita' pricing
  if (f.modalita === 'A') {
    payload.listino_id = f.listino_id
    payload.tipo_variazione_globale = f.tipo_variazione_globale
    payload.valore_variazione_globale = f.valore_variazione_globale != null ? String(f.valore_variazione_globale) : null
  } else if (f.modalita === 'B') {
    payload.listino_id = f.listino_id
    payload.tipo_variazione_globale = null
    payload.valore_variazione_globale = null
  } else if (f.modalita === 'C') {
    payload.listino_id = null
    payload.tipo_variazione_globale = null
    payload.valore_variazione_globale = null
  }
  return payload
}

async function handleSave() {
  if (isEdit.value) {
    const result = await execute(
      () => store.update(props.contrattoId, buildPayload()),
      { successMessage: t('contratti.contratto_salvato') }
    )
    if (result !== null) emit('saved', result)
  } else {
    const f = form.value
    const payload = {
      billing_account_id: f.billing_account_id,
      istanza_utility_id: f.istanza_utility_id,
      utility_id: f.utility_id,
      ...buildPayload(),
    }
    // Utility 1:1 inline: tipo/classe utenza (opzionali)
    if (f.utility_tipo_utenza_id || f.utility_classe_utenza_id) {
      payload.utility = {
        tipo_utenza_id: f.utility_tipo_utenza_id || null,
        classe_utenza_id: f.utility_classe_utenza_id || null,
      }
    }
    const result = await execute(
      () => store.create(payload),
      { successMessage: t('contratti.contratto_creato') }
    )
    if (result !== null) emit('saved', result)
  }
}

// Ricarica dettaglio (usata dopo cambio stato o mutazioni righe/utility).
async function refreshDetail() {
  if (!props.contrattoId) return
  const d = await store.fetchDetail(props.contrattoId)
  detail.value = d
  populateFromDetail(d)
}

// Stato dialog cessazione: per CESSATO chiediamo la data prima della
// transizione (default oggi). Le altre transizioni passano per il classico
// confirmAction (DRAFT->ATTIVO, SOSPESO->ATTIVO, ecc.).
//
// Comportamento data-driven (allineato col backend):
// - data <  oggi  -> cessazione immediata: stato passa a CESSATO
// - data >= oggi  -> cessazione PROGRAMMATA: stato resta ATTIVO/SOSPESO,
//                    job notturno DB allinea quando la data scade
const cessaDialogVisible = ref(false)
const cessaDialogData = ref(null)

const cessazioneProgrammata = computed(() => {
  if (!cessaDialogData.value) return false
  const oggi = new Date()
  oggi.setHours(0, 0, 0, 0)
  const scelta = new Date(cessaDialogData.value)
  scelta.setHours(0, 0, 0, 0)
  return scelta >= oggi
})

function openCessaDialog() {
  cessaDialogData.value = new Date()  // default oggi -> cessazione programmata per stasera
  cessaDialogVisible.value = true
}

async function onConfermaCessazione() {
  const validoAl = toDateString(cessaDialogData.value)
  const programmata = cessazioneProgrammata.value
  const result = await execute(
    () => store.cambiaStato(props.contrattoId, 'CESSATO', { validoAl }),
    {
      successMessage: programmata
        ? t('contratti.cessa_dialog_success_programmata', { data: validoAl })
        : t('contratti.cessa_dialog_success_immediata'),
    },
  )
  if (result !== null) {
    cessaDialogVisible.value = false
    await refreshDetail()
  }
}

// Cambio stato (edit). CESSATO ha flusso dedicato (dialog con data),
// gli altri stati usano il confirmAction generico.
function onCambiaStato(codice) {
  if (codice === 'CESSATO') {
    openCessaDialog()
    return
  }
  confirmAction({
    title: t('contratti.conferma_titolo'),
    message: t('contratti.conferma_cambio_stato', { stato: codice }),
    onAccept: async () => {
      const result = await execute(
        () => store.cambiaStato(props.contrattoId, codice),
        { successMessage: t('contratti.stato_cambiato') }
      )
      if (result !== null) await refreshDetail()
    },
  })
}

// Azioni disponibili per stato corrente. SOSPESO non e' destinazione (la
// gestione operativa della sospensione - blocco fatturazione, proroghe,
// ripresa - non e' implementata: nascondere finche' non c'e' la semantica).
// Resta come origine per ripristino di contratti gia' SOSPESI in DB
// (transizione manuale a ATTIVO o CESSATO).
const statiTransizionabili = computed(() => {
  if (!detail.value) return []
  const current = detail.value.stato_codice
  if (current === 'DRAFT') return ['ATTIVO']
  if (current === 'ATTIVO') return ['CESSATO']
  if (current === 'SOSPESO') return ['ATTIVO', 'CESSATO']
  return []
})

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
    :dismissable="true"
    @update:visible="val => emit('update:visible', val)"
    @after-show="onAfterShow"
  >
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('contratti.contratto')"
        icon="pi pi-file-edit"
      />
    </template>

    <div class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">
      <template v-if="contentReady">

      <!-- === Intestazione edit: numero + stato + azione affiancata === -->
      <template v-if="isEdit && detail">
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('contratti.field_numero') }}</label>
            <InputText :model-value="detail.numero" disabled class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('contratti.field_stato') }}</label>
            <div class="flex align-items-center gap-2">
              <Tag :value="detail.stato_descrizione" :severity="statoContrattoSeverity(detail.stato_codice)" />
              <Button v-for="stato in statiTransizionabili" :key="stato"
                :label="t(`contratti.azione_${stato.toLowerCase()}`)"
                :icon="stato === 'ATTIVO' ? 'pi pi-check' : stato === 'SOSPESO' ? 'pi pi-pause' : 'pi pi-times'"
                size="small" outlined
                class="app-escape"
                @click="onCambiaStato(stato)" />
            </div>
          </div>
        </div>

        <!-- Banner contratto bloccato: in stati post-DRAFT ammessa solo
             modifica valido_al (programma cessazione) + cambio stato.
             Coerente con Profilo A whitelist BE. -->
        <Message v-if="isContractLocked && detail.stato_codice !== 'CESSATO'"
          severity="info" :closable="false" size="small" class="mt-2">
          {{ t('contratti.banner_locked_attivo', { stato: detail.stato_descrizione }) }}
        </Message>
        <Message v-else-if="isContractLocked && detail.stato_codice === 'CESSATO'"
          severity="warn" :closable="false" size="small" class="mt-2">
          {{ t('contratti.banner_locked_cessato') }}
        </Message>
      </template>

      <!-- === Cliente (BA) + badge utility/PDP === -->
      <h4 class="mt-3">
        {{ t('contratti.section_cliente') }}
        <Tag v-if="baBadgeLabel" :value="baBadgeLabel" severity="info" class="ml-2" />
      </h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('contratti.field_billing_account') }} <span v-if="!isEdit">*</span></label>
          <BillingAccountLookup
            v-if="!isEdit"
            :model-value="form.billing_account_obj"
            @update:model-value="onBaSelected"
            :placeholder="t('contratti.select_billing_account')"
          />
          <InputText v-else :model-value="detail?.ba_ragione_sociale" disabled class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('contratti.field_ambito') }} <span v-if="!isEdit">*</span></label>
          <Select v-model="form.ambito" :options="ambitoOptions" option-label="label" option-value="value"
            class="w-full" :disabled="isEdit" />
        </div>
      </div>
      <!-- Categoria cliente snapshot: editabile in create e in DRAFT,
           bloccata dopo attivazione (trigger DB enforced) -->
      <div class="form-grid-2col mt-1">
        <div class="form-field">
          <label>{{ t('contratti.field_categoria_cliente_snapshot') }}</label>
          <LookupSelect
            v-model="form.categoria_cliente_id_snapshot"
            rel="anagrafiche.categorie_clienti"
            class="w-full"
            :placeholder="t('contratti.select_categoria_cliente')"
            show-clear
            :disabled="isEdit && detail?.stato_codice !== 'DRAFT'"
          />
        </div>
      </div>

      <!-- === Validità === -->
      <h4 class="mt-3">{{ t('contratti.section_validita') }}</h4>
      <div class="form-grid-3col">
        <div class="form-field">
          <label>{{ t('contratti.field_data') }} *</label>
          <DatePicker :model-value="parseIsoDate(form.data)"
            @update:model-value="form.data = toIsoDate($event)"
            date-format="dd/mm/yy" show-icon class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('contratti.field_valido_dal') }} *</label>
          <DatePicker :model-value="parseIsoDate(form.valido_dal)"
            @update:model-value="form.valido_dal = toIsoDate($event)"
            date-format="dd/mm/yy" show-icon class="w-full" />
        </div>
        <!-- Campo valido_al condizionale per stato:
             - DRAFT: editabile come "Fine validita' (opz.)"
             - ATTIVO/SOSPESO con valido_al impostato: readonly come
               "Cessazione programmata al {data}" (visibilita' su cessazione
               programmata futura, applicata via dialog Cessa)
             - ATTIVO/SOSPESO senza valido_al: nascosto (cessazione passa
               solo dal dialog dedicato)
             - CESSATO: readonly come "Data cessazione" -->
        <div class="form-field"
          v-if="!isEdit
            || detail?.stato_codice === 'DRAFT'
            || detail?.stato_codice === 'CESSATO'
            || (form.valido_al && (detail?.stato_codice === 'ATTIVO' || detail?.stato_codice === 'SOSPESO'))">
          <label>
            {{ detail?.stato_codice === 'CESSATO'
              ? t('contratti.field_data_cessazione')
              : (detail?.stato_codice === 'ATTIVO' || detail?.stato_codice === 'SOSPESO') && form.valido_al
                ? t('contratti.field_cessazione_programmata')
                : t('contratti.field_valido_al') }}
          </label>
          <DatePicker :model-value="parseIsoDate(form.valido_al)"
            @update:model-value="form.valido_al = toIsoDate($event)"
            :disabled="isEdit && detail?.stato_codice !== 'DRAFT'"
            date-format="dd/mm/yy" show-icon show-button-bar class="w-full" />
        </div>
      </div>

      <!-- === Pricing === -->
      <h4 class="mt-3">{{ t('contratti.section_pricing') }}</h4>
      <div class="form-field">
        <label>{{ t('contratti.field_modalita') }} *</label>
        <SelectButton v-model="form.modalita" :options="modalitaOptions"
          option-label="label" option-value="value"
          @change="onModalitaChange($event.value)"
          :allow-empty="false" />
        <Message severity="info" :closable="false" class="mt-05" size="small">
          {{ modalitaOptions.find(m => m.value === form.modalita)?.hint }}
        </Message>
      </div>

      <!-- Modalità A: listino + variazione globale -->
      <template v-if="form.modalita === 'A'">
        <div class="form-field">
          <label>{{ t('contratti.field_listino') }} *</label>
          <LookupSelect v-model="form.listino_id" rel="vendite.listini" class="w-full"
            :placeholder="t('contratti.select_listino')" />
        </div>
        <div class="form-grid-2col">
          <div class="form-field">
            <label>{{ t('contratti.field_tipo_variazione') }} *</label>
            <Select v-model="form.tipo_variazione_globale" :options="tipoVariazioneOptions"
              option-label="label" option-value="value" class="w-full" />
          </div>
          <div class="form-field">
            <label>{{ t('contratti.field_valore_variazione') }}</label>
            <InputNumber v-model="form.valore_variazione_globale" class="w-full"
              :min-fraction-digits="0" :max-fraction-digits="4" showButtons
              :suffix="form.tipo_variazione_globale === 'PERCENTUALE' ? ' %' : ''" />
            <small class="text-color-secondary">{{ t('contratti.hint_valore_variazione') }}</small>
          </div>
        </div>
      </template>

      <!-- Modalità B: listino + override righe -->
      <template v-else-if="form.modalita === 'B'">
        <div class="form-field">
          <label>{{ t('contratti.field_listino') }} *</label>
          <LookupSelect v-model="form.listino_id" rel="vendite.listini" class="w-full"
            :placeholder="t('contratti.select_listino')" />
        </div>
        <Message severity="info" :closable="false" size="small">
          {{ t('contratti.modalita_b_info') }}
        </Message>
      </template>

      <!-- Modalità C: tutto negoziato -->
      <template v-else>
        <Message severity="warn" :closable="false" size="small">
          {{ t('contratti.modalita_c_info') }}
        </Message>
      </template>

      <!-- === Tipo/Classe utenza (editabile in BOZZA, readonly dopo) === -->
      <h4 class="mt-3">{{ t('contratti.section_utenza') }}</h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('contratti.field_tipo_utenza') }}</label>
          <LookupSelect v-model="form.utility_tipo_utenza_id" rel="config.tipi_utenze" class="w-full"
            :placeholder="t('contratti.select_tipo_utenza')" show-clear
            :disabled="isEdit && detail?.stato_codice !== 'DRAFT'" />
        </div>
        <div class="form-field">
          <label>{{ t('contratti.field_classe_utenza') }}</label>
          <LookupSelect v-model="form.utility_classe_utenza_id" rel="config.classi_utenze" class="w-full"
            :placeholder="t('contratti.select_classe_utenza')" show-clear
            :disabled="isEdit && detail?.stato_codice !== 'DRAFT'" />
        </div>
      </div>

      <!-- === Note === -->
      <h4 class="mt-3">{{ t('contratti.section_note') }}</h4>
      <div class="form-field">
        <Textarea v-model="form.meta_note" rows="2" autoResize class="w-full" />
      </div>

      <!-- === Gestione righe (solo edit) === -->
      <template v-if="isEdit && detail">
        <h4 class="mt-3">{{ t('contratti.section_gestione') }}</h4>
        <div class="form-row-inline">
          <Button icon="pi pi-list" :label="t('contratti.gestisci_righe')"
            outlined class="app-manage-btn"
            @click="righeVisible = true" />
          <span class="text-color-secondary">{{ detail.righe?.length || 0 }} {{ t('contratti.righe_count_label') }}</span>
        </div>
      </template>

      <DrawerFooter :loading="loading" :disabled="!canSave" @save="handleSave" @cancel="onClose" />
      </template>
    </div>

    <!-- Sub-drawer: gestione righe -->
    <ContrattoRigheDrawer
      v-if="isEdit && detail"
      :visible="righeVisible"
      @update:visible="v => righeVisible = v"
      :contratto-id="props.contrattoId"
      :contratto-modalita="form.modalita"
      :righe-iniziali="detail.righe || []"
      :contratto-numero="detail.numero"
      :contratto-cliente="detail.ba_ragione_sociale"
      :contratto-valido-dal="detail.valido_dal"
      :contratto-valido-al="detail.valido_al"
      :contratto-stato-codice="detail.stato_codice"
      :contratto-stato-descrizione="detail.stato_descrizione"
      @changed="refreshDetail"
    />

    <!-- Dialog cessazione contratto: chiede la data di cessazione (default
         oggi) e fa POST cambia-stato {CESSATO, valido_al} in transazione BE.
         Comportamento data-driven:
         - data < oggi  -> cessazione immediata, stato CESSATO
         - data >= oggi -> cessazione programmata, stato resta ATTIVO/SOSPESO -->
    <Dialog v-model:visible="cessaDialogVisible" modal
      :header="cessazioneProgrammata
        ? t('contratti.cessa_dialog_titolo_programma')
        : t('contratti.cessa_dialog_titolo_immediata')"
      :style="{ width: '460px' }">
      <div class="form-field">
        <label>{{ t('contratti.cessa_dialog_data') }}</label>
        <DatePicker v-model="cessaDialogData" date-format="dd/mm/yy"
          show-icon show-button-bar />
      </div>
      <Message :severity="cessazioneProgrammata ? 'info' : 'warn'"
        :closable="false" class="mt-1" size="small">
        {{ cessazioneProgrammata
          ? t('contratti.cessa_dialog_warning_programmata')
          : t('contratti.cessa_dialog_warning_immediata') }}
      </Message>
      <template #footer>
        <Button :label="t('common.cancel')" text severity="secondary"
          @click="cessaDialogVisible = false" />
        <Button :label="cessazioneProgrammata
            ? t('contratti.cessa_dialog_conferma_programma')
            : t('contratti.cessa_dialog_conferma_immediata')"
          :icon="cessazioneProgrammata ? 'pi pi-calendar' : 'pi pi-times'"
          :severity="cessazioneProgrammata ? 'warn' : 'danger'"
          :disabled="!cessaDialogData || loading" :loading="loading"
          @click="onConfermaCessazione" />
      </template>
    </Dialog>

  </Drawer>
</template>

<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Drawer del singolo TITOLO IVA del soggetto (I7 / D10 del brief
// brief-be-fe-titoli-iva-soggetto): il documento registrato che SOSTITUISCE
// l'aliquota ordinaria di una riga.
//
// ⭐ Drawer AUTONOMO (`feedback_drawer_autonomi`): lo apre la lista dei titoli
//   del soggetto e — quando ci sara' — la lista di presidio dei titoli sfondati.
//   Non conosce chi lo ha aperto: riceve `soggettoId` e `titoloId`.
//
// ⚠️ IL PLAFOND SI VEDE SOLO SE IL TIPO HA UN TETTO. Non e' cosmesi: e' la
//   decisione del modello (`config.tipi_titolo_iva.ha_plafond`), e mostrare il
//   campo su un tipo che un tetto non ce l'ha produrrebbe un numero che nessuno
//   consuma — cioe' la voce 2 del brief madre in miniatura, un campo che promette
//   una cosa che non succede. Il guard vero e' a DB
//   (`E_TITOLO_IVA_PLAFOND_NON_AMMESSO`): qui si evita solo di proporlo.
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useDrawerClose } from '../../core/composables/useDrawerClose'
import { useInjectReadonly } from '../../core/composables/useReadonlyMode'
import { useConfirmAction } from '../../core/composables/useConfirmAction'
import { labelOrCode } from '../../core/utils/i18nLabel'
import { useDrawerContentReady } from '../../core/composables/useDrawerContentReady'
import { useFetchVersion } from '../../core/composables/useFetchVersion'
import { useEmittenteFiscaleField } from '../../core/composables/useEmittenteFiscaleField'
import { useGlobalLookup } from '../../core/composables/useGlobalLookup'
import { lookupCodici } from '../../core/apiCore'
import {
  getSoggettoTitoloIva,
  createSoggettoTitoloIva,
  updateSoggettoTitoloIva,
  createTitoloIvaAmbito,
  deleteTitoloIvaAmbito,
  annullaTitoloIvaMovimento,
  createTitoloIvaForzatura,
} from '../api/anagrafiche'
import { DRAWER_WIDTH, MANAGE_ICONS } from '../../core/constants'
import { toDateString, parseIsoDate, displayDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import DrawerTitle from '../../core/components/DrawerTitle.vue'
import FormFooter from '../../core/components/FormFooter.vue'
import AppDialog from '../../core/components/AppDialog.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import IvaSelect from '../../core/components/IvaSelect.vue'
import EmittenteFiscaleField from '../../core/components/EmittenteFiscaleField.vue'
import ArticoloLookup from '../../core/components/ArticoloLookup.vue'
import Drawer from 'primevue/drawer'
import Select from 'primevue/select'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import DatePicker from 'primevue/datepicker'
import Textarea from 'primevue/textarea'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'

const { t, te } = useI18n()
const { execute, loading, campiErrati } = useApiHandler()
const isReadonly = useInjectReadonly()
const { confirmDelete } = useConfirmAction()
const { defaultEmittenteId } = useEmittenteFiscaleField()

const props = defineProps({
  visible: { type: Boolean, default: false },
  soggettoId: { type: String, default: null },
  titoloId: { type: Number, default: null },
})
const emit = defineEmits(['update:visible', 'saved'])

const isEdit = computed(() => props.titoloId != null)
const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)
// ⚠️ Guard di versione: il drawer si apre su un titolo, si chiude e si riapre su
//    un altro piu' in fretta di quanto torni la prima fetch. Senza, la risposta
//    stantia sovrascrive il form del titolo giusto — e non da' nessun errore.
const fv = useFetchVersion()

const form = ref(defaultForm())
const detail = ref(null)
const ambiti = ref([])

// Ambito dichiarato, mai dedotto da un NULL (D12).
const ambitoOptions = computed(() => [
  { value: 'TUTTO', label: t('anagrafiche.titoli_iva.ambito_tutto') },
  { value: 'RISTRETTO', label: t('anagrafiche.titoli_iva.ambito_ristretto') },
])
const livelloOptions = computed(() => [
  { value: 'ARTICOLO', label: t('anagrafiche.titoli_iva.livello_articolo') },
  { value: 'GRUPPO_VOCE', label: t('anagrafiche.titoli_iva.livello_gruppo_voce') },
  { value: 'TIPO_VOCE', label: t('anagrafiche.titoli_iva.livello_tipo_voce') },
])

// ⭐ `ha_plafond` arriva dalla STESSA cache che alimenta il Select
//   (`useGlobalLookup` per chiave: una sola fetch condivisa), e non da un
//   handler `@change` — `LookupSelect` emette l'ID, non l'opzione, quindi
//   leggere `opt.ha_plafond` da li' sarebbe stato SEMPRE falso e il campo
//   plafond non sarebbe MAI comparso, in silenzio.
// 📌 La colonna e' esposta dal lookup perche' `config.tipi_titolo_iva` e' stata
//   registrata fra le lookup SPECIALIZZATE lato BE: e' il meccanismo che esiste
//   apposta per «il contratto generico piu' UNA colonna».
const { items: tipiTitolo } = useGlobalLookup(
  'config.tipi_titolo_iva',
  () => lookupCodici('config.tipi_titolo_iva'),
  { immediate: true },
)
const tipoSelezionato = computed(
  () => tipiTitolo.value.find(x => x.id === form.value.tipo_titolo_iva_id) || null,
)
// ⚠️ Ripiego sul dettaglio finche' il lookup non e' arrivato: in edit il campo
//   non deve sfarfallare da assente a presente.
const mostraPlafond = computed(() => (
  tipoSelezionato.value ? !!tipoSelezionato.value.ha_plafond
                        : !!detail.value?.tipo_ha_plafond
))

// ⚠️ RISTRETTO con zero righe: il BE lo DICHIARA (`ambito_incompleto`), qui non
//   si ri-deriva la regola. Si avvisa e non si blocca (Q2): il DB ammette quello
//   stato apposta, perche' il caso si costruisce in due istruzioni.
// ⚠️ Solo in EDIT: in creazione le righe di ambito non si possono ancora
//   aggiungere (il titolo non ha un id), quindi l'avviso direbbe all'operatore
//   di fare una cosa che non puo' fare — e' rumore, non un presidio.
//   Il caso si costruisce in due istruzioni ed e' voluto (Q2): l'avviso compare
//   al primo rientro, quando c'e' il pulsante per rimediare.
const ambitoIncompleto = computed(
  () => isEdit.value && form.value.ambito === 'RISTRETTO' && ambiti.value.length === 0,
)

function defaultForm() {
  return {
    emittente_fiscale_id: defaultEmittenteId.value ?? null,
    tipo_titolo_iva_id: null,
    iva_id: null,
    ambito: 'TUTTO',
    valido_dal: null,
    valido_al: null,
    protocollo: null,
    data_ricezione: null,
    riferimento: null,
    plafond: null,
    attivo: true,
    note: null,
  }
}

function populateFromDetail(d) {
  form.value = {
    emittente_fiscale_id: d.emittente_fiscale_id,
    tipo_titolo_iva_id: d.tipo_titolo_iva_id,
    iva_id: d.iva_id,
    ambito: d.ambito,
    valido_dal: d.valido_dal,
    valido_al: d.valido_al,
    protocollo: d.protocollo,
    data_ricezione: d.data_ricezione,
    riferimento: d.riferimento,
    plafond: d.plafond != null ? Number(d.plafond) : null,
    attivo: d.attivo,
    note: d.note,
  }
  ambiti.value = d.ambiti || []
}

watch(() => props.visible, async (val) => {
  if (!val) { fv.invalidate(); return }
  const v = fv.tag()
  ambiti.value = []
  if (isEdit.value) {
    const res = await execute(() => getSoggettoTitoloIva(props.soggettoId, props.titoloId))
    if (res === null || !fv.isCurrent(v)) return
    detail.value = res.data.data
    populateFromDetail(detail.value)
  } else {
    detail.value = null
    form.value = defaultForm()
  }
})

// Scopo: passando a un tipo SENZA tetto, il plafond digitato si azzera.
// ⚠️ Non e' cortesia: `E_TITOLO_IVA_PLAFOND_NON_AMMESSO` rifiuterebbe il
//   salvataggio, e il campo sarebbe gia' sparito dallo schermo — l'operatore
//   vedrebbe un errore su un valore che non vede piu'.
watch(mostraPlafond, (ha) => { if (!ha) form.value.plafond = null })

const canSave = computed(() => {
  if (isReadonly.value) return false
  const f = form.value
  if (!f.tipo_titolo_iva_id || !f.iva_id || !f.valido_dal) return false
  if (!isEdit.value && !f.emittente_fiscale_id) return false
  return true
})

function buildPayload() {
  const f = form.value
  const p = {
    tipo_titolo_iva_id: f.tipo_titolo_iva_id,
    iva_id: f.iva_id,
    ambito: f.ambito,
    valido_dal: toDateString(f.valido_dal),
    valido_al: toDateString(f.valido_al),
    protocollo: f.protocollo?.trim() || null,
    data_ricezione: toDateString(f.data_ricezione),
    riferimento: f.riferimento?.trim() || null,
    // ⚠️ Solo se il tipo ha un tetto: mandarlo su un tipo che non ce l'ha
    //   sarebbe respinto da `E_TITOLO_IVA_PLAFOND_NON_AMMESSO`.
    plafond: mostraPlafond.value && f.plafond != null ? String(f.plafond) : null,
    note: f.note?.trim() || null,
  }
  // ⛔ `emittente_fiscale_id` SOLO in create (Q5): spostarlo sposterebbe sotto un
  //   altro fornitore anche il plafond gia' consumato, perche' i movimenti sono
  //   attaccati al titolo. Il BE non lo accetta nemmeno in PATCH.
  if (!isEdit.value) p.emittente_fiscale_id = f.emittente_fiscale_id
  else p.attivo = f.attivo
  return p
}

async function onSave() {
  const azione = isEdit.value
    ? () => updateSoggettoTitoloIva(props.soggettoId, props.titoloId, buildPayload())
    : () => createSoggettoTitoloIva(props.soggettoId, buildPayload())
  const result = await execute(azione, {
    successMessage: isEdit.value
      ? t('anagrafiche.titoli_iva.titolo_salvato')
      : t('anagrafiche.titoli_iva.titolo_creato'),
  })
  if (result !== null) {
    emit('saved')
    emit('update:visible', false)
  }
}

// === Ambiti (master-detail inline) ===
const ambitoForm = ref(nuovoAmbito())
const ambitoFormAperto = ref(false)

function nuovoAmbito() {
  return {
    livello: 'ARTICOLO', articolo_id: null, articolo_obj: null,
    gruppo_voce_id: null, tipo_voce_id: null, note: null,
  }
}

// Scopo: cambiando livello si azzerano gli altri due oggetti.
// ⚠️ Non e' cortesia: `chk_soggetti_titoli_iva_ambiti_livello` pretende che le
//   altre due colonne siano NULL. Il BE normalizza comunque, ma lasciare il
//   residuo a video mostrerebbe una scelta che non verra' salvata.
function onLivelloChange() {
  const a = ambitoForm.value
  a.articolo_id = null; a.articolo_obj = null
  a.gruppo_voce_id = null; a.tipo_voce_id = null
}

const ambitoValido = computed(() => {
  const a = ambitoForm.value
  if (a.livello === 'ARTICOLO') return !!a.articolo_id
  if (a.livello === 'GRUPPO_VOCE') return !!a.gruppo_voce_id
  if (a.livello === 'TIPO_VOCE') return !!a.tipo_voce_id
  return false
})

async function onAddAmbito() {
  const a = ambitoForm.value
  const res = await execute(
    () => createTitoloIvaAmbito(props.soggettoId, props.titoloId, {
      livello: a.livello,
      articolo_id: a.articolo_id || null,
      gruppo_voce_id: a.gruppo_voce_id || null,
      tipo_voce_id: a.tipo_voce_id || null,
      note: a.note?.trim() || null,
    }),
    { successMessage: t('anagrafiche.titoli_iva.ambito_aggiunto') },
  )
  if (res === null) return
  ambitoForm.value = nuovoAmbito()
  ambitoFormAperto.value = false
  await ricaricaDettaglio()
}

function onDeleteAmbito(riga) {
  confirmDelete(descriviAmbito(riga), async () => {
    const res = await execute(
      () => deleteTitoloIvaAmbito(props.soggettoId, props.titoloId, riga.id),
      { successMessage: t('anagrafiche.titoli_iva.ambito_rimosso') },
    )
    if (res !== null) await ricaricaDettaglio()
  })
}

// Scopo: rilegge il dettaglio dal BE dopo una scrittura sui figli.
// ⚠️ Serve DOPO ogni movimento, non solo dopo gli ambiti: `imponibile_utilizzato`
//   e `residuo` li ricalcola un trigger, quindi il valore giusto lo sa solo il
//   database — aggiornarli a mano lato client sarebbe la seconda verita' che D5
//   ha tolto di mezzo.
async function ricaricaDettaglio() {
  const v = fv.tag()
  const res = await execute(() => getSoggettoTitoloIva(props.soggettoId, props.titoloId))
  if (res === null || !fv.isCurrent(v)) return
  detail.value = res.data.data
  ambiti.value = detail.value.ambiti || []
  emit('saved')
}

// Scopo: come si nomina una riga di ambito nella conferma di eliminazione.
// ⚠️ Il NOME della merce, mai l'id: e' la stessa regola dei messaggi di errore
//   del team DB — «nel VARIADIC il tipo di titolo e il NOME della merce».
function descriviAmbito(r) {
  return r.articolo_descrizione || r.gruppo_voce_descrizione
    || r.tipo_voce_descrizione || `#${r.id}`
}

// === Registro movimenti (D5) e forzatura manuale (Q3) ===

// Scopo: la frase che spiega perche' l'annullo e' spento.
// ⛔ Viaggia la CHIAVE, non il testo: il messaggio e' multilingua e vive nei
//    locales. `labelOrCode` mostra il codice grezzo se la chiave manca — il
//    vocabolario dei motivi e' del DB e puo' crescere.
function motivoAnnullo(riga) {
  return labelOrCode(t, te, riga.annullo_blocco_reason_key, riga.annullo_blocco_codice)
}

// Scopo: apre il dialog dell'annullo sulla riga scelta (Q7).
// ⚠️ Il motivo si chiede PRIMA: e' la traccia del perche', ed e' quello che
//    rende il registro leggibile a distanza di mesi. Non lo si lascia scoprire
//    dal rifiuto del `CHECK`.
function onAnnullaMovimento(riga) {
  annullo.value = { movimento_id: riga.id, motivo: '' }
  annulloVisible.value = true
}

const annulloValido = computed(() => !!annullo.value.motivo?.trim())

// Scopo: scrive il CONTRO-MOVIMENTO. Non e' una delete e non e' un update:
//        e' una riga nuova che punta a quella annullata, e l'accumulatore
//        torna al valore giusto da solo (Q7).
async function onSalvaAnnullo() {
  const res = await execute(
    () => annullaTitoloIvaMovimento(
      props.soggettoId, props.titoloId, annullo.value.movimento_id,
      { motivo: annullo.value.motivo.trim() },
    ),
    { successMessage: t('anagrafiche.titoli_iva.movimento_annullato') },
  )
  // ⚠️ `!== null` e non `if (res)`: un esito legittimamente falsy non e' un
  //    fallimento — e' la regola `feedback_drawer_result_check`.
  if (res === null) return
  annulloVisible.value = false
  await ricaricaDettaglio()
}

const movimenti = computed(() => detail.value?.movimenti || [])
const forzaturaVisible = ref(false)
const forzatura = ref(nuovaForzatura())

const annulloVisible = ref(false)
const annullo = ref({ movimento_id: null, motivo: '' })

function nuovaForzatura() {
  return { imponibile: null, data_movimento: new Date(), motivo: '' }
}

// ⚠️ Lo ZERO non passa: `chk_stiva_movimenti_segno` lo rifiuta, e un movimento
//   che non muove niente non e' una correzione — e' rumore nel registro.
//   Il SEGNO invece resta libero: una forzatura corregge in entrambe le
//   direzioni, e in diminuzione e' il caso piu' frequente (uno storno).
const forzaturaValida = computed(() => {
  const f = forzatura.value
  return !!f.imponibile && Number(f.imponibile) !== 0
    && !!f.data_movimento && !!f.motivo?.trim()
})

async function onSalvaForzatura() {
  const f = forzatura.value
  const res = await execute(
    () => createTitoloIvaForzatura(props.soggettoId, props.titoloId, {
      imponibile: String(f.imponibile),
      data_movimento: toDateString(f.data_movimento),
      motivo: f.motivo.trim(),
    }),
    { successMessage: t('anagrafiche.titoli_iva.forzatura_registrata') },
  )
  if (res === null) return
  forzaturaVisible.value = false
  forzatura.value = nuovaForzatura()
  await ricaricaDettaglio()
}

// Come si nomina il documento che ha mosso il plafond. Le forzature non ne
// hanno uno, ed e' proprio cio' che le distingue nel registro.
function descriviDocumento(m) {
  if (m.tipo_movimento === 'FORZATURA') return t('anagrafiche.titoli_iva.mov_manuale')
  return m.fattura_id ? `#${m.fattura_id}` : '—'
}

function movimentoSeverity(tipo) {
  return { FATTURA: 'info', NOTA_CREDITO: 'success', FORZATURA: 'warn' }[tipo] || 'secondary'
}

const onClose = useDrawerClose(emit)
</script>

<template>
  <!-- ⛔ `DRAWER_WIDTH.WIDE` e non `.LARGE`: quella chiave NON ESISTE in
       `constants.js`, e per mesi questo drawer e' stato largo **320px** — il
       default di PrimeVue per un drawer laterale. Nessun errore: `undefined`
       finisce in `width` e il browser ignora la regola, il build e' verde,
       ESLint tace. A video le griglie a 2 e 3 colonne collassavano in una e la
       maschera sembrava «scritta male» quando era solo strizzata.
       ⇒ Presidiato da `scripts/check-drawer-width.mjs`, che nasce da qui. -->
  <Drawer
    :visible="visible" @update:visible="emit('update:visible', $event)"
    position="right" :style="{ width: DRAWER_WIDTH.WIDE }" @after-show="onAfterShow">
    <template #header>
      <DrawerTitle
        :action="isEdit ? t('common.edit') : t('common.new')"
        :title="t('anagrafiche.titoli_iva.titolo')"
        :icon="MANAGE_ICONS.TITOLI_IVA" />
    </template>

    <div v-if="contentReady" class="app-drawer-content" :class="{ 'app-readonly': isReadonly }">

      <!-- ⚠️ Avviso, non blocco (Q2): il DB ammette apposta un titolo RISTRETTO
           senza righe, perche' il caso si costruisce in due istruzioni. Il
           messaggio dice l'EFFETTO, non lo stato. -->
      <Message v-if="ambitoIncompleto" severity="warn" :closable="false" class="mb-2">
        {{ t('anagrafiche.titoli_iva.avviso_ambito_incompleto') }}
      </Message>

      <h4>{{ t('anagrafiche.titoli_iva.section_titolo') }}</h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.field_emittente') }} <span v-if="!isEdit">*</span></label>
          <EmittenteFiscaleField
            v-model="form.emittente_fiscale_id"
            :record="detail" :is-edit="isEdit" :disabled="isReadonly" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.field_tipo') }} *</label>
          <LookupSelect
            v-model="form.tipo_titolo_iva_id" rel="config.tipi_titolo_iva"
            class="w-full" :disabled="isReadonly"
            :placeholder="t('anagrafiche.titoli_iva.select_tipo')" />
        </div>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.field_iva') }} *</label>
          <IvaSelect v-model="form.iva_id" :disabled="isReadonly" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.field_ambito') }}</label>
          <Select v-model="form.ambito" :options="ambitoOptions"
            option-label="label" option-value="value" class="w-full"
            :disabled="isReadonly" />
        </div>
      </div>

      <h4 class="mt-3">{{ t('anagrafiche.titoli_iva.section_validita') }}</h4>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.field_valido_dal') }} *</label>
          <DatePicker :model-value="parseIsoDate(form.valido_dal)"
            @update:model-value="form.valido_dal = toDateString($event)"
            date-format="dd/mm/yy" show-icon class="w-full" :disabled="isReadonly"
            :invalid="campiErrati.includes('valido_dal')" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.field_valido_al') }}</label>
          <DatePicker :model-value="parseIsoDate(form.valido_al)"
            @update:model-value="form.valido_al = toDateString($event)"
            date-format="dd/mm/yy" show-icon show-button-bar class="w-full"
            :disabled="isReadonly" />
        </div>
      </div>

      <h4 class="mt-3">{{ t('anagrafiche.titoli_iva.section_prova') }}</h4>
      <div class="form-grid-3col">
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.field_protocollo') }}</label>
          <InputText v-model="form.protocollo" class="w-full" :disabled="isReadonly" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.field_data_ricezione') }}</label>
          <DatePicker :model-value="parseIsoDate(form.data_ricezione)"
            @update:model-value="form.data_ricezione = toDateString($event)"
            date-format="dd/mm/yy" show-icon show-button-bar class="w-full"
            :disabled="isReadonly" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.field_riferimento') }}</label>
          <InputText v-model="form.riferimento" class="w-full" :disabled="isReadonly" />
        </div>
      </div>

      <!-- Il plafond esiste solo per i tipi che un tetto ce l'hanno (D10). -->
      <template v-if="mostraPlafond">
        <h4 class="mt-3">{{ t('anagrafiche.titoli_iva.section_plafond') }}</h4>
        <div class="form-grid-3col">
          <div class="form-field">
            <label>{{ t('anagrafiche.titoli_iva.field_plafond') }}</label>
            <InputNumber v-model="form.plafond" mode="currency" currency="EUR" locale="it-IT"
              class="w-full" :disabled="isReadonly" />
          </div>
          <div v-if="isEdit" class="form-field">
            <label>{{ t('anagrafiche.titoli_iva.field_utilizzato') }}</label>
            <!-- ⚠️ Sola lettura SEMPRE: lo scrive il trigger dell'accumulatore
                 come somma del registro (D5). Un campo editabile qui sarebbe il
                 «numero sovrascritto» che D5 ha tolto di mezzo. -->
            <InputText :model-value="formatCurrency(detail?.imponibile_utilizzato)"
              disabled class="w-full" />
          </div>
          <div v-if="isEdit" class="form-field">
            <label>{{ t('anagrafiche.titoli_iva.field_residuo') }}</label>
            <InputText :model-value="formatCurrency(detail?.residuo)"
              disabled class="w-full" />
          </div>
        </div>
      </template>

      <!-- === Ambito ristretto: su cosa si applica (D12) === -->
      <template v-if="form.ambito === 'RISTRETTO' && isEdit">
        <h4 class="mt-3">{{ t('anagrafiche.titoli_iva.section_ambito') }}</h4>
        <p class="text-color-secondary" style="font-size: 0.85rem;">
          {{ t('anagrafiche.titoli_iva.ambito_hint') }}
        </p>

        <DataTable :value="ambiti" class="app-datatable" data-key="id" size="small">
          <Column field="livello" :header="t('anagrafiche.titoli_iva.col_livello')">
            <template #body="{ data }">
              <Tag :value="t(`anagrafiche.titoli_iva.livello_${data.livello.toLowerCase()}`)"
                severity="info" />
            </template>
          </Column>
          <Column :header="t('anagrafiche.titoli_iva.col_oggetto')">
            <template #body="{ data }">{{ descriviAmbito(data) }}</template>
          </Column>
          <Column v-if="!isReadonly" style="width: 4rem">
            <template #body="{ data }">
              <Button :icon="MANAGE_ICONS.DELETE" text severity="danger"
                @click="onDeleteAmbito(data)" />
            </template>
          </Column>
          <template #empty>{{ t('anagrafiche.titoli_iva.ambito_vuoto') }}</template>
        </DataTable>

        <div v-if="!isReadonly" class="mt-2">
          <Button v-if="!ambitoFormAperto" :label="t('anagrafiche.titoli_iva.aggiungi_ambito')"
            :icon="MANAGE_ICONS.ADD" outlined size="small"
            @click="ambitoFormAperto = true" />
          <div v-else class="app-drawer-section">
            <div class="form-grid-2col">
              <div class="form-field">
                <label>{{ t('anagrafiche.titoli_iva.col_livello') }}</label>
                <Select v-model="ambitoForm.livello" :options="livelloOptions"
                  option-label="label" option-value="value" class="w-full"
                  @change="onLivelloChange" />
              </div>
              <div class="form-field">
                <label>{{ t('anagrafiche.titoli_iva.col_oggetto') }}</label>
                <ArticoloLookup v-if="ambitoForm.livello === 'ARTICOLO'"
                  v-model="ambitoForm.articolo_obj"
                  @select="ambitoForm.articolo_id = $event?.id ?? null" />
                <LookupSelect v-else-if="ambitoForm.livello === 'GRUPPO_VOCE'"
                  v-model="ambitoForm.gruppo_voce_id" rel="vendite.articoli_gruppi"
                  class="w-full" />
                <LookupSelect v-else v-model="ambitoForm.tipo_voce_id"
                  rel="vendite.articoli_tipologie" class="w-full" />
              </div>
            </div>
            <div class="flex gap-2 mt-2">
              <Button :label="t('common.add')" :icon="MANAGE_ICONS.ADD" size="small"
                :disabled="!ambitoValido" :loading="loading" @click="onAddAmbito" />
              <Button :label="t('common.cancel')" text size="small"
                @click="ambitoFormAperto = false; ambitoForm = nuovoAmbito()" />
            </div>
          </div>
        </div>
      </template>

      <!-- === Registro del plafond (D5) ===
           ⭐ Compare solo dove un tetto esiste: su un tipo senza plafond nessuno
           scrive movimenti, e un pannello sempre vuoto e' peggio di uno assente.
           ⛔ Il totale e' `imponibile_utilizzato`, che il trigger tiene pari alla
           somma del registro: il FE NON lo ricalcola sommando le righe: sarebbe
           una seconda verita' sullo stesso numero, cioe' il difetto che D5
           esiste per evitare. -->
      <template v-if="isEdit && mostraPlafond">
        <h4 class="mt-3">{{ t('anagrafiche.titoli_iva.section_registro') }}</h4>
        <DataTable :value="movimenti" class="app-datatable" data-key="id" size="small">
          <Column :header="t('anagrafiche.titoli_iva.col_data')">
            <template #body="{ data }">{{ displayDate(data.data_movimento) }}</template>
          </Column>
          <Column :header="t('anagrafiche.titoli_iva.col_movimento')">
            <template #body="{ data }">
              <Tag :value="t(`anagrafiche.titoli_iva.mov_${data.tipo_movimento.toLowerCase()}`)"
                :severity="movimentoSeverity(data.tipo_movimento)" />
            </template>
          </Column>
          <Column :header="t('anagrafiche.titoli_iva.col_imponibile')">
            <template #body="{ data }">{{ formatCurrency(data.imponibile) }}</template>
          </Column>
          <Column :header="t('anagrafiche.titoli_iva.col_documento')">
            <template #body="{ data }">{{ descriviDocumento(data) }}</template>
          </Column>
          <Column field="motivo" :header="t('anagrafiche.titoli_iva.col_motivo')" />
          <!-- ⭐ L'ANNULLO (Q7), col motivo quando e' spento. Il pulsante non
               sparisce: resta e SPIEGA — un pulsante grigio che non dice perche'
               e' indistinguibile da un bug.
               ⛔ Il motivo arriva dalla vista, e lo produce la STESSA check che
               la madre interroga per rifiutare: tooltip e rifiuto non possono
               divergere. -->
          <Column v-if="!isReadonly" style="width: 4rem">
            <template #body="{ data }">
              <span class="app-action-tooltip-wrap"
                v-tooltip.top="data.annullo_blocco_codice ? motivoAnnullo(data) : t('anagrafiche.titoli_iva.annulla_movimento')">
                <Button :icon="MANAGE_ICONS.UNDO" text severity="danger" size="small"
                  :disabled="!!data.annullo_blocco_codice"
                  :aria-label="t('anagrafiche.titoli_iva.annulla_movimento')"
                  @click="onAnnullaMovimento(data)" />
              </span>
            </template>
          </Column>
          <template #empty>{{ t('anagrafiche.titoli_iva.registro_vuoto') }}</template>
        </DataTable>

        <!-- ⛔ Da qui si scrive SOLO una forzatura (Q3): i movimenti di fattura e
             nota di credito li produce la fatturazione, dalla primitiva che
             tiene il lock. Il pulsante lo dice nel nome. -->
        <Button v-if="!isReadonly" class="mt-2"
          :label="t('anagrafiche.titoli_iva.forza_rettifica')"
          :icon="MANAGE_ICONS.EDIT" outlined size="small"
          @click="forzaturaVisible = true" />
      </template>

      <div v-if="isEdit" class="form-field mt-3">
        <label>{{ t('anagrafiche.titoli_iva.field_note') }}</label>
        <Textarea v-model="form.note" rows="2" class="w-full" :disabled="isReadonly" />
      </div>

      <FormFooter v-if="!isReadonly" :loading="loading" :disabled="!canSave"
        @save="onSave" @cancel="onClose" />
      <FormFooter v-else close-only @cancel="onClose" />
    </div>

    <!-- L'annullo di una forzatura (Q7): un contro-movimento, non una delete. -->
    <AppDialog
      v-model:visible="annulloVisible"
      :header="t('anagrafiche.titoli_iva.annulla_movimento')"
      width="md" :loading="loading" :save-disabled="!annulloValido"
      :save-label="t('anagrafiche.titoli_iva.annulla_movimento')"
      @save="onSalvaAnnullo" @cancel="annulloVisible = false">
      <p class="text-color-secondary" style="font-size: 0.85rem;">
        {{ t('anagrafiche.titoli_iva.annullo_hint') }}
      </p>
      <div class="form-field">
        <label>{{ t('anagrafiche.titoli_iva.col_motivo') }} *</label>
        <Textarea v-model="annullo.motivo" rows="2" class="w-full" />
      </div>
    </AppDialog>

    <!-- Forzatura manuale del plafond (Q3 + D5). -->
    <AppDialog
      v-model:visible="forzaturaVisible"
      :header="t('anagrafiche.titoli_iva.forza_rettifica')"
      width="md" :loading="loading" :save-disabled="!forzaturaValida"
      :save-label="t('anagrafiche.titoli_iva.registra_forzatura')"
      @save="onSalvaForzatura" @cancel="forzaturaVisible = false">
      <p class="text-color-secondary" style="font-size: 0.85rem;">
        {{ t('anagrafiche.titoli_iva.forzatura_hint') }}
      </p>
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.col_imponibile') }} *</label>
          <InputNumber v-model="forzatura.imponibile" mode="currency" currency="EUR"
            locale="it-IT" class="w-full" />
        </div>
        <div class="form-field">
          <label>{{ t('anagrafiche.titoli_iva.col_data') }} *</label>
          <DatePicker v-model="forzatura.data_movimento" date-format="dd/mm/yy"
            show-icon class="w-full" />
        </div>
      </div>
      <div class="form-field">
        <label>{{ t('anagrafiche.titoli_iva.col_motivo') }} *</label>
        <Textarea v-model="forzatura.motivo" rows="2" class="w-full" />
      </div>
    </AppDialog>
  </Drawer>
</template>

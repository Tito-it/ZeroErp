<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il form con cui si APRE una distinta contabile (Q-3 -> a, decisione di
//        Tid: «l'operatore deve poter caricare delle informazioni per aprire la
//        specifica contabile»).
//
// ⛔ NON un pulsante che crea al volo con dei default: un form. E' il foglio su
//    cui finira' del denaro, e chi lo apre dichiara di quale giornata e di quale
//    canale sta parlando.
//
// ⭐ IL CANALE SI SCEGLIE PER PRIMO E IL CENTRO SI DERIVA DA LUI. L'ente porta
//    il proprio `centro_riscossione_id` e un guard del database rifiuta la
//    coppia incoerente: chiederli entrambi a mano significa costruire un errore
//    che si puo' evitare. ⚠️ Il centro resta comunque OBBLIGATORIO nel payload —
//    il backend lo pretende sempre — quindi qui si deriva, non si omette.
//
// ⚠️ E il form deve reggere il caso SENZA canale (la cassa): finche' nessun
//    canale e' configurato si sceglie il centro direttamente. Oggi
//    `enti_incasso` e' a zero righe — ma dal 2026-08-28 e' a zero perche'
//    nessuno ne ha ancora creato uno, non perche' non si possa (DATO-1 chiuso).
//
// ⭐ E LA DISTINTA SA DI CHI E' (D3/D4 del brief distinta-numerata-sul-registro,
//    2026-09-17): il codice nasce sul registro dell'emittente, quindi
//    l'emittente si decide QUI. Col canale scelto e' il suo — il conto su cui
//    atterra il denaro ha un solo padrone — e il campo NON si mostra: chiederlo
//    sarebbe costruire un dissenso che il database rifiuterebbe. Senza canale
//    (la cassa) e' quello della SESSIONE, mostrato dal BB `EmittenteFiscaleField`
//    in sola lettura: l'emittente di lavoro si sceglie una volta dalla topbar
//    (decisione di Tid, 2026-09-02), e chi sta in «tutti gli emittenti» vede
//    l'avviso del BB e non puo' aprire — e' il livello 4 del database
//    (`E_CONTABILE_EMITTENTE_OBBLIGATORIO`) detto PRIMA di premere.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Textarea from 'primevue/textarea'

import AppDialog from '../../core/components/AppDialog.vue'
import EmittenteFiscaleField from '../../core/components/EmittenteFiscaleField.vue'
import LookupSelect from '../../core/components/LookupSelect.vue'
import { useApiHandler } from '../../core/composables/useApiHandler'
import { useEmittenteFiscaleField } from '../../core/composables/useEmittenteFiscaleField'
import { useNotify } from '../../core/composables/useNotify'
import { DATE_FORMAT } from '../../core/constants'
import { toDateString, oggiAziendale } from '../../core/utils/date'
import { creaDistinta } from '../api/pagamenti'
import { useCanaliIncasso } from '../composables/useCanaliIncasso'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

// ⚠️ Niente `class="w-full"` sui campi: `.form-field` e' gia' `flex-direction:
//    column`, quindi i figli si stirano da se'. Quella classe e' usata in una
//    ventina di componenti del progetto ma **non e' definita in nessun CSS** —
//    non fa niente, e sembra che faccia qualcosa.

const props = defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'aperta'])

const { t } = useI18n()
const notify = useNotify()
const { execute, loading, campiErrati } = useApiHandler()
// L'emittente su cui la SESSIONE scrive: `null` per chi lavora in «tutti gli
// emittenti». E' la stessa risposta che il database da' al livello 3
// (`fn_resolve_emittente_for_user` legge l'emittente attivo della topbar).
const { defaultEmittenteId } = useEmittenteFiscaleField()

// ⚠️ «Caricati e vuoti» e «non caricati» NON sono la stessa cosa, e a video si
//    somigliano: senza distinguerli, una fetch fallita direbbe «nessun canale
//    configurato» — un'affermazione, e falsa. I tre stati li tiene il BB.
const {
  canali,
  caricati: canaliCaricati,
  errore: erroreCanali,
  carica: caricaCanali,
  loading: caricamentoCanali,
} = useCanaliIncasso()

const form = ref(defaultForm())

// Scopo: la forma iniziale del foglio. La data nasce OGGI perche' e' il caso
//        normale — si registra il denaro della giornata — e resta modificabile.
function defaultForm() {
  return {
    ente_incasso_id: null,
    centro_riscossione_id: null,
    // ⚠️ Non e' una scelta di riga: e' l'emittente della sessione, pre-popolato
    //    come in ogni drawer documento (`ContrattoDrawer`, `OrdiniDrawer`…).
    emittente_fiscale_id: defaultEmittenteId.value ?? null,
    data_contabile: oggiAziendale(),
    importo_dichiarato: null,
    note: '',
  }
}

// ⭐ Col canale scelto il centro NON si tocca: lo porta l'ente. Il campo resta
//    VISIBILE (chi apre deve vedere su quale centro sta lavorando) ma disabilitato.
const centroDerivato = computed(() => form.value.ente_incasso_id != null)

// ⭐ L'emittente si mostra SOLO SENZA CANALE: col canale e' il suo per
//    costruzione, e a video lo dice una riga sotto il canale — non un campo
//    che chiederebbe di confermare una cosa gia' decisa.
const emittenteVisibile = computed(() => form.value.ente_incasso_id == null)
// Senza canale serve un emittente in sessione, o il database rifiuta al
// livello 4: e' il caso in cui il pulsante va SPENTO e non premuto per sentire
// un no — l'avviso che spiega e' quello del BB sotto il campo.
const canSave = computed(
  () =>
    form.value.centro_riscossione_id != null &&
    form.value.data_contabile != null &&
    (!emittenteVisibile.value || form.value.emittente_fiscale_id != null),
)

// Scopo: scelto un canale, deriva il suo centro.
// Note: ⚠️ Se il canale viene tolto il centro NON si azzera: e' rimasto l'ultimo
//       derivato, ed e' un valore valido — azzerarlo costringerebbe a
//       riselezionarlo per un gesto che non lo riguarda.
watch(() => form.value.ente_incasso_id, (id) => {
  if (id == null) return
  const canale = canali.value.find((c) => c.id === id)
  if (canale?.centro_riscossione_id != null) {
    form.value.centro_riscossione_id = canale.centro_riscossione_id
  }
})

// Scopo: carica i canali all'apertura e riazzera il form.
// Note: ⚠️ Si ricarica a ogni apertura: un canale configurato un minuto fa deve
//       comparire senza ricaricare la pagina.
watch(() => props.visible, async (aperto) => {
  if (!aperto) return
  form.value = defaultForm()
  await caricaCanali()
  fotografia.fissa()
})

async function onSave() {
  const payload = {
    centro_riscossione_id: form.value.centro_riscossione_id,
    data_contabile: toDateString(form.value.data_contabile),
  }
  if (form.value.ente_incasso_id != null) payload.ente_incasso_id = form.value.ente_incasso_id
  // ⛔ L'emittente viaggia SOLO se il campo e' a video (senza canale). Col
  //    canale non si manda: lo deriva il database dal conto, e mandarlo
  //    aprirebbe la porta a `E_CONTABILE_CANALE_DI_ALTRO_EMITTENTE` per un
  //    dissenso che nessuno ha scelto.
  if (emittenteVisibile.value && form.value.emittente_fiscale_id != null) {
    payload.emittente_fiscale_id = form.value.emittente_fiscale_id
  }
  // ⚠️ `0` e' un dichiarato legittimo («il foglio dice zero»): si esclude solo
  //    il campo NON compilato, non lo zero.
  if (form.value.importo_dichiarato != null) {
    payload.importo_dichiarato = form.value.importo_dichiarato
  }
  if (form.value.note?.trim()) payload.meta = { note: form.value.note.trim() }

  // ⚠️ NIENTE `silent` sulla creazione: i guard del database (coppia
  //    canale/centro incoerente, data fuori periodo) parlano, e in `silent` la
  //    finestra resterebbe aperta senza dire perche'.
  //    ⛔ E niente `successMessage`: il messaggio giusto dipende da `gia_popolata`
  //    — «aperta» e «ne hai ritrovata una con dentro del lavoro» non sono la
  //    stessa notizia.
  const dettaglio = await execute(() => creaDistinta(payload))
  // ⛔ `!== null`: un `0` legittimo non deve leggersi come fallimento.
  if (dettaglio === null) return

  // ⭐ L'ANNUNCIO CHE Q-3 PRETENDE. La funzione e' un *get or create*: con gli
  //    stessi dati il database non crea una seconda distinta, RIDA' LA SUA. Ed
  //    e' il comportamento giusto — ma entrare in silenzio dentro il lavoro di
  //    stamattina e' il modo in cui qualcuno registra due volte credendo di
  //    cominciare.
  // ⚠️ Il caso indistinguibile — distinta esistente e VUOTA — e' innocuo, ed e'
  //    per questo che l'annuncio si lega alle righe e non a «creata o no»: dalla
  //    chiamata quella differenza non si vede.
  if (dettaglio.gia_popolata) {
    notify.warn(
      t('pagamenti.distinte.gia_popolata', {
        righe: dettaglio.distinta?.righe_totali ?? 0,
      }),
    )
  } else {
    notify.success(t('pagamenti.distinte.aperta'))
  }
  emit('aperta', dettaglio.distinta?.id ?? null)
  emit('update:visible', false)
}

function onCancel() { emit('update:visible', false) }

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).
const fotografia = useFotografiaDialog(() => ({ ...form.value }), { visibile: () => props.visible, fissaAllApertura: false })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    :header="t('pagamenti.distinte.apri_titolo')"
    width="md"
    :loading="loading || caricamentoCanali"
    :save-disabled="!canSave"
    :save-label="t('pagamenti.distinte.apri_conferma')"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onSave"
    @cancel="onCancel"
  >
    <div class="form-grid">
      <!-- ⚠️ Un elenco vuoto si DICHIARA: un menu senza voci e senza
           spiegazione sembra un guasto dell'applicazione, non una condizione
           prevista. -->
      <Message
        v-if="canaliCaricati && !erroreCanali && !canali.length"
        severity="info"
        :closable="false"
        size="small"
      >
        {{ t('pagamenti.distinte.nessun_canale') }}
      </Message>

      <div class="form-field">
        <label>{{ t('pagamenti.distinte.campo_canale') }}</label>
        <Select
          v-model="form.ente_incasso_id"
          :options="canali"
          option-label="descrizione"
          option-value="id"
          :placeholder="t('pagamenti.distinte.campo_canale_placeholder')"
          :disabled="!canali.length"
          :invalid="campiErrati.includes('ente_incasso_id')"
          show-clear
        />
        <!-- ⭐ Col canale l'emittente e' deciso: si DICE, non si chiede. -->
        <small v-if="!emittenteVisibile" class="app-text-muted">
          {{ t('pagamenti.distinte.emittente_dal_canale') }}
        </small>
      </div>

      <!-- ⭐ Senza canale la distinta e' dell'emittente della SESSIONE: in sola
           lettura, come in ogni documento. Chi lavora in «tutti gli emittenti»
           vede l'avviso del BB e il pulsante resta spento. -->
      <div v-if="emittenteVisibile" class="form-field">
        <label>{{ t('pagamenti.distinte.campo_emittente') }} *</label>
        <EmittenteFiscaleField
          v-model="form.emittente_fiscale_id"
          :is-edit="false"
          :invalid="campiErrati.includes('emittente_fiscale_id')"
        />
        <small class="app-text-muted">
          {{ t('pagamenti.distinte.emittente_aiuto') }}
        </small>
      </div>

      <div class="form-field">
        <label>{{ t('pagamenti.distinte.campo_centro') }}</label>
        <LookupSelect
          v-model="form.centro_riscossione_id"
          rel="pagamenti.centri_riscossione"
          :placeholder="t('pagamenti.distinte.campo_centro_placeholder')"
          :disabled="centroDerivato"
          :invalid="campiErrati.includes('centro_riscossione_id')"
          show-clear
        />
        <!-- ⭐ Si dice PERCHE' e' bloccato: un campo disabilitato senza motivo
             si legge come un difetto. -->
        <small v-if="centroDerivato" class="app-text-muted">
          {{ t('pagamenti.distinte.centro_dal_canale') }}
        </small>
      </div>

      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('pagamenti.distinte.col_data_contabile') }}</label>
          <DatePicker
            v-model="form.data_contabile"
            :date-format="DATE_FORMAT"
            show-icon
            :invalid="campiErrati.includes('data_contabile')"
          />
        </div>
        <div class="form-field">
          <label>{{ t('pagamenti.distinte.col_importo_dichiarato') }}</label>
          <InputNumber
            v-model="form.importo_dichiarato"
            mode="currency"
            currency="EUR"
            locale="it-IT"
            :invalid="campiErrati.includes('importo_dichiarato')"
          />
          <!-- ⭐ E' la QUADRATURA: quanto dice il totale in cima al foglio
               arrivato. Facoltativo — ma senza, il controllo non scatta mai. -->
          <small class="app-text-muted">
            {{ t('pagamenti.distinte.dichiarato_aiuto') }}
          </small>
        </div>
      </div>

      <div class="form-field">
        <label>{{ t('pagamenti.distinte.campo_note') }}</label>
        <Textarea v-model="form.note" rows="2" auto-resize />
      </div>
    </div>
  </AppDialog>
</template>

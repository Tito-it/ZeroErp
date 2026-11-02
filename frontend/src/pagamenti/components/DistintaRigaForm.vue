<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: il form di UNA riga contabile — l'atto con cui si digita il denaro
//        arrivato: DI CHI e', quanto, quando, e con quale riferimento il canale
//        lo nomina.
//
// ⭐ IN CREAZIONE SI PARTE DAL DOCUMENTO (D16, 2026-09-14): chi digita un
//    incasso da una contabile bancaria SA chi ha pagato. Si cerca la fattura,
//    si sceglie la rata (facoltativa), l'importo si PROPONE dal residuo e si
//    corregge solo se cio' che e' arrivato e' diverso. La riga nasce ABBINATA
//    in un gesto solo. «Non riesco ad associarlo» e' un gesto ESPLICITO che
//    scopre i soli fatti: la riga nasce DA_ABBINARE e comparira' nella coda.
//    ⛔ L'eccezione si dichiara, non e' il default di un form — fino al 14/09
//    lo era, e faceva passare chi ha il nome sotto gli occhi per il flusso
//    dell'importo arrivato senza nome.
//
// ⚠️ IN MODIFICA si digitano i soli FATTI (R-6): ri-abbinare resta il verbo
//    `abbina`, che e' un gesto proprio. Mescolarli farebbe cambiare stato a
//    una riga mentre si corregge un importo. Una riga che NASCE non ha uno
//    stato da proteggere; una che c'e' gia' si'.
//
// ⭐ MA LA DESTINAZIONE SI VEDE SEMPRE (D19-b, Tid 2026-09-15): R-6 protegge
//    la SCRITTURA di fattura e rata, non la loro lettura. Chi corregge un
//    importo deve sapere su che cosa lo corregge — il documento com'e' scritto
//    (numero parlante, registro, data, totale, natura), il cliente, la rata
//    con scadenza e importo, e il residuo dalla base unica dei saldi. Fino al
//    17/09 in modifica il form nascondeva tutto (`v-if="!isEdit"`): si
//    cambiava un importo al buio. In creazione lo stesso blocco compare
//    appena scelta la fattura, e si aggiorna alla scelta della rata.
//
// ⭐ LA DOMANDA VERA E' «QUALE RATA?» (D19-c, 2026-09-17): accanto al lookup
//    della fattura c'e' il PICKER delle rate (`RatePickerDialog`) — cliente o
//    numero fattura → elenco rate col saldo — che in modalita' singola COMPILA
//    il form: fattura e rata nella stessa forma in cui arrivano dal lookup e
//    dalla tendina, cosi' la proposta dell'importo non cambia. ⚠️ Il lookup
//    resta: chi ha il numero sotto gli occhi lo digita. Il picker sta
//    ACCANTO, non al posto.
//
// ⭐ L'IMPORTO SI PROPONE DALLO SPAZIO, non dal residuo (Q-B, Tid 2026-09-17):
//    `residuo − in_lavorazione`, cioe' cio' che ci sta ANCORA prima di se' — e'
//    il numero che il guard di capienza confronta. Proporre il residuo su una
//    rata gia' tutta dichiarata in un'altra bozza invitava a scrivere un
//    importo che il database avrebbe rifiutato al Salva. La formula e'
//    `spazioSaldo`, nella base dei saldi: una sede, non tre.
//
// 🔴 IL DOPPIO TEMPO DELLA CAPIENZA vale in ENTRAMBI i modi, ed e' lo stesso
//    BB del dialogo di abbinamento (`useForzaturaConfermata`): primo tentativo
//    SENZA forzatura; sul rifiuto confermabile il messaggio del database coi
//    numeri, il motivo, e «Forza». Il frontend resta cieco ai codici.
//    ⭐ Anche in modifica (decisione di Tid, 2026-09-15 — Q-H del brief
//    D16/D17): correggere un importo incontra il guard della rata come
//    inserirlo, e il PATCH accetta `forzata` + `motivo_forzatura` come
//    secondo tempo. ⚠️ Fino a quel giorno non li accettava, e la prima stesura
//    di questo form offriva lo stesso un «Forza» che ripeteva il PATCH nudo:
//    un pulsante che il database rifiutava. Il verbo ha imparato a raccogliere
//    la conferma; il form la porta con `extra`, come alla nascita.
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import DatePicker from 'primevue/datepicker'
import InputNumber from 'primevue/inputnumber'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import ToggleSwitch from 'primevue/toggleswitch'

import DrawerContextHeader from '../../core/components/DrawerContextHeader.vue'
import FatturaLookup from '../../vendite/components/FatturaLookup.vue'
import NaturaDocTag from '../../core/components/NaturaDocTag.vue'
import SaldoPanel from './SaldoPanel.vue'
import { useForzaturaConfermata } from '../../core/composables/useForzaturaConfermata'
import { useDrawerFormPreserve } from '../../core/composables/useDrawerFormPreserve'
import { LIVELLO, spazioSaldo, useSaldi } from '../composables/useSaldi'
import { DATE_FORMAT, MANAGE_ICONS } from '../../core/constants'
import { displayDate, toDateString, parseIsoDate, oggiAziendale } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { aggiornaRiga, creaRiga, forzaturaConMotivo } from '../api/pagamenti'
import { useEtichettePagamenti } from '../etichette'
import RataSelect from './RataSelect.vue'
import RatePickerDialog from './RatePickerDialog.vue'

const props = defineProps({
  contabileId: { type: [Number, null], default: null },
  // La riga in modifica; `null` = nuova.
  riga: { type: [Object, null], default: null },
})
const emit = defineEmits(['salvata', 'annulla'])

const { t } = useI18n()
// L'etichetta della rata ha una sede sola (`etichette.js`): qui, nella tendina
// delle rate e nella tabella delle righe si legge la stessa forma.
const { rata: etichettaRata } = useEtichettePagamenti()
const isEdit = computed(() => props.riga?.id != null)

// ⭐ Un handler solo, quello del BB, per entrambi i modi: e' lui che riceve il
//    400 coi campi e il 409 confermabile, e da lui si leggono sia `campiErrati`
//    sia la domanda. Un secondo handler per la modifica non vedrebbe mai i
//    campi del 400 — e la modifica, dal 15/09, ha il suo secondo tempo.
const { esegui, conferma, annulla, richiestaConferma, loading, campiErrati } =
  useForzaturaConfermata()
// Il residuo del DOCUMENTO, per la proposta quando non si sceglie una rata:
// dalla base unica dei saldi, non da una lettura propria (§2.7).
const { saldo: saldoDocumento, leggi: leggiSaldoDocumento, azzera: azzeraSaldoDocumento } =
  useSaldi(LIVELLO.DOCUMENTO)

const form = ref(defaultForm())

// ── la destinazione (solo in creazione) ───────────────────────────
const fattura = ref(null)
const scadenzaId = ref(null)
const rataScelta = ref(null)
// ⭐ Il gesto esplicito: «non riesco ad associarlo».
const nonIdentificata = ref(false)
// Il picker delle rate (D19-c), aperto dal pulsante accanto al lookup.
const pickerVisible = ref(false)
const motivoForzatura = ref('')
// L'importo che questo form ha PROPOSTO per ultimo: si sovrascrive solo cio'
// che si e' proposto, mai cio' che l'operatore ha digitato.
let importoProposto = null

function defaultForm() {
  return {
    importo: null,
    riferimento_ente: '',
    // ⭐ La data del pagamento nasce OGGI: si sta digitando il denaro di
    //    giornata. ⚠️ Ma NON e' la data contabile della distinta — un incasso
    //    puo' essere di ieri e finire sul foglio di oggi.
    data_pagamento: oggiAziendale(),
    data_valuta: null,
  }
}

function resetDestinazione() {
  fattura.value = null
  scadenzaId.value = null
  rataScelta.value = null
  nonIdentificata.value = false
  motivoForzatura.value = ''
  importoProposto = null
  azzeraSaldoDocumento()
  annulla()
}

watch(
  () => props.riga,
  (r) => {
    form.value = r
      ? {
          importo: r.importo != null ? Number(r.importo) : null,
          riferimento_ente: r.riferimento_ente || '',
          data_pagamento: parseIsoDate(r.data_pagamento),
          data_valuta: parseIsoDate(r.data_valuta),
        }
      : defaultForm()
    resetDestinazione()
    // Dopo il giro di watch: anche la creazione conta. ⚠️ Dentro una freccia:
    //    il watch e' `immediate` e gira PRIMA che `fissa` sia dichiarata piu'
    //    sotto — `nextTick(fissa)` la leggerebbe adesso (TDZ).
    nextTick(() => fissa())
  },
  { immediate: true },
)

// Modifiche non salvate (2026-10-03, D-1 di
// work-done/analisi-fe-chrome-drawer.md): fino a quel giorno la X del
// drawer, l'ESC, il clic fuori e l'Annulla buttavano la riga in compilazione
// senza domanda. La fotografia e' il form PIU' la destinazione scelta, che
// vive fuori dal form; della destinazione si guardano gli ID: `RataSelect`
// riemette la rata come oggetto nuovo coi numeri uguali, e non e' una
// modifica. Il drawer la legge da `defineExpose` (`unisciFotografie`).
// ⚠️ `visibile` sempre vero: il form esiste solo mentre e' aperto (`v-if` nel
//    drawer), e allo smontaggio la fotografia se ne va con lui.
const { fissa, modificato, chiudiConConferma } = useDrawerFormPreserve(
  computed(() => ({
    ...form.value,
    fattura_id: fattura.value?.id ?? null,
    scadenza_id: rataScelta.value?.scadenza_id ?? null,
    non_identificata: nonIdentificata.value,
    motivo_forzatura: motivoForzatura.value,
  })),
  { visibile: () => true },
)
const annullaForm = () => chiudiConConferma(() => emit('annulla'))

// Scopo: propone un importo, ma solo sopra un campo vuoto o sopra la
//        proposta precedente — mai sopra un valore digitato.
// ⚠️ Uno spazio a zero non si propone: non c'e' niente da scrivere, e
//    proporre 0 inviterebbe a registrare il numero sbagliato. ⭐ Uno spazio
//    NEGATIVO invece SI' (dal 2026-09-17, P-5): sulla nota di credito e' il
//    rimborso, e il segno lo porta il numero — un `> 0` lo avrebbe negato.
function proponiImporto(spazio) {
  const valore = spazio != null ? Number(spazio) : null
  const sovrascrivibile = form.value.importo == null || form.value.importo === importoProposto
  if (!sovrascrivibile) return
  if (valore == null || valore === 0) {
    if (form.value.importo === importoProposto) form.value.importo = null
    importoProposto = null
    return
  }
  form.value.importo = valore
  importoProposto = valore
}

// Scelta la fattura: si legge il saldo del documento (la proposta senza rata).
// ⭐ Una rata resta scelta SOLO se e' del documento scelto (Q-2): il picker
//    consegna fattura e rata insieme, e azzerare la rata a ogni cambio di
//    fattura la farebbe sparire un istante dopo. Entrambe le sorgenti della
//    rata (`RataSelect`, il picker) portano `fattura_id`.
watch(fattura, async (f) => {
  if (rataScelta.value && rataScelta.value.fattura_id !== f?.id) rataScelta.value = null
  if (!f?.id) {
    azzeraSaldoDocumento()
    proponiImporto(null)
    return
  }
  await leggiSaldoDocumento(f.id)
})
// ⭐ La rata scelta vince sul documento; tolta la rata, si torna al documento.
//    In entrambi i casi la proposta e' lo SPAZIO (Q-B), dalla base unica.
watch([rataScelta, saldoDocumento], ([rata, doc]) => {
  if (isEdit.value || nonIdentificata.value) return
  proponiImporto(spazioSaldo(rata ?? doc))
})

// Scopo: il cliente della fattura gia' scelta, nella forma che
//        `BillingAccountLookup` mostra (`ragione_sociale_completa`, `codice`,
//        `id_fiscale`): il picker parte da li', e si puo' cambiare. `null`
//        senza fattura o senza billing account.
const clienteDellaFattura = computed(() => {
  const f = fattura.value
  if (f?.billing_account_id == null) return null
  return {
    id: f.billing_account_id,
    ragione_sociale_completa: f.ragione_sociale_completa ?? null,
    codice: f.ba_codice ?? null,
    id_fiscale: f.id_fiscale_univoco_cf_piva ?? null,
  }
})

// Scopo: la scelta dal picker (D19-c, modalita' singola): la riga porta tutte
//        le colonne della lista rate, e da li' si ricavano la fattura — nella
//        forma di `FatturaLookup` — e la rata nella forma di `RataSelect`.
// ⚠️ `scadenzaId` PRIMA che `RataSelect` ricarichi: il suo watch sulla fattura
//    tiene la scelta se e' fra le rate del documento (Q-2) e ri-emette la rata
//    coi numeri della tendina — che sostituiscono questi, uguali.
function onSceltaRata(riga) {
  fattura.value = {
    id: riga.fattura_id,
    billing_account_id: riga.billing_account_id,
    ba_codice: riga.ba_codice,
    numero: riga.numero,
    numero_documento: riga.numero_documento,
    serie: riga.serie,
    anno: riga.anno,
    data: riga.data,
    totale_doc: riga.totale_doc,
    registro_codice: riga.registro_codice,
    natura_doc_codice_interno: riga.natura_doc_codice_interno,
    natura_doc_descrizione: riga.natura_doc_descrizione,
    ragione_sociale_completa: riga.ragione_sociale_completa,
    id_fiscale_univoco_cf_piva: riga.id_fiscale_univoco_cf_piva,
  }
  rataScelta.value = {
    scadenza_id: riga.scadenza_id,
    fattura_id: riga.fattura_id,
    numero_rata: riga.numero_rata,
    data_scadenza: riga.data_scadenza,
    importo: riga.importo,
    residuo: riga.residuo,
    in_lavorazione: riga.in_lavorazione,
    incassato: riga.incassato,
    has_movimenti: riga.has_movimenti,
  }
  scadenzaId.value = riga.scadenza_id
}
// Il gesto esplicito azzera la destinazione: una riga «non identificata» non
// porta con se' una fattura scelta a meta'.
watch(nonIdentificata, (v) => {
  if (!v) return
  fattura.value = null
  scadenzaId.value = null
  rataScelta.value = null
  annulla()
})

// ── la destinazione LEGGIBILE (D19-b) ─────────────────────────────
// Scopo: il documento e la rata su cui si sta scrivendo, in UNA forma per i
//        due modi: in modifica dalla RIGA (le colonne `fattura_*`/`scadenza_*`
//        che il backend porta dal 17/09), in creazione dalla fattura scelta e
//        dalla rata scelta. `null` = nessuna destinazione (riga «non
//        identificata», o fattura non ancora scelta).
// ⚠️ Il numero parlante si LEGGE (`numero_documento`, sede unica a DB), mai
//    composto qui. Il ripiego al contatore (`numero`) vale per la fattura
//    scelta dal lookup finche' la vista non lo porta (brief DB, P-1): e' lo
//    stesso numero che il lookup mostra oggi, non una terza forma.
const destinazione = computed(() => {
  if (isEdit.value) {
    const r = props.riga
    if (r?.fattura_id == null) return null
    return {
      fatturaId: r.fattura_id,
      numeroDocumento: r.fattura_numero_documento ?? null,
      naturaCodice: r.natura_doc_codice_interno ?? null,
      naturaDescrizione: r.natura_doc_descrizione ?? null,
      registro: r.fattura_registro_codice ?? null,
      data: r.fattura_data ?? null,
      totale: r.fattura_totale_doc ?? null,
      cliente: r.billing_account_descrizione ?? null,
      scadenzaId: r.scadenza_id ?? null,
      numeroRata: r.scadenza_numero_rata ?? null,
      dataScadenza: r.scadenza_data ?? null,
      importoRata: r.scadenza_importo ?? null,
    }
  }
  const f = fattura.value
  if (f?.id == null) return null
  const rata = rataScelta.value
  return {
    fatturaId: f.id,
    numeroDocumento: f.numero_documento ?? (f.numero != null ? String(f.numero) : null),
    naturaCodice: f.natura_doc_codice_interno ?? null,
    naturaDescrizione: f.natura_doc_descrizione ?? null,
    registro: f.registro_codice ?? null,
    data: f.data ?? null,
    totale: f.totale_doc ?? null,
    cliente: f.ragione_sociale_completa ?? null,
    scadenzaId: rata?.scadenza_id ?? null,
    numeroRata: rata?.numero_rata ?? null,
    dataScadenza: rata?.data_scadenza ?? null,
    importoRata: rata?.importo ?? null,
  }
})

// Le voci del blocco: cliente in testa (la riga primaria dell'header), poi
// registro · data · totale · rata. La rata assente si DICE («sul documento»):
// una riga senza rata e' il fondo fattura, non un dato perso.
const destinazioneItems = computed(() => {
  const d = destinazione.value
  if (!d) return []
  const rata = d.scadenzaId != null
    ? etichettaRata({ numero_rata: d.numeroRata, data_scadenza: d.dataScadenza, importo: d.importoRata })
    : null
  return [
    { label: t('pagamenti.righe.col_billing_account_descrizione'), value: d.cliente },
    { label: t('pagamenti.righe.col_registro'), value: d.registro },
    { label: t('pagamenti.righe.col_fattura_data'), value: d.data ? displayDate(d.data) : null },
    {
      label: t('pagamenti.righe.col_fattura_totale'),
      value: d.totale != null ? formatCurrency(d.totale) : null,
    },
    { label: t('pagamenti.rata.campo'), value: rata, fallback: t('pagamenti.rata.sul_documento') },
  ]
})

// Il saldo del blocco: la RATA se c'e', altrimenti il DOCUMENTO. ⚠️ Il pannello
// legge il livello UNA volta: la `:key` lo rimonta quando cambia (e quando
// cambia il riferimento, cosi' non resta un istante il saldo di un'altra cosa).
const saldoLivello = computed(
  () => (destinazione.value?.scadenzaId != null ? LIVELLO.RATA : LIVELLO.DOCUMENTO),
)
const saldoRiferimentoId = computed(() => {
  const d = destinazione.value
  if (!d) return null
  return d.scadenzaId ?? d.fatturaId
})
const saldoKey = computed(() => `${saldoLivello.value}:${saldoRiferimentoId.value}`)
// ⭐ In modifica il saldo si chiede PRIMA DI SE': senza, «in lavorazione»
//    conterebbe proprio i soldi che si stanno correggendo. Sui due livelli
//    (dal 2026-09-18 anche il documento, P-6: la riga senza rata del fondo
//    fattura legge lo stesso «prima di se'» della rata). ⛔ Non si sana
//    sottraendo nel FE: sarebbe la seconda formula del saldo.
const saldoEscludiRigaId = computed(() => (isEdit.value ? props.riga?.id ?? null : null))

// ⚠️ `!= null` e non un test di verita': lo ZERO non e' un importo valido qui
//    (una riga da zero non e' denaro arrivato), ma va rifiutato dal DATABASE con
//    la sua frase — non nascosto disabilitando il pulsante, che lascerebbe
//    l'operatore senza sapere perche'.
// ⭐ In creazione serve ANCHE la destinazione, o la dichiarazione esplicita di
//    non averla: un form che salva senza ne' l'una ne' l'altra produrrebbe
//    l'eccezione per distrazione.
const canSave = computed(() => {
  if (form.value.importo == null) return false
  if (isEdit.value) return true
  return nonIdentificata.value || fattura.value?.id != null
})

function payloadFatti() {
  const payload = {
    importo: form.value.importo,
    data_pagamento: toDateString(form.value.data_pagamento),
  }
  // ⚠️ Stringa vuota -> NULL, mai `''`: il backend normalizza a NULL e una
  //    stringa vuota a database sarebbe un valore diverso da «non c'e'».
  payload.riferimento_ente = form.value.riferimento_ente?.trim() || null
  payload.data_valuta = form.value.data_valuta ? toDateString(form.value.data_valuta) : null
  return payload
}

// Scopo: primo tentativo — SENZA forzatura, sempre, in entrambi i modi.
// ⚠️ In modifica viaggiano i soli FATTI (R-6) piu', al secondo tempo, la
//    forzatura col suo motivo (`extra`): la destinazione resta di `abbina`.
async function onSalva() {
  const fatti = payloadFatti()
  if (isEdit.value) {
    const esito = await esegui(
      (extra) => aggiornaRiga(props.riga.id, { ...fatti, ...extra }),
      { successMessage: t('pagamenti.righe.aggiornata') },
    )
    if (esito !== null) emit('salvata')
    return
  }
  // ⭐ La destinazione viaggia coi fatti: un INSERT solo, e la riga nasce
  //    ABBINATA. `billing_account_id` dal lookup quando c'e' (il backend lo
  //    legge dalla fattura se manca).
  const destinazione = !nonIdentificata.value && fattura.value?.id != null
    ? {
        fattura_id: fattura.value.id,
        ...(fattura.value.billing_account_id != null
          ? { billing_account_id: fattura.value.billing_account_id }
          : {}),
        ...(scadenzaId.value != null ? { scadenza_id: scadenzaId.value } : {}),
      }
    : {}
  const esito = await esegui(
    (extra) => creaRiga(props.contabileId, { ...fatti, ...destinazione, ...extra }),
    { successMessage: t('pagamenti.righe.creata') },
  )
  if (esito !== null) emit('salvata')
}

// Scopo: secondo tentativo — con la forzatura e il suo motivo.
async function onConferma() {
  const esito = await conferma(forzaturaConMotivo(motivoForzatura.value.trim() || null))
  if (esito !== null) emit('salvata')
}
defineExpose({ modificato, chiudiConConferma })
</script>

<template>
  <div class="app-drawer-section">
    <h4>{{ t(isEdit ? 'pagamenti.righe.titolo_modifica' : 'pagamenti.righe.titolo_nuova') }}</h4>
  </div>

  <div class="form-grid">
    <!-- ══ Di chi e' (solo in creazione) ══ -->
    <template v-if="!isEdit">
      <div class="form-grid-2col">
        <div class="form-field">
          <label>{{ t('pagamenti.abbina.campo_fattura') }}</label>
          <!-- ⭐ BB `FatturaLookup` (core): cerca per numero, ragione sociale,
               codice BA, CF/P.IVA. La risposta a «quanto?» la da' il
               documento, non la memoria dell'operatore. ACCANTO, il picker
               delle rate (D19-c): la domanda vera e' «quale rata?». -->
          <div class="app-input-with-action">
            <FatturaLookup v-model="fattura" :disabled="nonIdentificata" />
            <!-- Icona letterale: «cerca» non e' un concetto di `MANAGE_ICONS`,
                 e i suoi fratelli (apri il resolver, esegui il test) sono
                 tutti scritti sul posto. -->
            <Button
              v-tooltip.top="t('pagamenti.rate.cerca')"
              :icon="MANAGE_ICONS.RICERCA"
              text
              rounded
              size="small"
              class="app-action-btn"
              :aria-label="t('pagamenti.rate.cerca')"
              :disabled="nonIdentificata"
              @click="pickerVisible = true"
            />
          </div>
        </div>
        <RataSelect
          v-model="scadenzaId"
          :fattura-id="fattura?.id ?? null"
          :natura-doc-codice="fattura?.natura_doc_codice_interno ?? null"
          :disabled="nonIdentificata"
          @select="(r) => { rataScelta = r }"
        />
      </div>
      <!-- ⭐ L'ECCEZIONE SI DICHIARA: un interruttore esplicito, non
           l'assenza di una scelta. Stessa forma di `DdtForm`/`OrdiniForm`. -->
      <div class="form-field">
        <label for="riga-non-identificata">{{ t('pagamenti.righe.non_identificata') }}</label>
        <div class="app-form-inline-toggle">
          <ToggleSwitch v-model="nonIdentificata" input-id="riga-non-identificata" />
          <small class="app-text-muted">
            {{ t('pagamenti.righe.non_identificata_aiuto') }}
          </small>
        </div>
      </div>
    </template>

    <!-- ══ Su che cosa si sta scrivendo (D19-b) ══
         Sempre, nei due modi: in creazione appena c'e' la fattura, in modifica
         dalla riga. In sola lettura per costruzione — la destinazione si cambia
         col verbo `abbina` (R-6), qui si guarda. -->
    <template v-if="destinazione">
      <DrawerContextHeader
        :tag-value="destinazione.numeroDocumento || t('fattura_lookup.senza_numero')"
        :items="destinazioneItems"
      >
        <!-- ⭐ La natura si SEGNALA, non si nasconde: una nota di credito su
             una riga di incasso e' il caso in cui il cliente ce la paga
             (D19-e) — e chi digita deve vederlo prima di confermare. Il BB
             tace da se' su una fattura ordinaria. -->
        <template #status>
          <NaturaDocTag
            :codice="destinazione.naturaCodice"
            :descrizione="destinazione.naturaDescrizione"
          />
        </template>
      </DrawerContextHeader>
      <!-- Il residuo dalla BASE UNICA (§2.7): rata se c'e', documento
           altrimenti. `:key` perche' il pannello legge il livello una volta. -->
      <SaldoPanel
        :key="saldoKey"
        :livello="saldoLivello"
        :riferimento-id="saldoRiferimentoId"
        :escludi-riga-id="saldoEscludiRigaId"
      />
    </template>
    <!-- In modifica, una riga SENZA destinazione lo dice: «non identificata»
         e' uno stato, non un blocco mancante. In creazione lo dice gia'
         l'interruttore. -->
    <Message v-else-if="isEdit" severity="secondary" :closable="false" size="small">
      <!-- Il nome del verbo viene dalla SUA chiave: se «Abbina a fattura»
           cambia nome, la frase lo segue. -->
      {{ t('pagamenti.righe.destinazione_assente', { azione: t('pagamenti.abbina.azione') }) }}
    </Message>

    <!-- ══ I fatti ══ -->
    <div class="form-grid-2col">
      <div class="form-field">
        <label>{{ t('pagamenti.righe.col_importo') }}</label>
        <!-- ⭐ Proposto dal residuo della rata (o del documento), e
             modificabile: si corregge solo se l'importo arrivato e' diverso. -->
        <InputNumber
          v-model="form.importo"
          mode="currency"
          currency="EUR"
          locale="it-IT"
          :invalid="campiErrati.includes('importo')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('pagamenti.righe.col_riferimento_ente') }}</label>
        <!-- ⭐ E' il riferimento con cui IL CANALE nomina il pagamento: e' cio'
             che permette di ritrovarlo quando il cliente telefona. -->
        <InputText
          v-model="form.riferimento_ente"
          :invalid="campiErrati.includes('riferimento_ente')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('pagamenti.righe.col_data_pagamento') }}</label>
        <DatePicker
          v-model="form.data_pagamento"
          :date-format="DATE_FORMAT"
          show-icon
          :invalid="campiErrati.includes('data_pagamento')"
        />
      </div>
      <div class="form-field">
        <label>{{ t('pagamenti.righe.col_data_valuta') }}</label>
        <DatePicker
          v-model="form.data_valuta"
          :date-format="DATE_FORMAT"
          show-icon
          show-button-bar
          :invalid="campiErrati.includes('data_valuta')"
        />
      </div>
    </div>

    <!-- ══ Il secondo tempo: la capienza non basta ══
         ⛔ NON e' un errore: e' una domanda. Il messaggio arriva dal DATABASE
            e porta gia' i numeri. Stessa forma del dialogo di abbinamento,
            dove vive nel footer: qui e' inline perche' il form e' inline. -->
    <template v-if="richiestaConferma">
      <Message severity="warn" :closable="false">
        {{ richiestaConferma.messaggio }}
      </Message>
      <div class="form-field">
        <label>{{ t('pagamenti.abbina.campo_motivo') }}</label>
        <Textarea v-model="motivoForzatura" rows="2" auto-resize />
        <small class="app-text-muted">{{ t('pagamenti.abbina.motivo_aiuto') }}</small>
      </div>
    </template>

    <!-- ⭐ Il picker delle rate (D19-c): si apre accanto al lookup, in
         modalita' singola compila il form. Montato nel form e non nel drawer:
         e' un attrezzo di QUESTO gesto. -->
    <RatePickerDialog
      v-if="!isEdit"
      v-model:visible="pickerVisible"
      :billing-account-iniziale="clienteDellaFattura"
      @scelta="onSceltaRata"
    />

    <div class="app-form-footer">
      <template v-if="richiestaConferma">
        <Tag severity="warn" :value="t('pagamenti.abbina.forzatura_resta_scritta')" />
        <Button
          text
          size="small"
          :label="t('common.cancel')"
          :icon="MANAGE_ICONS.BACK"
          @click="annulla"
        />
        <Button
          size="small"
          severity="warn"
          :label="t('pagamenti.abbina.forza')"
          :icon="MANAGE_ICONS.CONFIRM"
          :loading="loading"
          @click="onConferma"
        />
      </template>
      <template v-else>
        <Button
          text
          size="small"
          :label="t('common.cancel')"
          :icon="MANAGE_ICONS.BACK"
          @click="annullaForm"
        />
        <Button
          size="small"
          :label="t('common.save')"
          :icon="MANAGE_ICONS.CONFIRM"
          :loading="loading"
          :disabled="!canSave"
          @click="onSalva"
        />
      </template>
    </div>
  </div>
</template>

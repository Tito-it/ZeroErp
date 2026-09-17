<!--
  SPDX-License-Identifier: GPL-3.0-or-later
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
import { computed, ref, watch } from 'vue'
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
import FatturaLookup from '../../core/components/FatturaLookup.vue'
import NaturaDocTag from '../../core/components/NaturaDocTag.vue'
import SaldoPanel from '../../core/components/SaldoPanel.vue'
import { useForzaturaConfermata } from '../../core/composables/useForzaturaConfermata'
import { LIVELLO, useSaldi } from '../../core/composables/useSaldi'
import { DATE_FORMAT } from '../../core/constants'
import { displayDate, toDateString, parseIsoDate } from '../../core/utils/date'
import { formatCurrency } from '../../core/utils/format'
import { aggiornaRiga, creaRiga } from '../api/pagamenti'
import { useEtichettePagamenti } from '../etichette'
import RataSelect from './RataSelect.vue'

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
    data_pagamento: new Date(),
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
  },
  { immediate: true },
)

// Scopo: propone un importo, ma solo sopra un campo vuoto o sopra la
//        proposta precedente — mai sopra un valore digitato.
// ⚠️ Un residuo non positivo non si propone: «di troppo» o zero non sono un
//    importo arrivato, e proporli inviterebbe a registrare il numero sbagliato.
function proponiImporto(residuo) {
  const valore = residuo != null ? Number(residuo) : null
  const sovrascrivibile = form.value.importo == null || form.value.importo === importoProposto
  if (!sovrascrivibile) return
  if (valore == null || !(valore > 0)) {
    if (form.value.importo === importoProposto) form.value.importo = null
    importoProposto = null
    return
  }
  form.value.importo = valore
  importoProposto = valore
}

// Scelta la fattura: si legge il saldo del documento (la proposta senza rata).
watch(fattura, async (f) => {
  rataScelta.value = null
  if (!f?.id) {
    azzeraSaldoDocumento()
    proponiImporto(null)
    return
  }
  await leggiSaldoDocumento(f.id)
})
// ⭐ La rata scelta vince sul documento; tolta la rata, si torna al documento.
watch([rataScelta, saldoDocumento], ([rata, doc]) => {
  if (isEdit.value || nonIdentificata.value) return
  proponiImporto(rata ? rata.residuo : doc?.residuo)
})
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
      naturaCodice: r.fattura_natura_doc_codice_interno ?? null,
      naturaDescrizione: r.fattura_natura_doc_descrizione ?? null,
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
//    conterebbe proprio i soldi che si stanno correggendo. Sul documento il
//    pannello dichiara che non sa escluderla (la funzione DB non ha il
//    parametro): si legge sapendolo, non si sana sottraendo.
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
  const esito = await conferma(motivoForzatura.value.trim() || null)
  if (esito !== null) emit('salvata')
}
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
               documento, non la memoria dell'operatore. -->
          <FatturaLookup v-model="fattura" :disabled="nonIdentificata" />
        </div>
        <RataSelect
          v-model="scadenzaId"
          :fattura-id="fattura?.id ?? null"
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
          <small class="text-color-secondary">
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

    <div class="app-form-footer">
      <template v-if="richiestaConferma">
        <Tag severity="warn" :value="t('pagamenti.abbina.forzatura_resta_scritta')" />
        <Button
          text
          size="small"
          :label="t('common.cancel')"
          icon="pi pi-arrow-left"
          @click="annulla"
        />
        <Button
          size="small"
          severity="warn"
          :label="t('pagamenti.abbina.forza')"
          icon="pi pi-check"
          :loading="loading"
          @click="onConferma"
        />
      </template>
      <template v-else>
        <Button
          text
          size="small"
          :label="t('common.cancel')"
          icon="pi pi-arrow-left"
          @click="emit('annulla')"
        />
        <Button
          size="small"
          :label="t('common.save')"
          icon="pi pi-check"
          :loading="loading"
          :disabled="!canSave"
          @click="onSalva"
        />
      </template>
    </div>
  </div>
</template>

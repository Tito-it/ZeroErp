<!--
  SPDX-License-Identifier: GPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: IL VERBO CHE PORTA L'INCASSO ALLA RATA — si sceglie la fattura, poi
//        (facoltativa) la rata, e la riga passa ad ABBINATA.
//
// ⭐ Un solo gesto, non due: fattura, cliente e rata viaggiano in un solo
//    `UPDATE`, perche' sono lo stesso atto. La rata e' FACOLTATIVA: si puo'
//    abbinare al documento senza dire quale rata — il fondo fattura e' cosi'.
//
// 🔴 IL DOPPIO TEMPO DELLA CAPIENZA, e non e' un dettaglio di interfaccia:
//    il primo tentativo si manda SENZA forzatura. Se sulla rata non c'e' spazio
//    il database rifiuta con la ragione e i numeri; solo allora si chiede il
//    MOTIVO e si ripete con `forzata = true`, che resta **scritto sulla riga**
//    ed e' cio' che l'elenco delle rate fuori capienza legge per esistere.
//    ⛔ Forzare al primo colpo «per semplificare» nasconde invece di registrare.
//    ⚠️ Il riconoscimento passa dall'`ui_action` `confirm_and_retry`
//    (`useForzaturaConfermata`): il frontend resta CIECO ai codici.
//
// ⚠️ E la COERENZA non e' confermabile: «questa rata e' di questa fattura?» e'
//    un rifiuto secco (400) e resta tale — si conferma la capienza, mai il
//    legame sbagliato.
//
// ⭐ SI APRE SULLA DESTINAZIONE CHE LA RIGA HA GIA' (rilievo in-app di Tid,
//    2026-09-18). Su una riga gia' abbinata il dialog si apriva VUOTO: chi lo
//    apriva per vedere o cambiare l'abbinamento si trovava a cercare da capo
//    un documento che la riga aveva sotto, e «vuoto» si leggeva come «non e'
//    abbinata». Ora fattura e rata arrivano dalla riga — le stesse colonne
//    `fattura_*`/`scadenza_*` che il form di modifica gia' legge (D19-b) —
//    nella forma che `FatturaLookup` e `RataSelect` mostrano; ri-abbinare e'
//    cambiare documento o rata da li'. ⚠️ Con la destinazione INVARIATA il
//    verbo resta spento e lo dice: un «Abbina» che riscrive lo stesso legame
//    non e' un gesto, e' un pulsante che non fa niente.
//
// ⭐ DUE MODI, UN DIALOGO (FE-4, D20-b — 2026-09-19). In modo `registra` e' la
//    TARDIVA: una riga SOSPESA sotto una distinta gia' registrata si abbina E
//    si registra nello stesso gesto — movimento scritto, riga POSTATA, la
//    distinta resta CHIUSA. Cambiano il titolo, il verbo del pulsante (rosso:
//    non si torna indietro) e l'endpoint (`registraRigaTardiva`); restano la
//    stessa domanda «quale documento, quale rata» e lo stesso doppio tempo
//    della capienza. ⚠️ «Invariata» non spegne niente qui: registrare E'
//    sempre un gesto, anche sulla destinazione che la riga porta gia'.
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

import AppDialog from '../../core/components/AppDialog.vue'
import FatturaLookup from '../../vendite/components/FatturaLookup.vue'
import { useForzaturaConfermata } from '../../core/composables/useForzaturaConfermata'
import { displayDate } from '../../core/utils/date'
import { MANAGE_ICONS } from '../../core/constants'
import { abbinaRiga, forzaturaConMotivo, registraRigaTardiva } from '../api/pagamenti'
import { useChiaveGesto } from '../../core/composables/useChiaveGesto'
import { formatCurrency } from '../../core/utils/format'
import { MODO_ABBINA } from '../composables/useAzioniRigaContabile'
import RataSelect from './RataSelect.vue'
import { useFotografiaDialog } from '../../core/composables/useFotografiaDialog'

const props = defineProps({
  visible: { type: Boolean, default: false },
  riga: { type: [Object, null], default: null },
  // `MODO_ABBINA.ABBINA` (default) | `MODO_ABBINA.REGISTRA` (la tardiva).
  modo: { type: String, default: MODO_ABBINA.ABBINA },
})
const emit = defineEmits(['update:visible', 'abbinata'])

const { t } = useI18n()
const { esegui, conferma, annulla, richiestaConferma, loading } = useForzaturaConfermata()
// La key del gesto: vive finche' il dialog resta aperto (`reset` la azzera).
const gesto = useChiaveGesto()

const registra = computed(() => props.modo === MODO_ABBINA.REGISTRA)

const fattura = ref(null)
const scadenzaId = ref(null)
const motivoForzatura = ref('')
// ⭐ Le rate COL SALDO, i tre stati e la nota «facoltativa» stanno in
//    `RataSelect` (estratto il 14/09 alla seconda occorrenza: la nascita
//    della riga con la destinazione fa la stessa domanda). Qui resta il verbo.
const rataSelect = ref(null)
const caricamento = computed(() => rataSelect.value?.loading === true)

// Scopo: la destinazione che la riga porta GIA', nella forma di `FatturaLookup`
//        (l'oggetto fattura coi campi che il lookup mostra) e di `RataSelect`
//        (lo `scadenza_id`). `fattura` a `null` = la riga non e' abbinata.
// ⚠️ Le colonne sono quelle di `_RIGA_COLONNE` del repository (prefisso
//    `fattura_`/`scadenza_`, il cliente in `billing_account_descrizione`), le
//    stesse che la lista delle righe (`pagamenti.distinta_righe`) consegna.
function destinazioneDallaRiga(r) {
  if (r?.fattura_id == null) return { fattura: null, scadenzaId: null }
  return {
    fattura: {
      id: r.fattura_id,
      billing_account_id: r.billing_account_id ?? null,
      numero: r.fattura_numero ?? null,
      serie: r.fattura_serie ?? null,
      anno: r.fattura_anno ?? null,
      numero_documento: r.fattura_numero_documento ?? null,
      data: r.fattura_data ?? null,
      totale_doc: r.fattura_totale_doc ?? null,
      registro_codice: r.fattura_registro_codice ?? null,
      natura_doc_codice_interno: r.natura_doc_codice_interno ?? null,
      natura_doc_descrizione: r.natura_doc_descrizione ?? null,
      ragione_sociale_completa: r.billing_account_descrizione ?? null,
    },
    scadenzaId: r.scadenza_id ?? null,
  }
}

// ⭐ «Invariata» = stesso documento E stessa rata della riga: il verbo non ha
//    niente da scrivere. ⚠️ Si confronta con la RIGA, non con cio' che il
//    dialog ha proposto all'apertura: e' la riga il fatto.
const invariata = computed(() => {
  const r = props.riga
  if (r?.fattura_id == null || fattura.value?.id == null) return false
  return fattura.value.id === r.fattura_id
    && (scadenzaId.value ?? null) === (r.scadenza_id ?? null)
})

const canSave = computed(
  () => fattura.value?.id != null && (registra.value || !invariata.value),
)

// Scopo: all'apertura si riparte dalla riga — con la sua destinazione se ce
//        l'ha, vuoti altrimenti. ⚠️ `scadenzaId` e `fattura` insieme, nello
//        stesso giro: il watch di `RataSelect` sulla fattura tiene la rata
//        gia' scelta se e' fra quelle del documento appena caricato (Q-2), e
//        la trova solo se e' gia' nel `modelValue` quando la fattura cambia.
function reset() {
  const { fattura: f, scadenzaId: sc } = destinazioneDallaRiga(props.riga)
  fattura.value = f
  scadenzaId.value = sc
  motivoForzatura.value = ''
  annulla()
  gesto.azzera()
}
watch(() => props.visible, (v) => { if (v) reset() })

// Scopo: primo tentativo — SENZA forzatura, sempre.
async function onAbbina() {
  const base = {
    fattura_id: fattura.value.id,
    ...(fattura.value.billing_account_id != null
      ? { billing_account_id: fattura.value.billing_account_id }
      : {}),
    ...(scadenzaId.value != null ? { scadenza_id: scadenzaId.value } : {}),
  }
  // ⭐ Il verbo lo sceglie il MODO: stesso payload, due endpoint. La tardiva
  //    dice nel toast QUANTO ha registrato: «fatto» senza il numero non dice
  //    se il movimento e' di sessanta o di seicento.
  // ⭐ La key del GESTO (`useChiaveGesto`): la tardiva e' irreversibile, e un
  //    reinvio dopo un timeout deve ricevere l'esito del primo, non scrivere
  //    un secondo movimento. ⚠️ Il secondo tempo (`forzata` + motivo) e' un
  //    payload diverso, quindi una key nuova: il primo era stato rifiutato.
  const modo = registra.value ? 'registra' : 'abbina'
  const verbo = registra.value ? registraRigaTardiva : abbinaRiga
  const chiamata = (extra) => {
    const payload = { ...base, ...extra }
    return gesto.invia(
      { modo, rigaId: props.riga.id, ...payload },
      (config) => verbo(props.riga.id, payload, config),
    )
  }
  const esito = await esegui(chiamata, {
    successMessage: registra.value
      ? t('pagamenti.abbina.registrata', { importo: formatCurrency(props.riga.importo) })
      : t('pagamenti.abbina.fatto'),
  })
  if (esito !== null) chiudiConEsito()
}

// Scopo: secondo tentativo — con la forzatura e il suo motivo.
async function onConferma() {
  const esito = await conferma(forzaturaConMotivo(motivoForzatura.value.trim() || null))
  if (esito !== null) chiudiConEsito()
}

function chiudiConEsito() {
  emit('abbinata')
  emit('update:visible', false)
}

// D-14: la destinazione scelta e il motivo sono lavoro dell'operatore (della fattura si guarda l'id: il lookup la riemette come oggetto nuovo).
const fotografia = useFotografiaDialog(() => ({ fattura: fattura.value?.id ?? null, scadenzaId: scadenzaId.value, motivo: motivoForzatura.value }), { visibile: () => props.visible })
</script>

<template>
  <AppDialog
    :conferma-uscita="fotografia.chiudiConConferma"
    :visible="visible"
    :header="registra ? t('pagamenti.abbina.titolo_registra') : t('pagamenti.abbina.titolo')"
    width="md"
    :loading="loading || caricamento"
    :save-disabled="!canSave || richiestaConferma !== null"
    :save-label="registra ? t('pagamenti.abbina.conferma_registra') : t('pagamenti.abbina.conferma')"
    :save-severity="registra ? 'danger' : null"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onAbbina"
    @cancel="emit('update:visible', false)"
  >
    <div class="form-grid">
      <!-- ⛔ Nella tardiva si dice che non si torna indietro, e si dice PRIMA:
           e' la stessa frase della registrazione della distinta, perche' e'
           lo stesso fatto — un movimento che nasce. -->
      <Message v-if="registra" severity="warn" :closable="false">
        {{ t('pagamenti.abbina.registra_irreversibile') }}
      </Message>

      <!-- Che cosa si sta abbinando: senza, si sceglie una fattura al buio. -->
      <Message v-if="riga" severity="secondary" :closable="false" size="small">
        {{ t('pagamenti.abbina.contesto', {
          importo: formatCurrency(riga.importo),
          data: displayDate(riga.data_pagamento),
        }) }}
        <template v-if="riga.riferimento_ente"> · {{ riga.riferimento_ente }}</template>
      </Message>

      <div class="form-field">
        <label>{{ t('pagamenti.abbina.campo_fattura') }}</label>
        <!-- ⭐ BB `FatturaLookup` (core): la ricerca del documento non e' un
             fatto degli incassi — la stessa domanda la fa la sistemazione di
             un'eccedenza, ed e' li' che ha smesso di essere un'occorrenza sola
             (regola del 2, §5.3 del brief). -->
        <FatturaLookup v-model="fattura" />
      </div>

      <!-- Le rate col saldo, facoltative: il BB di dominio. `v-model` porta
           lo `scadenza_id`, ed e' tutto cio' che il verbo deve mandare. -->
      <RataSelect ref="rataSelect" v-model="scadenzaId" :fattura-id="fattura?.id ?? null" />

      <!-- Perche' «Abbina» e' spento: la riga e' gia' cosi'. Senza questa riga
           un pulsante grigio su un form compilato si legge come un guasto.
           ⚠️ Non nella tardiva: li' il verbo e' acceso anche sulla stessa
           destinazione, perche' registrare e' comunque un gesto. -->
      <Message v-if="invariata && !registra" severity="info" :closable="false" size="small">
        {{ t('pagamenti.abbina.gia_cosi') }}
      </Message>

      <!-- ══ Il secondo tempo: la capienza non basta ══
           ⛔ NON e' un errore: e' una domanda. Il messaggio arriva dal DATABASE
              e porta gia' i numeri — non si riscrive qui una frase che il
              catalogo compone meglio, ed e' multilingua. -->
      <template v-if="richiestaConferma">
        <Message severity="warn" :closable="false">
          {{ richiestaConferma.messaggio }}
        </Message>
        <div class="form-field">
          <label>{{ t('pagamenti.abbina.campo_motivo') }}</label>
          <Textarea v-model="motivoForzatura" rows="2" auto-resize />
          <!-- ⭐ Il motivo non e' un ornamento: e' quello che chi dovra'
               sistemare l'eccedenza leggera' nell'elenco delle rate fuori
               capienza, magari settimane dopo. -->
          <small class="app-text-muted">{{ t('pagamenti.abbina.motivo_aiuto') }}</small>
        </div>
      </template>
    </div>

    <!-- In attesa di conferma il footer standard non basta: le scelte sono
         «forza» o «rinuncia», e la prima e' un gesto che resta scritto. -->
    <template v-if="richiestaConferma" #footer>
      <div class="app-form-footer">
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
      </div>
    </template>
  </AppDialog>
</template>

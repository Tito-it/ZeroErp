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
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

import AppDialog from '../../core/components/AppDialog.vue'
import FatturaLookup from '../../core/components/FatturaLookup.vue'
import { useForzaturaConfermata } from '../../core/composables/useForzaturaConfermata'
import { RISULTATI, useLetturaTreStati } from '../../core/composables/useLetturaTreStati'
import { displayDate } from '../../core/utils/date'
import { abbinaRiga, listRateFattura } from '../api/pagamenti'
import { formatCurrency } from '../../core/utils/format'

const props = defineProps({
  visible: { type: Boolean, default: false },
  riga: { type: [Object, null], default: null },
})
const emit = defineEmits(['update:visible', 'abbinata'])

const { t } = useI18n()
const { esegui, conferma, annulla, richiestaConferma, loading } = useForzaturaConfermata()

const fattura = ref(null)
const scadenzaId = ref(null)
const motivoForzatura = ref('')
// ⚠️ «La fattura non ha rate» e «non sono riuscito a leggerle» si vedono uguali
//    — un Select vuoto — e portano a due conclusioni diverse. I tre stati li
//    tiene il BB.
const {
  dati: rate,
  caricati: rateCaricate,
  errore: erroreRate,
  loading: caricamento,
  carica: caricaRate,
  azzera: azzeraRate,
} = useLetturaTreStati((id) => listRateFattura(id), { estrai: RISULTATI, vuoto: [] })

const canSave = computed(() => fattura.value?.id != null)

// Scopo: scelta la fattura, si caricano le sue rate COL SALDO.
// Note: ⭐ Le rate arrivano gia' col saldo (`residuo · in_lavorazione ·
//       incassato`): un elenco di rate senza saldo non risponde alla domanda per
//       cui lo si apre — «dove ci sta questo incasso?».
watch(fattura, async (f) => {
  scadenzaId.value = null
  azzeraRate()
  if (!f?.id) return
  await caricaRate(f.id)
})

// ⚠️ Il residuo NEGATIVO su una rata significa «e' gia' entrato piu' del
//    dovuto»: si dice a parole, mai come «-120,00», che si legge come un guasto.
function etichettaRata(r) {
  const residuo = Number(r.residuo ?? 0)
  const stato = residuo < 0
    ? t('pagamenti.abbina.rata_di_troppo', { importo: formatCurrency(Math.abs(residuo)) })
    : t('pagamenti.abbina.rata_residuo', { importo: formatCurrency(residuo) })
  return `${t('pagamenti.abbina.rata_n', { n: r.numero_rata })} · ${displayDate(r.data_scadenza)} · ${stato}`
}

function reset() {
  fattura.value = null
  azzeraRate()
  scadenzaId.value = null
  motivoForzatura.value = ''
  annulla()
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
  const esito = await esegui(
    (extra) => abbinaRiga(props.riga.id, { ...base, ...extra }),
    { successMessage: t('pagamenti.abbina.fatto') },
  )
  if (esito !== null) chiudiConEsito()
}

// Scopo: secondo tentativo — con la forzatura e il suo motivo.
async function onConferma() {
  const esito = await conferma(motivoForzatura.value.trim() || null)
  if (esito !== null) chiudiConEsito()
}

function chiudiConEsito() {
  emit('abbinata')
  emit('update:visible', false)
}
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="t('pagamenti.abbina.titolo')"
    width="md"
    :loading="loading || caricamento"
    :save-disabled="!canSave || richiestaConferma !== null"
    :save-label="t('pagamenti.abbina.conferma')"
    @update:visible="(v) => emit('update:visible', v)"
    @save="onAbbina"
    @cancel="emit('update:visible', false)"
  >
    <div class="form-grid">
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

      <div class="form-field">
        <label>{{ t('pagamenti.abbina.campo_rata') }}</label>
        <Select
          v-model="scadenzaId"
          :options="rate"
          :option-label="etichettaRata"
          option-value="scadenza_id"
          :placeholder="t('pagamenti.abbina.campo_rata_placeholder')"
          :disabled="!fattura || !rate.length"
          show-clear
        />
        <!-- ⭐ La rata e' FACOLTATIVA, e va detto: senza, l'operatore crede di
             dover per forza sceglierne una e su un fondo fattura si blocca. -->
        <!-- ⛔ Tre casi, non due: rate presenti · nessuna rata · non lette.
             L'ultimo NON si spaccia per il secondo. -->
        <small v-if="erroreRate" class="app-text-muted">
          {{ t('pagamenti.abbina.rate_non_lette') }}
        </small>
        <small v-else-if="rateCaricate && !rate.length" class="app-text-muted">
          {{ t('pagamenti.abbina.nessuna_rata') }}
        </small>
        <small v-else class="app-text-muted">{{ t('pagamenti.abbina.rata_facoltativa') }}</small>
      </div>

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
      </div>
    </template>
  </AppDialog>
</template>

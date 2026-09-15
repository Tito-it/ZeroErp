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
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'

import AppDialog from '../../core/components/AppDialog.vue'
import FatturaLookup from '../../core/components/FatturaLookup.vue'
import { useForzaturaConfermata } from '../../core/composables/useForzaturaConfermata'
import { displayDate } from '../../core/utils/date'
import { abbinaRiga } from '../api/pagamenti'
import { formatCurrency } from '../../core/utils/format'
import RataSelect from './RataSelect.vue'

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
// ⭐ Le rate COL SALDO, i tre stati e la nota «facoltativa» stanno in
//    `RataSelect` (estratto il 14/09 alla seconda occorrenza: la nascita
//    della riga con la destinazione fa la stessa domanda). Qui resta il verbo.
const rataSelect = ref(null)
const caricamento = computed(() => rataSelect.value?.loading === true)

const canSave = computed(() => fattura.value?.id != null)

function reset() {
  fattura.value = null
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

      <!-- Le rate col saldo, facoltative: il BB di dominio. `v-model` porta
           lo `scadenza_id`, ed e' tutto cio' che il verbo deve mandare. -->
      <RataSelect ref="rataSelect" v-model="scadenzaId" :fattura-id="fattura?.id ?? null" />

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

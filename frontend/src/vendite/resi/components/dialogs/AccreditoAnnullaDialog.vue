<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: annullo dell'accredito di UNA riga di reso (B2-bis / D-NC-11) — il
// caso «ho cliccato la riga sbagliata». Toglie le rettifiche registrate e
// cancella le righe di ponte: l'accredito torna dovuto in coda e la merce resa
// torna accreditabile.
//
// ⭐ Componente unico per le DUE sedi da cui si raggiunge — la coda accrediti
// (quando il conto della merce ha riportato dentro la riga) e il drawer del
// reso (la sede principale, perché dopo il verbo la riga esce dalla coda). Due
// copie di questo dialog divergerebbero sul testo, ed è proprio il testo la
// parte che conta.
//
// ⚠️ DIALOG E NON SEMPLICE CONFERMA: il motivo è obbligatorio (backend + madre
// DB) ed è l'unica traccia del PERCHÉ — l'annullo cancella le righe di ponte,
// quindi lo storico dirà cosa è stato tolto, non perché. Stesso pattern
// dell'annullo riga manuale sulle commesse.
//
// ⚠️ LE DUE STRADE NON SONO LA STESSA COSA, e il testo lo dice: questo annulla
// l'ACCREDITO (a monte del documento); il reset del lotto annulla il DOCUMENTO
// e la nota di credito viene RIGENERATA al giro successivo, perché la merce
// resa non è cambiata. Confonderle manda l'operatore sulla strada sbagliata
// credendo di aver disfatto.
import { useI18n } from 'vue-i18n'
import Message from 'primevue/message'
import MotivoDialog from '../../../../core/components/MotivoDialog.vue'
import { useApiHandler } from '../../../../core/composables/useApiHandler'
import { useNotify } from '../../../../core/composables/useNotify'
import { annullaAccredito } from '../../api/resiApi'

const props = defineProps({
  visible: { type: Boolean, required: true },
  // La riga da disfare. ⚠️ Le due sedi la chiamano diversamente: la coda porta
  // `resi_riga_id` (grana riga della vista), il drawer `id` (PK della riga di
  // reso). Sono lo stesso numero: si normalizza qui invece di chiedere ai due
  // caller di adattarsi a una forma.
  riga: { type: Object, default: null },
  // ⚠️ Readonly PURO del chiamante (permessi area / split), MAI quello
  // combinato con lo stato del documento. Senza questo override la dialog
  // eredita il readonly dell'albero e `FormFooter` NASCONDE il pulsante di
  // conferma: resta solo «Annulla», e l'annullo dell'accredito diventa
  // impossibile — misurato in-app il 2026-08-19.
  // ⭐ E non e' un caso limite, e' il caso NORMALE: l'annullo vive su un reso
  // CONFERMATO, cioe' esattamente dove il drawer e' in protect. Stessa ragione
  // e stessa forma di `DdtResoDialog`.
  readonly: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'annullato'])

const { t } = useI18n()
const { execute, loading } = useApiHandler()
const notify = useNotify()

// Il motivo (obbligatorio), il suo azzeramento a ogni apertura e la fotografia
// sono di `MotivoDialog`: qui solo il gesto.
async function salva(motivo) {
  const rigaId = props.riga?.resi_riga_id ?? props.riga?.id
  const res = await execute(
    () => annullaAccredito(props.riga.reso_id, rigaId, motivo),
  )
  if (res === null) return
  emit('update:visible', false)
  notify.success(t('vendite.resi.annullo_esito'))
  emit('annullato')
}

// D-14: uscire con dati inseriti chiede (AppDialog `conferma-uscita`).</script>

<template>
  <MotivoDialog
    :visible="visible"
    :header="t('vendite.resi.annullo_header')"
    :label="t('vendite.resi.annullo_motivo')"
    obbligatorio
    :loading="loading"
    :readonly="readonly"
    :save-label="t('vendite.resi.annullo_salva')"
    save-severity="danger"
    @update:visible="emit('update:visible', $event)"
    @conferma="salva"
  >
    <p class="app-text-muted">
      {{ t('vendite.resi.annullo_conferma') }}
    </p>
    <Message severity="warn" :closable="false" size="small">
      {{ t('vendite.resi.annullo_avviso_reset') }}
    </Message>
  </MotivoDialog>
</template>

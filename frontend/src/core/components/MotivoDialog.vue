<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: CONFERMARE UN GESTO DANDONE IL MOTIVO — bloccare una credenziale,
//        disattivarne il secondo fattore, annullare un accredito o una
//        sistemazione, approvare o rifiutare un prezzo. Estratto il 2026-10-03
//        (regola del 2, ok Tid): la stessa forma — spiegazione, un campo
//        motivo, un pulsante d'azione — era scritta in cinque dialog, con lo
//        stato del motivo, il suo azzeramento all'apertura e la sua
//        fotografia ricopiati in ognuno, e gia' divergenti (la gravita' del
//        pulsante diversa per lo stesso gesto distruttivo, il motivo
//        obbligatorio scritto in due modi).
//
// ⭐ IL MOTIVO E' DEL BB: nasce vuoto a ogni apertura (mai residui del giro
//    precedente: il motivo di ieri su un gesto di oggi sarebbe una traccia
//    falsa, e la traccia e' tutto cio' che resta), si fotografa (uscire
//    dopo averlo scritto chiede, D-14) e arriva al chiamante con `conferma`,
//    gia' ripulito degli spazi — `null` se vuoto. Il chiamante tiene solo il
//    gesto: la chiamata, l'esito, la chiusura.
// ⚠️ La chiusura dopo il successo e' del chiamante (`v-model:visible` a
//    false): un rifiuto del backend deve lasciare il dialog aperto col motivo.
//
// Uso:
//   <MotivoDialog
//     v-model:visible="visibile"
//     :header="t('…')" :label="t('…')" obbligatorio
//     :save-label="t('…')" save-severity="danger"
//     :loading="loading" :invalid="campiErrati.includes('motivo')"
//     @conferma="(motivo) => blocca(motivo)"
//   >
//     <p>{{ t('…spiegazione') }}</p>
//   </MotivoDialog>
import { computed, ref, watch } from 'vue'
import Textarea from 'primevue/textarea'
import AppDialog from './AppDialog.vue'
import { useFotografiaDialog } from '../composables/useFotografiaDialog'

const props = defineProps({
  visible: { type: Boolean, required: true },
  header: { type: String, required: true },
  // L'etichetta del campo: il motivo ha un nome diverso per gesto
  // («Motivo del blocco», «Motivazione», «Nota»).
  label: { type: String, required: true },
  // Obbligatorio: senza motivo il pulsante d'azione resta spento.
  obbligatorio: { type: Boolean, default: false },
  // Una riga d'aiuto sotto il campo.
  aiuto: { type: String, default: null },
  // Il bordo d'errore quando il backend rifiuta il motivo (`campiErrati`).
  invalid: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  saveLabel: { type: String, default: null },
  saveSeverity: { type: String, default: null },
  width: { type: String, default: 'sm' },
  // Passato tale e quale ad AppDialog: `undefined` eredita la catena.
  readonly: { type: Boolean, default: undefined },
})

const emit = defineEmits(['update:visible', 'conferma'])

const motivo = ref('')
const pulito = computed(() => motivo.value.trim())

watch(() => props.visible, (aperto) => { if (aperto) motivo.value = '' }, { immediate: true })

const fotografia = useFotografiaDialog(() => ({ motivo: motivo.value }), { visibile: () => props.visible })

function conferma() {
  emit('conferma', pulito.value || null)
}
</script>

<template>
  <AppDialog
    :visible="visible"
    :header="header"
    :width="width"
    :loading="loading"
    :readonly="readonly"
    :save-label="saveLabel"
    :save-severity="saveSeverity"
    :save-disabled="obbligatorio && !pulito"
    :conferma-uscita="fotografia.chiudiConConferma"
    @update:visible="(v) => emit('update:visible', v)"
    @save="conferma"
  >
    <slot />
    <div class="form-field">
      <label>{{ label }}<template v-if="obbligatorio"> *</template></label>
      <Textarea v-model="motivo" rows="3" auto-resize fluid :invalid="invalid" />
      <small v-if="aiuto" class="app-text-muted">{{ aiuto }}</small>
    </div>
  </AppDialog>
</template>

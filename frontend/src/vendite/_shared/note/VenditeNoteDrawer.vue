<script setup>
// Building block: drawer note per i documenti vendite (contratti, preventivi,
// offerte, ordini, DDT, fatture). Assorbe il boilerplate di dominio —
// costruzione `apiClient` dal basePath, titolo, mappatura righe→opzioni del
// select RIGA, render del `NoteDrawer` generico. Le note usano la stessa
// tabella/API per tutti i domini (`makeNotesApi`).
// ⭐ Dal 2026-10-31 si monta DIRETTAMENTE dai drawer e dalle liste dei
//    documenti (regola del 2): i sei wrapper di dominio (`ContrattoNoteDrawer`,
//    `PreventivoNoteDrawer`, `OffertaNoteDrawer`, `OrdineNoteDrawer`,
//    `DdtNoteDrawer`, `FatturaNoteDrawer`) erano diventati identici — props
//    visible / id / emittente / righe, cambiavano il dominio, il titolo e i
//    campi della label riga — e sono stati ritirati. Quello che li
//    distingueva sta in `DOMINI_NOTE_VENDITE` (`dominiNote.js`), una riga per
//    documento.
//
// ⭐ PERCHE' `:id` + `:emittente-fiscale-id` E NON IL DOCUMENTO INTERO. Il
//    nome del campo dell'emittente non e' lo stesso nei sei documenti: la
//    fattura porta la PK in `emittente_fiscale_pk` (li' `emittente_fiscale_id`
//    e' il soggetto_ruolo), e le liste passano la riga della lista, non il
//    dettaglio. Chi monta il drawer sa che forma ha il SUO documento: e' lui
//    che sceglie il campo, a vista nel template. Un BB che lo indovinasse dal
//    dominio sarebbe un secondo posto dove la forma del documento e' scritta.
//
// ⚠️ L'EMITTENTE E' OBBLIGATORIO. La lista `vendite.note` ha il padre
//    composto (percorso + emittente): senza emittente la lista resta in
//    attesa del padre (`attesaPadre`) per sempre, senza errore e senza
//    righe. In DEV lo si dice in console (vedi `watch` sotto).
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { makeNotesApi } from '../../../core/api/notes'
import NoteDrawer from '../../../core/components/NoteDrawer.vue'
import { DOMINI_NOTE_VENDITE } from './dominiNote'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Slug dominio per il basePath API: `/vendite/{dominio}/{id}`.
  dominio: { type: String, required: true, validator: (v) => v in DOMINI_NOTE_VENDITE },
  // Id del documento padre; null finché non disponibile → drawer non montato.
  id: { type: [Number, null], default: null },
  // L'emittente del documento (PK): la lista `vendite.note` ha il perimetro
  // dell'emittente, e questo e' il lasciapassare del cancello (2026-10-31).
  // ⚠️ Della fattura e' `emittente_fiscale_pk`, non `emittente_fiscale_id`.
  emittenteFiscaleId: { type: Number, default: null },
  // Righe sorgente del select RIGA, gia' caricate dal padre: `{ id, <codice>,
  // <descrizione> }` coi nomi del dominio (`DOMINI_NOTE_VENDITE`). Chi non
  // le passa ha le sole note di documento selezionabili.
  righe: { type: Array, default: () => [] },
})
// `saved` ripropaga il TOTALE note emesso dal BB `NoteDrawer` (vedi lì): serve
// ai padri che mostrano un badge counter (`useContatoreNote.aggiorna`).
const emit = defineEmits(['update:visible', 'saved'])

const dominio = computed(() => DOMINI_NOTE_VENDITE[props.dominio])

const apiClient = computed(() => {
  if (!props.id) return null
  return makeNotesApi(`/vendite/${props.dominio}/${props.id}`, {
    emittenteFiscaleId: props.emittenteFiscaleId,
  })
})

// ⛔ Un drawer aperto senza emittente non e' una lista vuota: e' una lista che
//    non partira' mai. Il silenzio e' il difetto — in DEV si fa rumore.
if (import.meta.env.DEV) {
  watch(
    () => props.visible && props.id != null && props.emittenteFiscaleId == null,
    (senzaEmittente) => {
      if (!senzaEmittente) return
      console.warn(
        `[VenditeNoteDrawer] note di ${props.dominio} #${props.id} aperte senza ` +
        '`emittenteFiscaleId`: la lista `vendite.note` aspettera\' il padre per sempre. ' +
        'Passa la PK dell\'emittente del documento (fattura: `emittente_fiscale_pk`).',
      )
    },
    { immediate: true },
  )
}

// Adapter righe → opzioni select. Label "{codice} — {descrizione}" con
// fallback su id; campi del dominio.
// ⚠️ Le righe senza `id` sono escluse: alcune viste di esposizione producono
// righe sintetiche (es. KIT_PADRE di `vw_fattura_righe_esposte`, id NULL) che
// non esistono in tabella e non possono reggere la FK `target_riga_id` — senza
// guard il select mostrerebbe un'opzione «#null» che fallisce al salvataggio.
const righeOptions = computed(() => {
  const { codeField, descField } = dominio.value
  return (props.righe || []).filter((r) => r.id != null).map((r) => {
    const code = r[codeField]
    const desc = r[descField]
    return {
      value: r.id,
      label: code ? `${code}${desc ? ' — ' + desc : ''}` : `#${r.id}`,
    }
  })
})
</script>

<template>
  <NoteDrawer
    v-if="apiClient"
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    :api-client="apiClient"
    codice="vendite.note"
    :emittente-fiscale-id="emittenteFiscaleId"
    :title="t(dominio.titolo)"
    supports-riga
    :righe-options="righeOptions"
    @saved="(total) => emit('saved', total)"
  />
</template>

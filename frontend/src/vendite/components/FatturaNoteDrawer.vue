<script setup>
// Wrapper thin: cabla il BB `VenditeNoteDrawer` sulla fattura corrente.
// Sesto dominio note del ciclo attivo, simmetrico a preventivo/contratto/
// offerta/ordine/DDT; cambia solo dominio + title + i campi della label riga.
// ⭐ Le righe arrivano da `vw_fattura_righe_lista` (dal 2026-09-28, la stessa
//    vista della lista a video): il primo livello, con la chiave vera in
//    `fatture_righe_id` e i componenti esposti di un kit DENTRO il padre
//    (`componenti`). Una nota di riga si aggancia a una riga che esiste in
//    tabella: qui si appiattiscono le righe vere — quelle di primo livello e i
//    componenti — e il padre di un kit, che in tabella non c'e', resta fuori.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import VenditeNoteDrawer from '../_shared/note/VenditeNoteDrawer.vue'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
  fatturaId: { type: [Number, null], default: null },
  // Righe già caricate dal drawer padre (`dettaglio.righe`), per popolare il
  // select RIGA del form note. Shape di `vw_fattura_righe_lista`.
  righe: { type: Array, default: () => [] },
})

// Scopo: le righe VERE della fattura, nella forma del BB (`id`, codice,
//        descrizione): la riga di primo livello se esiste in tabella, poi i
//        suoi componenti esposti.
const righeVere = computed(() => props.righe.flatMap((r) => [
  ...(r.fatture_righe_id != null
    ? [{ id: r.fatture_righe_id, articolo_codice: r.articolo_codice, descrizione: r.descrizione }]
    : []),
  ...(r.componenti || []).map((c) => ({
    id: c.fatture_righe_id,
    articolo_codice: c.articolo_codice,
    descrizione: c.descrizione,
  })),
]))
// `saved` porta il totale note aggiornato (dal BB): il drawer fattura ci
// aggiorna il badge senza rileggere il dettaglio.
const emit = defineEmits(['update:visible', 'saved'])
</script>

<template>
  <VenditeNoteDrawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    dominio="fatture"
    :id="fatturaId"
    :title="t('vendite.fatture.note_titolo')"
    :righe="righeVere"
    code-field="articolo_codice"
    desc-field="descrizione"
    @saved="(total) => emit('saved', total)"
  />
</template>

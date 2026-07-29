<script setup>
// Wrapper thin: cabla il BB `VenditeNoteDrawer` sulla fattura corrente.
// Sesto dominio note del ciclo attivo, simmetrico a preventivo/contratto/
// offerta/ordine/DDT; cambia solo dominio + title + i campi della label riga.
// Le righe arrivano da `vw_fattura_righe_esposte`: le KIT_PADRE sintetiche
// (id NULL) sono scartate dal guard del BB (`righeOptions`), non qui.
import { useI18n } from 'vue-i18n'
import VenditeNoteDrawer from '../_shared/note/VenditeNoteDrawer.vue'

const { t } = useI18n()

defineProps({
  visible: { type: Boolean, default: false },
  fatturaId: { type: [Number, null], default: null },
  // Righe già caricate dal drawer padre, per popolare il select RIGA del form
  // note. Shape da `vw_fattura_righe_esposte` (articolo_codice, descrizione).
  righe: { type: Array, default: () => [] },
})
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
    :righe="righe"
    code-field="articolo_codice"
    desc-field="descrizione"
    @saved="(total) => emit('saved', total)"
  />
</template>

<script setup>
// Wrapper thin: cabla il BB `VenditeNoteDrawer` sull'ordine corrente.
// Simmetrico a Preventivo/Contratto/Offerta NoteDrawer; cambia solo dominio +
// title. Il basePath note diventa `/vendite/ordini/<id>` → `/note/` (BE
// PartitionedNoteRepository target_tipo='ORDINE_VENDITA').
import { useI18n } from 'vue-i18n'
import VenditeNoteDrawer from '../../_shared/note/VenditeNoteDrawer.vue'

const { t } = useI18n()

defineProps({
  visible: { type: Boolean, default: false },
  ordineId: { type: [Number, null], default: null },
  // Righe dell'ordine gia' caricate nel drawer padre: popolano il select RIGA
  // del form note. Le righe ordine espongono `articolo_codice`/`descrizione`.
  righe: { type: Array, default: () => [] },
})
// `saved` porta il TOTALE note aggiornato (dal BB `NoteDrawer`): il padre ci
// aggiorna il pulsante «Gestisci note» (`useContatoreNote`).
const emit = defineEmits(['update:visible', 'saved'])
</script>

<template>
  <VenditeNoteDrawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    dominio="ordini"
    :id="ordineId"
    :title="t('vendite.ordini.note_titolo')"
    :righe="righe"
    code-field="articolo_codice"
    desc-field="descrizione"
    @saved="(total) => emit('saved', total)"
  />
</template>

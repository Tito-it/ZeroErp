<script setup>
// Wrapper thin: cabla il BB `VenditeNoteDrawer` sul contratto corrente.
// Simmetrico a Preventivo/Offerta NoteDrawer; cambia solo dominio + title.
import { useI18n } from 'vue-i18n'
import VenditeNoteDrawer from '../_shared/note/VenditeNoteDrawer.vue'

const { t } = useI18n()

defineProps({
  visible: { type: Boolean, default: false },
  contrattoId: { type: [Number, null], default: null },
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
    dominio="contratti"
    :id="contrattoId"
    :title="t('vendite.contratti.note_titolo')"
    :righe="righe"
    @saved="(total) => emit('saved', total)"
  />
</template>

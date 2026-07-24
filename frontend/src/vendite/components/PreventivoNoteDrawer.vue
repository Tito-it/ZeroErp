<script setup>
// Wrapper thin: cabla il BB `VenditeNoteDrawer` sul preventivo corrente.
// Simmetrico a Contratto/Offerta NoteDrawer; cambia solo dominio + title.
import { useI18n } from 'vue-i18n'
import VenditeNoteDrawer from '../_shared/note/VenditeNoteDrawer.vue'

const { t } = useI18n()

defineProps({
  visible: { type: Boolean, default: false },
  preventivoId: { type: [Number, null], default: null },
  // Righe del preventivo gia' caricate nel drawer padre: usate per popolare
  // il select RIGA del form note. Shape attesa: [{ id, codice_articolo, descrizione, ... }].
  righe: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:visible', 'saved'])
</script>

<template>
  <VenditeNoteDrawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    dominio="preventivi"
    :id="preventivoId"
    :title="t('vendite.preventivi.note_titolo')"
    :righe="righe"
    @saved="emit('saved')"
  />
</template>

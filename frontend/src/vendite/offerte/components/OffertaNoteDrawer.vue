<script setup>
// Wrapper thin: cabla il BB `VenditeNoteDrawer` sull'offerta corrente.
// Simmetrico a Contratto/Preventivo NoteDrawer; oltre a dominio + title,
// le righe del select RIGA sono le eccezioni dell'offerta
// (`vendite.offerte_commerciali_eccezioni`), che espongono i campi label
// `articolo_codice`/`articolo_descrizione` → passati via codeField/descField.
import { useI18n } from 'vue-i18n'
import VenditeNoteDrawer from '../../_shared/note/VenditeNoteDrawer.vue'

const { t } = useI18n()

defineProps({
  visible: { type: Boolean, default: false },
  offertaId: { type: [Number, null], default: null },
  // Le eccezioni dell'offerta diventano opzioni del select RIGA del NoteDrawer.
  eccezioni: { type: Array, default: () => [] },
})
// `saved` porta il TOTALE note aggiornato (dal BB `NoteDrawer`): il padre ci
// aggiorna il pulsante «Gestisci note» (`useContatoreNote`).
const emit = defineEmits(['update:visible', 'saved'])
</script>

<template>
  <VenditeNoteDrawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    dominio="offerte"
    :id="offertaId"
    :title="t('vendite.offerte.note_titolo')"
    :righe="eccezioni"
    code-field="articolo_codice"
    desc-field="articolo_descrizione"
    @saved="(total) => emit('saved', total)"
  />
</template>

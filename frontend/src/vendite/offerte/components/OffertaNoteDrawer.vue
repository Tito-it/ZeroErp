<script setup>
// Wrapper thin: cabla il NoteDrawer generico sull'offerta corrente.
// Simmetrico a ContrattoNoteDrawer / PreventivoNoteDrawer: cambia solo
// il basePath API. Il building block sottostante gestisce CRUD, layout
// (lista + form sotto), permessi readonly via inject, scope (DOCUMENTO
// vs RIGA) e tutta la UX. Le righe esposte come opzioni del select RIGA
// sono le eccezioni dell'offerta (`vendite.offerte_commerciali_eccezioni`).
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { makeNotesApi } from '../../../core/api/notes'
import NoteDrawer from '../../../core/components/NoteDrawer.vue'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
  offertaId: { type: [Number, null], default: null },
  // Le eccezioni dell'offerta diventano opzioni del select RIGA del NoteDrawer.
  eccezioni: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:visible', 'saved'])

const apiClient = computed(() => {
  if (!props.offertaId) return null
  return makeNotesApi(`/vendite/offerte/${props.offertaId}`)
})

const righeOptions = computed(() => {
  return (props.eccezioni || []).map((e) => ({
    value: e.id,
    label: e.articolo_codice
      ? `${e.articolo_codice}${e.articolo_descrizione ? ' — ' + e.articolo_descrizione : ''}`
      : `#${e.id}`,
  }))
})
</script>

<template>
  <NoteDrawer
    v-if="apiClient"
    :visible="visible"
    :api-client="apiClient"
    :title="t('vendite.offerte.note_titolo')"
    supports-riga
    :righe-options="righeOptions"
    @update:visible="emit('update:visible', $event)"
    @saved="emit('saved')"
  />
</template>

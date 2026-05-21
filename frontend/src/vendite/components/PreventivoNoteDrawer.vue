<script setup>
// Wrapper thin: cabla il NoteDrawer generico sul preventivo corrente.
// Costruisce il basePath dell'API e l'elenco righe per il select RIGA.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { makeNotesApi } from '../../core/api/notes'
import NoteDrawer from '../../core/components/NoteDrawer.vue'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
  preventivoId: { type: [Number, null], default: null },
  // Righe del preventivo gia' caricate nel drawer padre: usate per popolare
  // il select RIGA del form note. Shape attesa: [{ id, codice_articolo, descrizione, ... }].
  righe: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:visible', 'saved'])

const apiClient = computed(() => {
  if (!props.preventivoId) return null
  return makeNotesApi(`/vendite/preventivi/${props.preventivoId}`)
})

// Adapter righe -> opzioni select. Etichetta ottimizzata per readability nel
// dropdown: "{codice_articolo} — {descrizione}" o fallback su id.
const righeOptions = computed(() => {
  return (props.righe || []).map(r => ({
    value: r.id,
    label: r.codice_articolo
      ? `${r.codice_articolo}${r.descrizione ? ' — ' + r.descrizione : ''}`
      : `#${r.id}`,
  }))
})
</script>

<template>
  <NoteDrawer
    v-if="apiClient"
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    :api-client="apiClient"
    :title="t('preventivi.note_titolo')"
    supports-riga
    :righe-options="righeOptions"
    @saved="emit('saved')"
  />
</template>

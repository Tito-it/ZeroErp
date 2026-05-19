<script setup>
// Wrapper thin: cabla il NoteDrawer generico sul contratto corrente.
// Simmetrico a PreventivoNoteDrawer; cambia solo il basePath API.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { makeNotesApi } from '../../core/api/notes'
import NoteDrawer from '../../core/components/NoteDrawer.vue'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
  contrattoId: { type: [Number, null], default: null },
  righe: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:visible', 'saved'])

const apiClient = computed(() => {
  if (!props.contrattoId) return null
  return makeNotesApi(`/vendite/contratti/${props.contrattoId}`)
})

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
    :title="t('contratti.note_titolo')"
    supports-riga
    :righe-options="righeOptions"
    @saved="emit('saved')"
  />
</template>

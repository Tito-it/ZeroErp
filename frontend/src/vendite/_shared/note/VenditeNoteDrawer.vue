<script setup>
// Building block: drawer note per i documenti vendite (contratti, preventivi,
// offerte). Assorbe il boilerplate dei wrapper di dominio — costruzione
// `apiClient` dal basePath, mappatura righe→opzioni del select RIGA, render
// del `NoteDrawer` generico. Le note usano la stessa tabella/API per tutti i
// domini (`makeNotesApi`); l'unica divergenza fra i domini sono le righe
// sorgente del select RIGA (contratti/preventivi espongono
// `codice_articolo`/`descrizione`, le eccezioni offerta
// `articolo_codice`/`articolo_descrizione`) → parametrizzate via
// `codeField`/`descField`.
import { computed } from 'vue'
import { makeNotesApi } from '../../../core/api/notes'
import NoteDrawer from '../../../core/components/NoteDrawer.vue'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Slug dominio per il basePath API: `/vendite/{dominio}/{id}`.
  dominio: { type: String, required: true },
  // Id del documento padre; null finché non disponibile → drawer non montato.
  id: { type: [Number, null], default: null },
  title: { type: String, default: '' },
  // Righe sorgente del select RIGA (righe documento o eccezioni offerta).
  righe: { type: Array, default: () => [] },
  // Nomi campo per la label opzione, variano per dominio.
  codeField: { type: String, default: 'codice_articolo' },
  descField: { type: String, default: 'descrizione' },
})
const emit = defineEmits(['update:visible', 'saved'])

const apiClient = computed(() => {
  if (!props.id) return null
  return makeNotesApi(`/vendite/${props.dominio}/${props.id}`)
})

// Adapter righe → opzioni select. Label "{codice} — {descrizione}" con
// fallback su id; campi parametrici per assorbire la divergenza offerta.
const righeOptions = computed(() => {
  return (props.righe || []).map((r) => {
    const code = r[props.codeField]
    const desc = r[props.descField]
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
    :title="title"
    supports-riga
    :righe-options="righeOptions"
    @saved="emit('saved')"
  />
</template>

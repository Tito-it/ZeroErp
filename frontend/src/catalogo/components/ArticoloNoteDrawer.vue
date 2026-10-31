<script setup>
// Wrapper thin: cabla il NoteDrawer generico (BB partizionato) sull'articolo
// corrente. Refactor 2026-05-21 (Fase 2.B): sostituisce il vecchio
// CatalogoNoteDrawer ad-hoc per allinearsi al pattern usato da preventivi/
// contratti. Lo schema DB `catalogo.note` e' gemello di `vendite.note`
// (target_tipo/target_id/target_riga_id/anchor_tipo/posizione/seq/visibile/
// solo_stampa/id_stile/id_lingua/meta); cambia solo il routing URL (pattern
// "split": LIST/POST sotto parent, DETAIL su /catalogo/note/<id>/),
// gestito da `makeArticoloNotesApi`.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import NoteDrawer from '../../core/components/NoteDrawer.vue'
import { makeArticoloNotesApi } from '../api/catalogo'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null },
})
// `saved` porta il TOTALE note aggiornato (dal BB `NoteDrawer`): il padre ci
// aggiorna il pulsante «Gestisci note» (`useContatoreNote`).
const emit = defineEmits(['update:visible', 'saved'])

// articoloId e' UUID (catalogo.articoli.id); il padre della lista del
// `NoteDrawer` e' il percorso del client (`basePath`), quindi un cambio
// articolo durante il lifecycle rilegge la lista giusta.
const apiClient = computed(() => {
  if (!props.articoloId) return null
  return makeArticoloNotesApi(props.articoloId)
})
</script>

<template>
  <NoteDrawer
    v-if="apiClient"
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    :api-client="apiClient"
    codice="catalogo.note"
    :title="t('catalogo.tab_note')"
    @saved="(total) => emit('saved', total)"
  />
</template>

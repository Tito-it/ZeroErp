<script setup>
// Scopo: Sub-drawer per gestione note articolo.
// Wrapper su CatalogoNoteDrawer generico con API articolo.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { listArticoloNote, createArticoloNota } from '../api/catalogo'
import CatalogoNoteDrawer from '../../core/components/CatalogoNoteDrawer.vue'

const { t } = useI18n()

const props = defineProps({
  visible: { type: Boolean, default: false },
  articoloId: { type: [String, null], default: null }
})
const emit = defineEmits(['update:visible', 'saved'])

const listFn = computed(() => () => listArticoloNote(props.articoloId))
const createFn = computed(() => (payload) => createArticoloNota(props.articoloId, payload))
</script>

<template>
  <CatalogoNoteDrawer
    :visible="visible"
    @update:visible="emit('update:visible', $event)"
    :list-fn="listFn"
    :create-fn="createFn"
    :title="t('catalogo.tab_note')"
    @saved="emit('saved')"
  />
</template>

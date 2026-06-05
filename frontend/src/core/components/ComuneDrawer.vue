<script setup>
// Scopo: drawer per creazione comuni non censiti (esteri, frazioni).
// Wrapper su EntityFormDrawer (schema-driven). Solo create (nessun mode/item):
// EntityFormDrawer usa il default mode='create'.
// Riusabile da: tab Comuni, futuro gestione anagrafiche.
import EntityFormDrawer from './EntityFormDrawer.vue'
import { useComuniStore } from '../../anagrafiche/stores/comuni'
import { lookupProvince } from '../../anagrafiche/api/anagrafiche'
import { NAV_ICONS } from '../navigation'

defineProps({
  visible: { type: Boolean, default: false },
})
const emit = defineEmits(['update:visible', 'saved'])

const store = useComuniStore()
const fields = [
  { name: 'descrizione', type: 'text', labelKey: 'indirizzi.campo_descrizione', required: true },
  {
    name: 'provincia_id',
    type: 'select',
    labelKey: 'indirizzi.campo_provincia',
    lookupFn: lookupProvince,
    placeholderKey: 'indirizzi.select_provincia',
  },
]
</script>

<template>
  <EntityFormDrawer
    :visible="visible"
    :store="store"
    :fields="fields"
    title-key="indirizzi.comune"
    :icon="NAV_ICONS.COMUNE"
    :refresh-on-save="false"
    :success-keys="{ create: 'indirizzi.comune_creato' }"
    @update:visible="emit('update:visible', $event)"
    @saved="emit('saved')"
  />
</template>

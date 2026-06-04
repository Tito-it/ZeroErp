<script setup>
// Scopo: drawer CRUD province. Wrapper su EntityFormDrawer (schema-driven).
import EntityFormDrawer from './EntityFormDrawer.vue'
import { useProvinceStore } from '../../anagrafiche/stores/province'
import { lookupRegioni } from '../../anagrafiche/api/anagrafiche'
import { NAV_ICONS } from '../navigation'

defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  item: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'saved'])

const store = useProvinceStore()
const fields = [
  { name: 'descrizione', type: 'text', labelKey: 'geo.col_descrizione', required: true },
  { name: 'sigla', type: 'text', labelKey: 'geo.col_sigla', required: true, maxlength: 10 },
  {
    name: 'regione_id',
    type: 'select',
    labelKey: 'geo.col_regione',
    lookupFn: lookupRegioni,
    placeholderKey: 'geo.select_regione',
  },
]
</script>

<template>
  <EntityFormDrawer
    :visible="visible"
    :mode="mode"
    :item="item"
    :store="store"
    :fields="fields"
    title-key="geo.provincia"
    :icon="NAV_ICONS.PROVINCIA"
    :refresh-on-save="false"
    :success-keys="{ create: 'geo.provincia_creata', update: 'geo.provincia_salvata' }"
    @update:visible="emit('update:visible', $event)"
    @saved="emit('saved')"
  />
</template>

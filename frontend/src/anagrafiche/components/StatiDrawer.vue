<script setup>
// Scopo: drawer CRUD stati (nazioni). Wrapper su EntityFormDrawer (schema-driven).
import EntityFormDrawer from '../../core/components/EntityFormDrawer.vue'
import { useStatiStore } from '../stores/stati'
import { DRAWER_WIDTH } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'

defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  item: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'saved'])

const store = useStatiStore()
const fields = [
  { name: 'descrizione', type: 'text', labelKey: 'geo.col_descrizione', required: true },
  {
    group: true,
    fields: [
      { name: 'codice_iso2', type: 'text', labelKey: 'geo.col_iso2', maxlength: 2 },
      { name: 'codice_iso3', type: 'text', labelKey: 'geo.col_iso3', maxlength: 3 },
      { name: 'sigla_stato', type: 'text', labelKey: 'geo.col_sigla', maxlength: 10 },
      { name: 'codice_telefonico', type: 'text', labelKey: 'geo.col_telefono', maxlength: 10 },
    ],
  },
  { name: 'continente', type: 'text', labelKey: 'geo.col_continente' },
]
</script>

<template>
  <EntityFormDrawer
    :visible="visible"
    :mode="mode"
    :item="item"
    :store="store"
    :fields="fields"
    title-key="geo.stato"
    :icon="NAV_ICONS.STATO"
    :width="DRAWER_WIDTH.STANDARD"
    :refresh-on-save="false"
    :success-keys="{ create: 'geo.stato_creato', update: 'geo.stato_salvato' }"
    @update:visible="emit('update:visible', $event)"
    @saved="emit('saved')"
  />
</template>

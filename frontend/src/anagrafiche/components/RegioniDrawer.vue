<script setup>
// Scopo: drawer CRUD regioni. Wrapper su EntityFormDrawer (schema-driven).
import EntityFormDrawer from '../../core/components/EntityFormDrawer.vue'
import { useRegioniStore } from '../stores/regioni'
import { lookupStati } from '../api/anagrafiche'
import { NAV_ICONS } from '../../core/navigation'

defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  item: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'saved'])

const store = useRegioniStore()
const fields = [
  { name: 'descrizione', type: 'text', labelKey: 'geo.col_descrizione', required: true },
  {
    name: 'stato_id',
    type: 'select',
    labelKey: 'geo.col_stato',
    lookupFn: lookupStati,
    placeholderKey: 'geo.select_stato',
    // NOT NULL a DB: svuotarlo e' un 400 della PATCH, non un «non toccare».
    required: true,
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
    title-key="geo.regione"
    :icon="NAV_ICONS.REGIONE"
    :refresh-on-save="false"
    :success-keys="{ create: 'geo.regione_creata', update: 'geo.regione_salvata' }"
    @update:visible="emit('update:visible', $event)"
    @saved="emit('saved')"
  />
</template>

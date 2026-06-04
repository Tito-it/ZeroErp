<script setup>
// Scopo: drawer CRUD codici postali (CAP). Wrapper su EntityFormDrawer.
// NB refresh-on-save=false: il refresh lista e' coperto da useTabFreshness
// (emitDataChanged dello store) — niente fetchList esplicito ridondante.
import EntityFormDrawer from './EntityFormDrawer.vue'
import ComuneAutocomplete from './ComuneAutocomplete.vue'
import { useCodiciPostaliStore } from '../../anagrafiche/stores/codiciPostali'
import { NAV_ICONS } from '../navigation'

defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  item: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'saved'])

const store = useCodiciPostaliStore()
const fields = [
  { name: 'codice', type: 'text', labelKey: 'indirizzi.col_cap', required: true, maxlength: 5 },
  {
    name: 'comune_id',
    type: 'autocomplete',
    labelKey: 'indirizzi.campo_comune',
    required: true,
    component: ComuneAutocomplete,
    disabledInEdit: true,
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
    title-key="indirizzi.cap"
    :icon="NAV_ICONS.CAP"
    :refresh-on-save="false"
    :success-keys="{ create: 'indirizzi.cap_creato', update: 'indirizzi.cap_salvato' }"
    @update:visible="emit('update:visible', $event)"
    @saved="emit('saved')"
  />
</template>

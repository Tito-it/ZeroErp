<script setup>
// Scopo: drawer CRUD toponomastica (tipi strada). Wrapper su EntityFormDrawer.
// Riusabile da: tab Toponomastica, futuro gestione stradario.
// Il toggle `attivo` e' editOnly: mostrato/inviato solo in edit (in create
// l'entita' nasce attiva via default DB).
import EntityFormDrawer from '../../core/components/EntityFormDrawer.vue'
import { useToponomasticaStore } from '../stores/toponomastica'
import { NAV_ICONS } from '../../core/navigation'

defineProps({
  visible: { type: Boolean, default: false },
  mode: { type: String, default: 'create' },
  item: { type: Object, default: null },
})
const emit = defineEmits(['update:visible', 'saved'])

const store = useToponomasticaStore()
const fields = [
  { name: 'descrizione', type: 'text', labelKey: 'indirizzi.campo_descrizione', required: true },
  { name: 'attivo', type: 'toggle', labelKey: 'indirizzi.campo_attivo', editOnly: true },
]
</script>

<template>
  <EntityFormDrawer
    :visible="visible"
    :mode="mode"
    :item="item"
    :store="store"
    :fields="fields"
    title-key="indirizzi.toponomastica"
    :icon="NAV_ICONS.TOPONOMASTICA"
    :refresh-on-save="false"
    :success-keys="{ create: 'indirizzi.toponomastica_creata', update: 'indirizzi.toponomastica_salvata' }"
    @update:visible="emit('update:visible', $event)"
    @saved="emit('saved')"
  />
</template>

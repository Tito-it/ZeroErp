<script setup>
// Scopo: Host cross-dominio che apre, "a comando", il drawer di DETTAGLIO del
// documento vendite corrispondente a un tipo sorgente + id — così le tappe
// del pannello "Passaggi" aprono il dettaglio impilato (come il link pratica
// apre PraticaDrawer), invece di navigare alla lista. La mappa tipo->drawer
// (con import async che spezza il ciclo di import) vive in lineageDrawers.js.
import { ref, computed, watch, nextTick } from 'vue'
import { LINEAGE_DRAWERS } from './lineageDrawers'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Tipo sorgente della tappa da aprire (codice_interno).
  tipoCodice: { type: String, default: null },
  // Id numerico di dominio del documento (from_doc_id/to_doc_id BE).
  docId: { type: [Number, null], default: null },
})

const emit = defineEmits(['update:visible'])

// Drawer attualmente montato (resta montato-nascosto dopo la chiusura: un
// solo drawer, costo trascurabile; il prossimo open lo rimpiazza).
const activeTipo = ref(null)
const activeId = ref(null)
const innerVisible = ref(false)
// Contatore di aperture: entra nella :key -> ogni open rimonta un'istanza
// PULITA del drawer anche su stesso (tipo, id). Senza, il drawer riaperto
// mostrerebbe lo stato del load precedente (catena/dettaglio stantii se nel
// frattempo il documento e' cambiato: evasione, push, reso).
const openSeq = ref(0)

const activeEntry = computed(() => (activeTipo.value ? LINEAGE_DRAWERS[activeTipo.value] : null))

// Props del drawer attivo: la prop id ha nome variabile per dominio; `mode`
// solo dove il drawer lo accetta (edit = dettaglio su id esistente).
const drawerProps = computed(() => {
  const entry = activeEntry.value
  if (!entry) return {}
  const p = { [entry.idProp]: activeId.value }
  if (entry.hasMode) p.mode = 'edit'
  return p
})

// Apertura: monta il drawer del tipo richiesto e lo apre al tick successivo
// (visible false->true dà lo slide-in di PrimeVue Drawer).
watch(
  () => [props.visible, props.tipoCodice, props.docId],
  ([vis, tipo, id]) => {
    if (vis && tipo && id != null && LINEAGE_DRAWERS[tipo]) {
      activeTipo.value = tipo
      activeId.value = id
      openSeq.value += 1
      nextTick(() => { innerVisible.value = true })
    } else {
      innerVisible.value = false
    }
  },
  { immediate: true },
)

// Scopo: Chiusura dal drawer figlio -> propaga al genitore (che azzera il
// proprio flag di visibilità).
function onInnerVisible(v) {
  innerVisible.value = v
  if (!v) emit('update:visible', false)
}
</script>

<template>
  <component
    :is="activeEntry.comp"
    v-if="activeEntry"
    :key="`${activeTipo}:${activeId}:${openSeq}`"
    :visible="innerVisible"
    v-bind="drawerProps"
    @update:visible="onInnerVisible" />
</template>

<script setup>
// Scopo: Host cross-dominio che apre, "a comando", il drawer di DETTAGLIO del
// documento vendite corrispondente a una chiave registry + id — così le tappe
// del pannello "Passaggi" e le righe drill-down dei cruscotti aprono il
// dettaglio impilato (come il link pratica apre PraticaDrawer), invece di
// navigare alla lista. La mappa chiave->drawer (con import async che spezza il
// ciclo di import) vive in documentoDrawers.js.
import { ref, computed, watch, nextTick, markRaw } from 'vue'
import { DOCUMENTO_DRAWERS } from './documentoDrawers'

const props = defineProps({
  visible: { type: Boolean, default: false },
  // Chiave registry del documento da aprire: tipo sorgente (codice_interno)
  // per le tappe lineage, chiave non-sorgente per i drawer senza sorgente
  // propria (COMMESSA_GESTIONE).
  tipoCodice: { type: String, default: null },
  // Id numerico di dominio del documento (from_doc_id/to_doc_id BE lineage,
  // documento_id delle viste vw_dash_* per i cruscotti).
  docId: { type: [Number, null], default: null },
})

const emit = defineEmits(['update:visible'])

// Drawer attualmente montato (resta montato-nascosto dopo la chiusura: un
// solo drawer, costo trascurabile; il prossimo open lo rimpiazza).
const activeTipo = ref(null)
const activeId = ref(null)
const innerVisible = ref(false)
// Componente RISOLTO del drawer attivo (il modulo importato, non un
// `defineAsyncComponent`): reso solo dopo che il chunk e' caricato, così monta
// in modo SINCRONO con `innerVisible=false` e osserva poi la transizione
// false->true che innesca `@after-show`/il watch di caricamento dettaglio.
// Con un componente async il figlio reale montava un microtask dopo, quando
// `innerVisible` era gia' true -> apertura con i soli default (bug "prima
// volta vuoto"). markRaw: e' una definizione componente, non va resa reattiva.
const resolvedComp = ref(null)
// Contatore di aperture: entra nella :key -> ogni open rimonta un'istanza
// PULITA del drawer anche su stesso (tipo, id). Senza, il drawer riaperto
// mostrerebbe lo stato del load precedente (catena/dettaglio stantii se nel
// frattempo il documento e' cambiato: evasione, push, reso). Fa anche da
// token anti-stale per l'apertura async sotto (open concorrenti).
const openSeq = ref(0)

const activeEntry = computed(() => (activeTipo.value ? DOCUMENTO_DRAWERS[activeTipo.value] : null))

// Props del drawer attivo: la prop id ha nome variabile per dominio; `mode`
// solo dove il drawer lo accetta (edit = dettaglio su id esistente).
const drawerProps = computed(() => {
  const entry = activeEntry.value
  if (!entry) return {}
  const p = { [entry.idProp]: activeId.value }
  if (entry.hasMode) p.mode = 'edit'
  return p
})

// Apertura: (1) attende il caricamento del chunk del drawer, (2) rende il
// componente risolto -> monta nascosto (visible=false), (3) al tick successivo
// lo apre (visible false->true dà lo slide-in di PrimeVue Drawer E fa scattare
// @after-show/il watch di caricamento dettaglio del figlio). Attendere il
// chunk e montare il componente reale PRIMA di aprire e' cio' che elimina il
// "primo click apre vuoto": senza, il figlio nasceva gia' visibile (o montava
// asincrono dopo il flip) e non vedeva la transizione.
watch(
  () => [props.visible, props.tipoCodice, props.docId],
  async ([vis, tipo, id]) => {
    if (!(vis && tipo && id != null && DOCUMENTO_DRAWERS[tipo])) {
      innerVisible.value = false
      return
    }
    const entry = DOCUMENTO_DRAWERS[tipo]
    activeTipo.value = tipo
    activeId.value = id
    innerVisible.value = false
    resolvedComp.value = null
    const seq = (openSeq.value += 1)
    // Carica il chunk PRIMA di rendere il drawer, poi rende il componente
    // risolto (mount sincrono). Import deduplicato dalla cache dei moduli.
    let mod
    try { mod = await entry.load() } catch { return }
    // Apertura piu' recente vince: scarta i risultati di open sorpassate.
    if (seq !== openSeq.value) return
    resolvedComp.value = markRaw(mod.default ?? mod)
    await nextTick() // il drawer monta ora, ancora nascosto (visible=false)
    if (seq !== openSeq.value) return
    innerVisible.value = true // transizione false->true: slide-in + load figlio
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
    :is="resolvedComp"
    v-if="resolvedComp"
    :key="`${activeTipo}:${activeId}:${openSeq}`"
    :visible="innerVisible"
    v-bind="drawerProps"
    @update:visible="onInnerVisible" />
</template>

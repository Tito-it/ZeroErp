<script setup>
// Scopo: Vista principale gestione articoli catalogo.
//        Drawer articolo + sub-drawer UoM/BoM/Note apribili da lista e da drawer.
import { ref } from 'vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useIngressoDaQuery } from '../../core/composables/useIngressoDaQuery'
import { FORME_ID, idNellaForma } from '../../core/utils/idNellaForma'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useArticoliStore } from '../stores/articoli'
import ArticoliSearchTable from '../components/ArticoliSearchTable.vue'
import ArticoloDrawer from '../components/ArticoloDrawer.vue'
import ArticoloUomDrawer from '../components/ArticoloUomDrawer.vue'
import ArticoloBomDrawer from '../components/ArticoloBomDrawer.vue'
import ArticoloNoteDrawer from '../components/ArticoloNoteDrawer.vue'

const drawer = useDrawerState()
const store = useArticoliStore()
const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)
useReadonlyMode(READONLY_DOMAINS.CATALOGO, READONLY_MODELS.ARTICOLO)

// Sub-drawer aperti dalla lista
const uomDrawerVisible = ref(false)
const uomArticoloId = ref(null)
const bomDrawerVisible = ref(false)
const bomArticoloId = ref(null)
const noteDrawerVisible = ref(false)
const noteArticoloId = ref(null)

// ⛔ Ritirato il 2026-11-11 (ok Tid) un `watch` sul contesto globale
//    (`ctx.entitaId`), copiato dalle liste dei soggetti alla nascita della
//    vista: il contesto porta il `cliente_id`/`fornitore_id` di un soggetto,
//    mai un articolo, e qui apriva un drawer articolo con l'id di un cliente.
//    Si apre un articolo dalla lista o dal deep-link qui sotto.
// ⭐ Deep-link `?open=<uuid>`: la lista apre l'articolo indicato. Lo usa il
//    BERSAGLIO di un errore (2026-11-11, S-BE-1 di brief-db-revisione-dbops):
//    «Apri articolo» sul padre spento. L'id e' un uuid (`catalogo.articoli.id`).
//    ⚠️ Apre e basta: cosa si puo' fare dell'articolo lo dicono i permessi di
//    chi clicca (drawer in sola lettura, capability), come dalla lista.
useIngressoDaQuery({
  nomeRotta: 'catalogo-articoli',
  gestori: {
    open: (grezzo) => {
      const id = idNellaForma(grezzo, FORME_ID.UUID)
      if (id !== null) drawer.editRow({ id }, 'id')
    },
  },
})

function onManageUom(data) {
  uomArticoloId.value = data.id
  uomDrawerVisible.value = true
}
function onManageBom(data) {
  bomArticoloId.value = data.id
  bomDrawerVisible.value = true
}
function onManageNote(data) {
  noteArticoloId.value = data.id
  noteDrawerVisible.value = true
}
</script>

<template>
  <div class="app-page">
    <ArticoliSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @manage-uom="onManageUom"
      @manage-bom="onManageBom"
      @manage-note="onManageNote"
    />

    <ArticoloDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :articolo-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <!-- Sub-drawer aperti dalla lista -->
    <ArticoloUomDrawer
      :visible="uomDrawerVisible"
      @update:visible="v => uomDrawerVisible = v"
      :articolo-id="uomArticoloId"
    />
    <ArticoloBomDrawer
      :visible="bomDrawerVisible"
      @update:visible="v => bomDrawerVisible = v"
      :articolo-id="bomArticoloId"
    />
    <ArticoloNoteDrawer
      :visible="noteDrawerVisible"
      @update:visible="v => noteDrawerVisible = v"
      :articolo-id="noteArticoloId"
    />
  </div>
</template>

<script setup>
// Scopo: Vista principale gestione offerte commerciali.
//        Host della lista + drawer master + handler navigazione post-push
//        verso ContrattoDrawer via deep-link `?open=<id>` (cablato in
//        ContrattiListView con watcher su route.query.open).
import { useRouter } from 'vue-router'
import { useDrawerState } from '../../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../../core/constants'
import OfferteSearchTable from '../components/OfferteSearchTable.vue'
import OffertaDrawer from '../components/OffertaDrawer.vue'
import { useOfferteStore } from '../stores/offerte'

const drawer = useDrawerState()
const store = useOfferteStore()
const router = useRouter()

// Permessi: livello area `vendite` + livello oggetto `offerta_commerciale`
// (in attesa che il BE catalogizzi il model in `config.area_model_overrides`).
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.OFFERTA_COMMERCIALE)

async function onDrawerSaved(data) {
  // Se l'evento porta un id diverso (es. revisione N+1), apriamo direttamente
  // la nuova offerta in edit. Altrimenti: refresh lista + chiudi drawer.
  if (data?.id && data.id !== drawer.state.itemId) {
    drawer.editRow({ id: data.id }, 'id')
    if (store.hasSearched) await store.fetchList()
    return
  }
  store.filters.offset = 0
  if (store.hasSearched) await store.fetchList()
  drawer.close()
}

// Post-push contratto (o click "Apri contratto esistente" dal dialog
// "gia' generato"): naviga a /vendite/contratti?open=<id>. Il
// ContrattiListView intercetta il query param e apre il drawer in edit.
function onNavigateContratto({ contrattoId }) {
  if (!contrattoId) return
  // Chiude il drawer offerta prima di navigare per evitare due drawer
  // aperti contemporaneamente (PrimeVue non lo supporta).
  drawer.close()
  router.push({ name: 'vendite-contratti', query: { open: contrattoId } })
}
</script>

<template>
  <div class="app-page">
    <OfferteSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <OffertaDrawer
      :visible="drawer.state.visible"
      :mode="drawer.state.mode"
      :offerta-id="drawer.state.itemId"
      @update:visible="(v) => (drawer.state.visible = v)"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
      @navigate-contratto="onNavigateContratto"
    />
  </div>
</template>

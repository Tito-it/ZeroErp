<script setup>
// Scopo: Vista gestione contratti v5 (testata + pricing A/B/C + righe + utility).
import { nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useContrattiStore } from '../stores/contratti'
import ContrattiSearchTable from '../components/ContrattiSearchTable.vue'
import ContrattoDrawer from '../components/ContrattoDrawer.vue'
import ContrattoRigheDrawer from '../components/ContrattoRigheDrawer.vue'

const drawer = useDrawerState()
const store = useContrattiStore()
const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)
const route = useRoute()
const router = useRouter()

// Provider readonly dominio vendite.
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.CONTRATTO)

// Deep-link: ?open=<id> apre direttamente il drawer in edit. Usato per la
// navigazione cross-dominio (es. post-push da OffertaDrawer). Il query
// param viene rimosso dopo l'apertura per evitare ri-apertura su refresh.
watch(
  () => route.query.open,
  (openId) => {
    if (!openId) return
    const idNum = Number(openId)
    if (!Number.isFinite(idNum) || idNum <= 0) return
    nextTick(() => {
      drawer.editRow({ id: idNum }, 'id')
      // Rimuove il query param per pulire l'URL.
      const newQuery = { ...route.query }
      delete newQuery.open
      router.replace({ query: newQuery })
    })
  },
  { immediate: true },
)

// Drawer righe aperto direttamente dalla lista
const righeDrawer = ref({
  visible: false,
  contrattoId: null,
  emittenteFiscaleId: null,
  numero: '',
  cliente: '',
  validoDal: '',
  validoAl: null,
  statoCodice: '',
  statoDescrizione: '',
})

// Scopo: Apre il drawer righe direttamente dalla lista.
// Carica il dettaglio per il contesto (intestazione ed emittente): le righe
// le legge il drawer, dalla sua lista.
async function onOpenRighe(data) {
  const detail = await store.fetchDetail(data.id)
  if (!detail) return
  righeDrawer.value = {
    visible: true,
    contrattoId: detail.id,
    emittenteFiscaleId: detail.emittente_fiscale_id ?? null,
    numero: detail.numero,
    cliente: detail.ba_ragione_sociale,
    validoDal: detail.valido_dal,
    validoAl: detail.valido_al,
    statoCodice: detail.stato_codice_interno,
    statoDescrizione: detail.stato_descrizione,
  }
}
</script>

<template>
  <div class="app-page">
    <ContrattiSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
      @open-righe="onOpenRighe"
    />

    <ContrattoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :contratto-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />

    <ContrattoRigheDrawer
      :visible="righeDrawer.visible"
      @update:visible="v => righeDrawer.visible = v"
      :contratto-id="righeDrawer.contrattoId"
      :emittente-fiscale-id="righeDrawer.emittenteFiscaleId"
      :contratto-numero="righeDrawer.numero"
      :contratto-cliente="righeDrawer.cliente"
      :contratto-valido-dal="righeDrawer.validoDal"
      :contratto-valido-al="righeDrawer.validoAl"
      :contratto-stato-codice="righeDrawer.statoCodice"
      :contratto-stato-descrizione="righeDrawer.statoDescrizione"
    />
  </div>
</template>

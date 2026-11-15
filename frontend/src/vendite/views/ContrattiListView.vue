<script setup>
// Scopo: Vista gestione contratti v5 (testata + pricing A/B/C + righe + utility).
import { ref } from 'vue'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useDrawerSavedListRefresh } from '../../core/composables/useDrawerSavedListRefresh'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useIngressoDaQuery } from '../../core/composables/useIngressoDaQuery'
import { FORME_ID, idNellaForma } from '../../core/utils/idNellaForma'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { useContrattiStore } from '../stores/contratti'
import ContrattiSearchTable from '../components/ContrattiSearchTable.vue'
import ContrattoDrawer from '../components/ContrattoDrawer.vue'
import ContrattoRigheDrawer from '../components/ContrattoRigheDrawer.vue'

const drawer = useDrawerState()
const store = useContrattiStore()
const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)

// Provider readonly dominio vendite.
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.CONTRATTO)

// Deep-link: ?open=<id> apre direttamente il drawer in edit. Usato per la
// navigazione cross-dominio (post-push da OffertaDrawer) e dal bersaglio di un
// errore. Guard sulla rotta, KeepAlive e pulizia della query: BB
// `useIngressoDaQuery` (2026-11-11; prima un `watch` senza guard, che sotto
// KeepAlive reagiva anche al `?open=` di un'altra lista).
useIngressoDaQuery({
  nomeRotta: 'vendite-contratti',
  gestori: {
    open: (grezzo) => {
      const id = idNellaForma(grezzo, FORME_ID.INTERO)
      if (id !== null) drawer.editRow({ id }, 'id')
    },
  },
})

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
  righeModificabili: false,
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
    // La capability del DB (`can_edit_righe`): il drawer non rilegge lo stato.
    righeModificabili: detail.capabilities?.can_edit_righe === true,
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
      :righe-modificabili="righeDrawer.righeModificabili"
    />
  </div>
</template>

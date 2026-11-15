<script setup>
// Scopo: Vista admin promo articoli (dominio vendite, operativa-commerciale).
//        STADIO 0 del resolver pricing v5.
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useIngressoDaQuery } from '../../core/composables/useIngressoDaQuery'
import { FORME_ID, idNellaForma } from '../../core/utils/idNellaForma'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../core/constants'
import { usePromoArticoliStore } from '../stores/promoArticoli'
import PromoArticoliSearchTable from '../components/PromoArticoliSearchTable.vue'
import PromoArticoloDrawer from '../components/PromoArticoloDrawer.vue'

const drawer = useDrawerState()
const store = usePromoArticoliStore()

// Provider readonly con override per model 'promo_articolo' (v2 permessi):
// default = livello area 'vendite', ma admin puo' impostare un override
// specifico sulle promo senza toccare il resto dell'area.
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.PROMO_ARTICOLO)

// ⭐ Deep-link `?open=<id>`: la lista apre la promo indicata. Lo usa il
//    BERSAGLIO di un errore (2026-11-11, S-BE-1 di brief-db-revisione-dbops).
//    Apre e basta: cosa si puo' fare lo dicono i permessi di chi clicca.
useIngressoDaQuery({
  nomeRotta: 'vendite-promo-articoli',
  gestori: {
    open: (grezzo) => {
      const id = idNellaForma(grezzo, FORME_ID.INTERO)
      if (id !== null) drawer.editRow({ id }, 'id')
    },
  },
})

async function onDrawerSaved() {
  store.filters.offset = 0
  await store.fetchList()
  drawer.close()
}
</script>

<template>
  <div class="app-page">
    <PromoArticoliSearchTable
      @new="drawer.openCreate"
      @row-click="(data) => drawer.editRow(data, 'id')"
    />

    <PromoArticoloDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :mode="drawer.state.mode"
      :record-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>

<script setup>
// Scopo: Vista principale gestione resi di vendita. Tre tab: lista resi
//        (configurabile) + le due code di lavoro "da accreditare" (righe a
//        credito CONFERMATE, predisposizione slice nota di credito) e "da
//        ri-consegnare" (righe per ri-consegna con copertura pendente).
//        Host del drawer reso. Il reso NASCE solo dal DDT (pannello nel
//        drawer DDT): nessuna azione "Nuovo" qui. Clone ridotto di DdtView.
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import Tab from 'primevue/tab'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'

import { useDrawerState } from '../../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, READONLY_MODELS } from '../../../core/constants'
import { useResiStore } from '../stores/resi'
import ResiSearchTable from '../components/ResiSearchTable.vue'
import ResiCodaTable from '../components/ResiCodaTable.vue'
import ResoDrawer from '../components/ResoDrawer.vue'

const { t } = useI18n()
const drawer = useDrawerState()
const store = useResiStore()
const activeTab = ref('lista')

// Permessi: livello area `vendite` + livello oggetto `reso` (fallback ad
// area se il model non e' catalogato, vedi frontend-standards).
useReadonlyMode(READONLY_DOMAINS.VENDITE, READONLY_MODELS.RESO)

// Su 'saved' (patch testata / conferma / annullo / ri-consegna): refresh
// lista + chiude drawer.
async function onDrawerSaved() {
  store.filters.offset = 0
  if (store.hasSearched) await store.fetchList()
  drawer.close()
}

// Dalle code si apre lo stesso drawer reso (riga -> reso_id).
function openReso(resoId) {
  drawer.editRow({ id: resoId }, 'id')
}
</script>

<template>
  <div class="app-page">
    <!-- `lazy`: i pannelli montano solo alla prima attivazione — senza, le
         due code fetcherebbero al load pagina anche se l'utente resta sulla
         lista (PrimeVue 4 monta tutti i TabPanel eager con v-show). -->
    <Tabs v-model:value="activeTab" lazy>
      <TabList>
        <Tab value="lista">{{ t('vendite.resi.tab_lista') }}</Tab>
        <Tab value="da-accreditare">{{ t('vendite.resi.tab_da_accreditare') }}</Tab>
        <Tab value="da-riconsegnare">{{ t('vendite.resi.tab_da_riconsegnare') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="lista">
          <ResiSearchTable
            @row-click="(data) => drawer.editRow(data, 'id')"
          />
        </TabPanel>
        <TabPanel value="da-accreditare">
          <ResiCodaTable coda="accreditare" @apri-reso="openReso" />
        </TabPanel>
        <TabPanel value="da-riconsegnare">
          <ResiCodaTable coda="riconsegnare" @apri-reso="openReso" />
        </TabPanel>
      </TabPanels>
    </Tabs>

    <ResoDrawer
      :visible="drawer.state.visible"
      @update:visible="v => drawer.state.visible = v"
      :reso-id="drawer.state.itemId"
      @saved="onDrawerSaved"
      @cancelled="drawer.close"
    />
  </div>
</template>

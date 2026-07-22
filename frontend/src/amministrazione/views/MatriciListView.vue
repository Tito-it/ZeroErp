<script setup>
// Scopo: Vista contenitore per raggruppare le matrici di configurazione
// dell'amministrazione software in un unico punto di navigazione.
import { useI18n } from 'vue-i18n'
import Tab from 'primevue/tab'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import UtilitiesTipiRuoloListView from './UtilitiesTipiRuoloListView.vue'
import TipiRuoloTipiIndirizzoListView from './TipiRuoloTipiIndirizzoListView.vue'
import CategorieClientiListiniListView from './CategorieClientiListiniListView.vue'

const { t } = useI18n()
</script>

<template>
  <div class="app-page">
    <Tabs value="utilities-ruoli" lazy>
      <TabList>
        <Tab value="utilities-ruoli">{{ t('amministrazione.matrici.tab_utilities_ruoli') }}</Tab>
        <Tab value="indirizzi-ruoli">{{ t('amministrazione.matrici.tab_indirizzi_ruoli') }}</Tab>
        <Tab value="categorie-listini">{{ t('amministrazione.matrici.tab_categorie_listini') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="utilities-ruoli">
          <div class="app-tab-content">
            <UtilitiesTipiRuoloListView />
          </div>
        </TabPanel>
        <TabPanel value="indirizzi-ruoli">
          <div class="app-tab-content">
            <TipiRuoloTipiIndirizzoListView />
          </div>
        </TabPanel>
        <TabPanel value="categorie-listini">
          <div class="app-tab-content">
            <CategorieClientiListiniListView />
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

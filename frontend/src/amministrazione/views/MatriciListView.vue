<script setup>
// Scopo: Vista contenitore per raggruppare le matrici di configurazione
// dell'amministrazione software in un unico punto di navigazione.
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import UtilitiesTipiRuoloListView from './UtilitiesTipiRuoloListView.vue'
import TipiRuoloTipiIndirizzoListView from './TipiRuoloTipiIndirizzoListView.vue'
import CategorieClientiListiniListView from './CategorieClientiListiniListView.vue'

const { t } = useI18n()
const tabViewKey = ref(0)

onMounted(() => {
  // Scopo: forza il ricalcolo dell'ink bar PrimeVue dopo il mount nel layout.
  tabViewKey.value += 1
})
</script>

<template>
  <div class="app-page">
    <TabView lazy :key="tabViewKey">
      <TabPanel :header="t('amministrazione.matrici.tab_utilities_ruoli')">
        <div class="app-tab-content">
          <UtilitiesTipiRuoloListView />
        </div>
      </TabPanel>
      <TabPanel :header="t('amministrazione.matrici.tab_indirizzi_ruoli')">
        <div class="app-tab-content">
          <TipiRuoloTipiIndirizzoListView />
        </div>
      </TabPanel>
      <TabPanel :header="t('amministrazione.matrici.tab_categorie_listini')">
        <div class="app-tab-content">
          <CategorieClientiListiniListView />
        </div>
      </TabPanel>
    </TabView>
  </div>
</template>

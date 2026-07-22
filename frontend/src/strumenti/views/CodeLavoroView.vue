<script setup>
// Scopo: Vista completa «Code di lavoro» (FE-4, brief gestione-code): due tab
//        — coda lavori generica (dbops.coda_lavori, per-utente) e coda stampa
//        (vendite.fatture_stampa_coda, per-emittente). Ogni tab è una lista
//        paginata con filtri; le azioni di governo (annulla/requeue) vivono
//        nel tab coda lavori, sulle sole righe proprie (o con code_manage).
//        Accesso primario dal badge top bar; questa è la via sidebar
//        (Strumenti → Code di lavoro).
import { useI18n } from 'vue-i18n'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import CodaLavoriTab from '../components/CodaLavoriTab.vue'
import CodaStampaTab from '../components/CodaStampaTab.vue'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.STRUMENTI)
</script>

<template>
  <div class="app-page">
    <div class="app-page-toolbar">
      <div class="app-page-filters">
        <h2 style="margin: 0;">{{ t('strumenti.code.page_title') }}</h2>
        <small class="text-color-secondary">{{ t('strumenti.code.page_description') }}</small>
      </div>
      <ReadonlyBadge />
    </div>

    <Tabs value="lavori" lazy class="app-tab-content">
      <TabList>
        <Tab value="lavori">
          <i class="pi pi-inbox" /> {{ t('strumenti.code.tab_lavori') }}
        </Tab>
        <Tab value="stampa">
          <i class="pi pi-print" /> {{ t('strumenti.code.tab_stampa') }}
        </Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="lavori">
          <CodaLavoriTab />
        </TabPanel>
        <TabPanel value="stampa">
          <CodaStampaTab />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

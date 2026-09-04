<script setup>
// Scopo: Vista completa «Code di lavoro» (FE-4, brief gestione-code): due tab
//        — coda lavori generica (dbops.coda_lavori, per-utente) e coda stampa
//        (vendite.fatture_stampa_coda, per-emittente). Ogni tab è una lista
//        paginata con filtri; le azioni di governo (annulla/requeue) vivono
//        nel tab coda lavori, sulle sole righe proprie (o con code_manage).
//        Accesso primario dal badge top bar; questa è la via sidebar
//        (Strumenti → Code di lavoro).
//
// ⭐ Dal 2026-09-04 la scheda attiva è DEEP-LINKABILE (`?tab=lavori|stampa`):
//    il drawer rapido del badge in topbar ha un blocco per coda, e il titolo di
//    ogni blocco apre questa vista GIÀ sulla coda che si stava guardando —
//    prima portava sempre sulla scheda di default.
import { useI18n } from 'vue-i18n'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import ReadonlyBadge from '../../core/components/ReadonlyBadge.vue'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useTabDaQuery } from '../../core/composables/useTabDaQuery'
import { CODE_TABS, READONLY_DOMAINS } from '../../core/constants'
import CodaLavoriTab from '../components/CodaLavoriTab.vue'
import CodaStampaTab from '../components/CodaStampaTab.vue'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.STRUMENTI)

// La scheda attiva, pilotabile da fuori con `?tab=` (il drawer del badge in
// topbar apre la coda su cui si e' cliccato). Guard sulla rotta, pulizia della
// query e i due agganci KeepAlive vivono nel BB.
const activeTab = useTabDaQuery({
  nomeRotta: 'strumenti-code-lavoro',
  ammessi: CODE_TABS,
  iniziale: CODE_TABS.LAVORI,
})
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

    <!-- ⚠️ NIENTE `app-tab-content` sul contenitore <Tabs> (pattern ResiView):
         quella classe, come figlia diretta di .app-page, attiva
         `flex:1; min-height:0; overflow:hidden` — regola pensata per il
         PANNELLO di contenuto, non per il contenitore dei tab. Applicata qui
         faceva prendere tutto lo spazio ai TabPanels, che schiacciavano fuori
         vista la TabList: i tab comparivano al primo paint e sparivano appena
         la tabella si popolava. Sintomo dipendente dai DATI (chi vedeva più
         righe non vedeva più i tab) — bug 2026-07-22. -->
    <Tabs v-model:value="activeTab" lazy>
      <TabList>
        <Tab :value="CODE_TABS.LAVORI">
          <i class="pi pi-inbox" /> {{ t('strumenti.code.tab_lavori') }}
        </Tab>
        <Tab :value="CODE_TABS.STAMPA">
          <i class="pi pi-print" /> {{ t('strumenti.code.tab_stampa') }}
        </Tab>
      </TabList>
      <TabPanels>
        <TabPanel :value="CODE_TABS.LAVORI">
          <CodaLavoriTab />
        </TabPanel>
        <TabPanel :value="CODE_TABS.STAMPA">
          <CodaStampaTab />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

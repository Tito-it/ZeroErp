<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: Vista «Disponibilita'» — due schede sulla stessa domanda, «quanto
//        c'e'»: per (articolo, magazzino), che e' la grana del registro, e per
//        articolo, che e' la somma sui magazzini visibili.
//
// ⚠️ Il permesso e' di AREA (`magazzino`) e lo dichiara la vista, una volta:
//    le due schede leggono la stessa vista `security_invoker` con lo stesso
//    perimetro, non c'e' un livello oggetto da distinguere.
// ⚠️ NIENTE `app-tab-content` sul contenitore <Tabs> (§Pattern Tab-View): su
//    quel contenitore i TabPanels schiaccerebbero la TabList fuori vista
//    appena la tabella si popola — un sintomo che dipende dai DATI.
import { useI18n } from 'vue-i18n'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'

import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { useTabDaQuery } from '../../core/composables/useTabDaQuery'
import { READONLY_DOMAINS } from '../../core/constants'
import DisponibilitaSearchTable from '../components/DisponibilitaSearchTable.vue'
import { TAB_DISPONIBILITA } from '../vocabolari'

const { t } = useI18n()
useReadonlyMode(READONLY_DOMAINS.MAGAZZINO)

// La scheda attiva, pilotabile da fuori con `?tab=`.
const activeTab = useTabDaQuery({
  nomeRotta: 'magazzino-disponibilita',
  ammessi: TAB_DISPONIBILITA,
  iniziale: TAB_DISPONIBILITA.MAGAZZINI,
})
</script>

<template>
  <div class="app-page">
    <!-- `lazy`: i pannelli montano solo alla prima attivazione — senza, le due
         liste partirebbero insieme al primo ingresso. -->
    <Tabs v-model:value="activeTab" lazy>
      <TabList>
        <Tab :value="TAB_DISPONIBILITA.MAGAZZINI">{{ t('magazzino.disponibilita.tab_magazzini') }}</Tab>
        <Tab :value="TAB_DISPONIBILITA.ARTICOLI">{{ t('magazzino.disponibilita.tab_articoli') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel :value="TAB_DISPONIBILITA.MAGAZZINI">
          <DisponibilitaSearchTable :scheda="TAB_DISPONIBILITA.MAGAZZINI" />
        </TabPanel>
        <TabPanel :value="TAB_DISPONIBILITA.ARTICOLI">
          <DisponibilitaSearchTable :scheda="TAB_DISPONIBILITA.ARTICOLI" />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

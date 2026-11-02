<!--
  SPDX-License-Identifier: AGPL-3.0-or-later
  Copyright (C) 2026 Tid (Michele Carlo Titini)
-->
<script setup>
// Scopo: l'area «Accessi» di Amm. Software (brief-db-be-fe-area-accessi, A-1):
//        tre schede che insieme censiscono TUTTE le credenziali, ognuna in una
//        scheda sola — «Operatori» (chi ha la veste operatore, anche con altre
//        vesti), «Altri accessi» (le altre persone, comprese quelle senza
//        alcuna veste), «Di sistema» (le macchine).
// ⭐ La partizione la decide il DB (`script.fn_categoria_accesso`): le tre
//    liste la leggono, nessuna scheda la ricalcola.
// ⭐ La scheda attiva si sceglie anche da fuori con `?tab=` (BB
//    `useTabDaQuery`): il link vecchio `/amm-software/operatori` porta qui,
//    sulla scheda «Operatori».
import { useI18n } from 'vue-i18n'
import Tab from 'primevue/tab'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import Tabs from 'primevue/tabs'
import { useTabDaQuery } from '../../core/composables/useTabDaQuery'
import { ACCESSI_TABS } from '../constants'
import AccessiAltriTab from '../components/AccessiAltriTab.vue'
import AccessiSistemaTab from '../components/AccessiSistemaTab.vue'
import OperatoriListView from './OperatoriListView.vue'

const { t } = useI18n()

const activeTab = useTabDaQuery({
  nomeRotta: 'amm-software-accessi',
  ammessi: ACCESSI_TABS,
  iniziale: ACCESSI_TABS.OPERATORI,
})
</script>

<template>
  <div class="app-page">
    <Tabs v-model:value="activeTab" lazy>
      <TabList>
        <Tab :value="ACCESSI_TABS.OPERATORI">{{ t('amministrazione.accessi.tab_operatori') }}</Tab>
        <Tab :value="ACCESSI_TABS.ALTRI">{{ t('amministrazione.accessi.tab_altri') }}</Tab>
        <Tab :value="ACCESSI_TABS.SISTEMA">{{ t('amministrazione.accessi.tab_sistema') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel :value="ACCESSI_TABS.OPERATORI">
          <div class="app-tab-content">
            <OperatoriListView />
          </div>
        </TabPanel>
        <TabPanel :value="ACCESSI_TABS.ALTRI">
          <AccessiAltriTab />
        </TabPanel>
        <TabPanel :value="ACCESSI_TABS.SISTEMA">
          <AccessiSistemaTab />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

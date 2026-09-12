<script setup>
// Scopo: Vista «Unita' di misura» — contenitore dei tre tab che governano
//        l'impianto delle UdM: le unita', le conversioni fra unita' e le
//        tipologie che le raggruppano.
//
// ⭐ Raggruppate il 2026-09-04 (richiesta di Tid). Erano tre voci di menu
//    separate: le tre tabelle pero' sono UN soggetto solo — un tipo raggruppa
//    le unita', una conversione ne lega due — e nessuna si legge da sola. Sul
//    menu del dominio, inoltre, tre voci su quattro erano impianto delle UdM e
//    l'articolo — il soggetto vero del catalogo — era una voce fra quattro.
//    Precedente identico e gia' in servizio: `IndirizziView` (sette tabelle di
//    configurazione geografica sotto una voce).
//
// ⛔ Questa vista NON dichiara il readonly: lo fa ogni scheda, a livello
//    OGGETTO. Le tre non hanno lo stesso model (`UOM_TIPI` contro
//    `UNITA_MISURA`), quindi un provider unico d'area qui appiattirebbe una
//    granularita' che oggi c'e' — sarebbe una regressione del modello permessi
//    travestita da semplificazione.
//
// ⚠️ NIENTE `app-tab-content` sul contenitore <Tabs> (§Pattern Tab-View): come
//    figlia diretta di `.app-page` quella classe attiva `flex:1; overflow:hidden`
//    ed e' pensata per il PANNELLO — sul contenitore i TabPanels schiacciano
//    fuori vista la TabList appena la tabella si popola. Sintomo dipendente dai
//    DATI: chi vede poche righe non se ne accorge.
import { useI18n } from 'vue-i18n'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import Tab from 'primevue/tab'
import TabPanels from 'primevue/tabpanels'
import TabPanel from 'primevue/tabpanel'
import { useTabDaQuery } from '../../core/composables/useTabDaQuery'
import { UOM_TABS } from '../constants'
import UnitaMisuraTab from '../components/UnitaMisuraTab.vue'
import ConversioniUomTab from '../components/ConversioniUomTab.vue'
import UomTipiTab from '../components/UomTipiTab.vue'

const { t } = useI18n()
// La scheda attiva, pilotabile da fuori con `?tab=`: ci arrivano le due rotte
// di compatibilita' (`/catalogo/conversioni-uom`, `/catalogo/uom-tipi`).
const activeTab = useTabDaQuery({
  nomeRotta: 'catalogo-unita-misura',
  ammessi: UOM_TABS,
  iniziale: UOM_TABS.UNITA,
})
</script>

<template>
  <div class="app-page">
    <Tabs v-model:value="activeTab" lazy>
      <TabList>
        <Tab :value="UOM_TABS.UNITA">{{ t('catalogo.tab_unita_misura') }}</Tab>
        <Tab :value="UOM_TABS.CONVERSIONI">{{ t('catalogo.tab_conversioni_uom') }}</Tab>
        <Tab :value="UOM_TABS.TIPI">{{ t('catalogo.tab_uom_tipi') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel :value="UOM_TABS.UNITA">
          <UnitaMisuraTab />
        </TabPanel>
        <TabPanel :value="UOM_TABS.CONVERSIONI">
          <ConversioniUomTab />
        </TabPanel>
        <TabPanel :value="UOM_TABS.TIPI">
          <UomTipiTab />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

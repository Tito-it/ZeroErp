<script setup>
// Scopo: vista principale Gestione Geografica con 7 tab.
import { ref, onMounted, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useDrawerState } from '../../core/composables/useDrawerState'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import IndirizziSearchTable from '../components/IndirizziSearchTable.vue'
import IndirizzoDrawer from '../components/IndirizzoDrawer.vue'
import ToponomasticaSearchTable from '../../core/components/ToponomasticaSearchTable.vue'
import ToponomasticaDrawer from '../../core/components/ToponomasticaDrawer.vue'
import ComuniSearchTable from '../../core/components/ComuniSearchTable.vue'
import ComuneDrawer from '../../core/components/ComuneDrawer.vue'
import CodiciPostaliSearchTable from '../../core/components/CodiciPostaliSearchTable.vue'
import CodiciPostaliDrawer from '../../core/components/CodiciPostaliDrawer.vue'
import ProvinceSearchTable from '../../core/components/ProvinceSearchTable.vue'
import ProvinceDrawer from '../../core/components/ProvinceDrawer.vue'
import RegioniSearchTable from '../../core/components/RegioniSearchTable.vue'
import RegioniDrawer from '../../core/components/RegioniDrawer.vue'
import StatiSearchTable from '../../core/components/StatiSearchTable.vue'
import StatiDrawer from '../../core/components/StatiDrawer.vue'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'

const { t } = useI18n()
const { isReadonly } = useReadonlyMode(READONLY_DOMAINS.ANAGRAFICHE)
const indDrawer = useDrawerState()
const topoDrawer = useDrawerState()
const comuneDrawer = useDrawerState()
const capDrawer = useDrawerState()
const provDrawer = useDrawerState()
const regDrawer = useDrawerState()
const statoDrawer = useDrawerState()

// Scopo: forza remount TabView dopo mount per ink bar
const tabViewKey = ref(0)
onMounted(() => { nextTick(() => { tabViewKey.value++ }) })
</script>

<template>
  <div class="app-page">
    <TabView lazy :key="tabViewKey">
      <TabPanel :header="t('indirizzi.tab_indirizzi')">
        <IndirizziSearchTable
          @new="indDrawer.openCreate"
          @row-click="(data) => indDrawer.editRow(data, 'indirizzo_dettaglio_id')"
        />
      </TabPanel>

      <TabPanel :header="t('indirizzi.tab_toponomastica')">
        <ToponomasticaSearchTable
          @new="topoDrawer.openCreate"
          @row-click="(data) => topoDrawer.editRow(data)"
        />
      </TabPanel>

      <TabPanel :header="t('indirizzi.tab_comuni')">
        <ComuniSearchTable @new="comuneDrawer.openCreate" />
      </TabPanel>

      <TabPanel :header="t('indirizzi.tab_cap')">
        <CodiciPostaliSearchTable
          @new="capDrawer.openCreate"
          @row-click="(data) => capDrawer.editRow(data)"
        />
      </TabPanel>

      <TabPanel :header="t('geo.tab_province')">
        <ProvinceSearchTable
          @new="provDrawer.openCreate"
          @row-click="(data) => provDrawer.editRow(data)"
        />
      </TabPanel>

      <TabPanel :header="t('geo.tab_regioni')">
        <RegioniSearchTable
          @new="regDrawer.openCreate"
          @row-click="(data) => regDrawer.editRow(data)"
        />
      </TabPanel>

      <TabPanel :header="t('geo.tab_stati')">
        <StatiSearchTable
          @new="statoDrawer.openCreate"
          @row-click="(data) => statoDrawer.editRow(data)"
        />
      </TabPanel>

    </TabView>

    <IndirizzoDrawer
      :visible="indDrawer.state.visible"
      @update:visible="v => indDrawer.state.visible = v"
      :mode="indDrawer.state.mode"
      :item-id="indDrawer.state.itemId"
    />
    <ToponomasticaDrawer
      :visible="topoDrawer.state.visible"
      @update:visible="v => topoDrawer.state.visible = v"
      :mode="topoDrawer.state.mode"
      :item="topoDrawer.state.itemData"
    />
    <ComuneDrawer
      :visible="comuneDrawer.state.visible"
      @update:visible="v => comuneDrawer.state.visible = v"
    />
    <CodiciPostaliDrawer
      :visible="capDrawer.state.visible"
      @update:visible="v => capDrawer.state.visible = v"
      :mode="capDrawer.state.mode"
      :item="capDrawer.state.itemData"
    />
    <ProvinceDrawer
      :visible="provDrawer.state.visible"
      @update:visible="v => provDrawer.state.visible = v"
      :mode="provDrawer.state.mode"
      :item="provDrawer.state.itemData"
    />
    <RegioniDrawer
      :visible="regDrawer.state.visible"
      @update:visible="v => regDrawer.state.visible = v"
      :mode="regDrawer.state.mode"
      :item="regDrawer.state.itemData"
    />
    <StatiDrawer
      :visible="statoDrawer.state.visible"
      @update:visible="v => statoDrawer.state.visible = v"
      :mode="statoDrawer.state.mode"
      :item="statoDrawer.state.itemData"
    />
  </div>
</template>

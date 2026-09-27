<script setup>
// Scopo: Vista contenitore per raggruppare la configurazione documentale
// in un unico punto di navigazione, coerente con amm-software/matrici.
//
// Nota permessi: la navigazione e' nel dominio `config`, ma le entita'
// gestite (template documenti + asset) appartengono allo schema/area
// `documenti`. Il route guard valuta solo `meta.domain` (config) e quindi
// non blocca utenti con `documenti=BLOCCATO`. Il check qui sotto chiude
// la falla mostrando StatusPage forbidden invece di una pagina vuota
// con errori 403 al primo POST.
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { READONLY_DOMAINS, STATUS_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import Tab from 'primevue/tab'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import StatusPage from '../../core/components/StatusPage.vue'
import ModelliDocumentiTemplatesView from './ModelliDocumentiTemplatesView.vue'
import ModelliDocumentiAssetView from './ModelliDocumentiAssetView.vue'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

const isDocumentiBlocked = computed(() =>
  auth.isAreaBlocked(READONLY_DOMAINS.DOCUMENTI),
)
</script>

<template>
  <div class="app-page">
    <StatusPage
      v-if="isDocumentiBlocked"
      :icon="STATUS_ICONS.VIETATO"
      :title="t('errors.forbidden_title')"
      :message="t('errors.forbidden_message')"
      :action-label="t('errors.back_home')"
      :action-icon="NAV_ICONS.HOME"
      @action="router.push('/')"
    />
    <Tabs v-else value="modelli" lazy>
      <TabList>
        <Tab value="modelli">{{ t('config.documenti.tab_modelli') }}</Tab>
        <Tab value="asset">{{ t('config.documenti.tab_asset') }}</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="modelli">
          <div class="app-tab-content">
            <ModelliDocumentiTemplatesView />
          </div>
        </TabPanel>
        <TabPanel value="asset">
          <div class="app-tab-content">
            <ModelliDocumentiAssetView />
          </div>
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

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
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { READONLY_DOMAINS } from '../../core/constants'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import StatusPage from '../../core/components/StatusPage.vue'
import ModelliDocumentiTemplatesView from './ModelliDocumentiTemplatesView.vue'
import ModelliDocumentiAssetView from './ModelliDocumentiAssetView.vue'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const tabViewKey = ref(0)

const isDocumentiBlocked = computed(() =>
  auth.isAreaBlocked(READONLY_DOMAINS.DOCUMENTI),
)

onMounted(() => {
  // Scopo: forza il ricalcolo dell'ink bar PrimeVue dopo il mount nel layout.
  tabViewKey.value += 1
})
</script>

<template>
  <div class="app-page">
    <StatusPage
      v-if="isDocumentiBlocked"
      icon="pi pi-lock"
      :title="t('errors.forbidden_title')"
      :message="t('errors.forbidden_message')"
      :action-label="t('errors.back_home')"
      action-icon="pi pi-home"
      @action="router.push('/')"
    />
    <TabView v-else lazy :key="tabViewKey">
      <TabPanel :header="t('config_documenti.tab_modelli')">
        <div class="app-tab-content">
          <ModelliDocumentiTemplatesView />
        </div>
      </TabPanel>
      <TabPanel :header="t('config_documenti.tab_asset')">
        <div class="app-tab-content">
          <ModelliDocumentiAssetView />
        </div>
      </TabPanel>
    </TabView>
  </div>
</template>

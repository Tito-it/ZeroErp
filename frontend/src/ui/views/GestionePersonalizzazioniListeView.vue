<script setup>
// Scopo: Pagina contenitore "Gestione personalizzazioni liste".
//        Esposta sotto /config/personalizzazioni-liste, configurazione
//        operativa accessibile a tenant admin con almeno una delle
//        2 azioni di processo o a SUPER_ADMIN (bypass).
//
//        Header: Select "Lista corrente" condiviso da tutti i tab.
//        Tabs lazy con tab condizionali alle azioni:
//          - Preset           (azione `ui_preset_manage`)
//          - Permessi colonne (azione `ui_permesso_manage`)
//
//        Note sui tab Fase 2 (Definizioni + Catalogo colonne):
//        sono "amministrazione tecnica" e atterreranno in una view
//        dedicata sotto /amm-software/personalizzazioni-liste-tecniche
//        quando i CRUD su `lista_definizione` / `lista_colonna` saranno
//        operativi. In Fase 1 quei CRUD restano gestiti via seed CSV,
//        quindi la pagina admin amm-software non esiste ancora.
//
//        Schema BE coinvolto: `ui` (skip_area_check). Il check accesso
//        e' sulle 2 azioni di processo o SUPER_ADMIN.
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import Tab from 'primevue/tab'
import Tabs from 'primevue/tabs'
import TabList from 'primevue/tablist'
import TabPanel from 'primevue/tabpanel'
import TabPanels from 'primevue/tabpanels'
import StatusPage from '../../core/components/StatusPage.vue'
import { useAuthStore } from '../../stores/auth'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS, STATUS_ICONS } from '../../core/constants'
import { NAV_ICONS } from '../../core/navigation'
import ListaCorrenteSelect from '../components/ListaCorrenteSelect.vue'
import ListaPresetPanel from '../components/ListaPresetPanel.vue'
import ListaColonnaPermessoPanel from '../components/ListaColonnaPermessoPanel.vue'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()

// Provider readonly. Le entita' gestite sono in schema `ui`
// (skip_area_check), ma la pagina vive sotto config: per coerenza
// del badge sola lettura usiamo l'area `config`.
useReadonlyMode(READONLY_DOMAINS.CONFIG)

const canManagePreset = computed(
  () => auth.isSuperAdmin || auth.isActionAllowed('ui_preset_manage'),
)
const canManagePermesso = computed(
  () => auth.isSuperAdmin || auth.isActionAllowed('ui_permesso_manage'),
)
const canAccess = computed(
  () => canManagePreset.value || canManagePermesso.value,
)

// Tab attivo. I due tab sono CONDIZIONALI ai permessi: un valore fisso
// ('preset') lascerebbe senza pannello chi ha solo `ui_permesso_manage`.
// TabView v3 attivava da se' il primo pannello reso, `Tabs` v4 no — il
// default va quindi calcolato sul primo tab effettivamente presente.
// Scelta utente (`tabScelto`) e default convivono: il ref parte null e
// il getter cade sul primo tab disponibile finche' l'utente non sceglie,
// cosi' il valore resta corretto anche se i permessi arrivano async.
const primoTabDisponibile = computed(() =>
  canManagePreset.value ? 'preset' : 'permessi',
)
const tabScelto = ref(null)
const activeTab = computed({
  get: () => tabScelto.value ?? primoTabDisponibile.value,
  set: (v) => { tabScelto.value = v },
})
</script>

<template>
  <div class="app-page">
    <StatusPage
      v-if="!canAccess"
      :icon="STATUS_ICONS.VIETATO"
      :title="t('errors.forbidden_title')"
      :message="t('errors.forbidden_message')"
      :action-label="t('errors.back_home')"
      :action-icon="NAV_ICONS.HOME"
      @action="router.push('/')"
    />

    <template v-else>
      <div class="ui-admin-header">
        <h2 class="ui-admin-title">{{ t('ui.admin.titolo') }}</h2>
        <ListaCorrenteSelect />
      </div>

      <Tabs v-model:value="activeTab" lazy>
        <TabList>
          <Tab v-if="canManagePreset" value="preset">{{ t('ui.admin.tab_preset') }}</Tab>
          <Tab v-if="canManagePermesso" value="permessi">{{ t('ui.admin.tab_permessi') }}</Tab>
        </TabList>
        <TabPanels>
          <TabPanel v-if="canManagePreset" value="preset">
            <ListaPresetPanel />
          </TabPanel>
          <TabPanel v-if="canManagePermesso" value="permessi">
            <ListaColonnaPermessoPanel />
          </TabPanel>
        </TabPanels>
      </Tabs>
    </template>
  </div>
</template>

<style scoped>
.ui-admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0.5rem 0 0.75rem;
  border-bottom: 1px solid var(--app-drawer-section-border, transparent);
}
.ui-admin-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}
.ui-admin-placeholder {
  padding: 2rem;
  text-align: center;
  color: var(--app-text-muted);
  font-style: italic;
}
</style>

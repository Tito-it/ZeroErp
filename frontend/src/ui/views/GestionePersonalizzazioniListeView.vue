<script setup>
// Scopo: Pagina contenitore "Gestione personalizzazioni liste".
//        Esposta sotto /config/personalizzazioni-liste, configurazione
//        operativa accessibile a tenant admin con almeno una delle
//        2 azioni di processo o a SUPER_ADMIN (bypass).
//
//        Header: Select "Lista corrente" condiviso da tutti i tab.
//        TabView lazy con tab condizionali alle azioni:
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
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import StatusPage from '../../core/components/StatusPage.vue'
import { useAuthStore } from '../../stores/auth'
import { useReadonlyMode } from '../../core/composables/useReadonlyMode'
import { READONLY_DOMAINS } from '../../core/constants'
import ListaCorrenteSelect from '../components/ListaCorrenteSelect.vue'
import ListaPresetPanel from '../components/ListaPresetPanel.vue'
import ListaColonnaPermessoPanel from '../components/ListaColonnaPermessoPanel.vue'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const tabViewKey = ref(0)

// Provider readonly. Le entita' gestite sono in schema `ui`
// (skip_area_check), ma la pagina vive sotto config: per coerenza
// del badge sola lettura usiamo l'area `config`.
useReadonlyMode(READONLY_DOMAINS.CONFIG)

const canManagePreset = computed(
  () => auth.isAdmin || auth.isActionAllowed('ui_preset_manage'),
)
const canManagePermesso = computed(
  () => auth.isAdmin || auth.isActionAllowed('ui_permesso_manage'),
)
const canAccess = computed(
  () => canManagePreset.value || canManagePermesso.value,
)

onMounted(() => {
  tabViewKey.value += 1
})
</script>

<template>
  <div class="app-page">
    <StatusPage
      v-if="!canAccess"
      icon="pi pi-lock"
      :title="t('errors.forbidden_title')"
      :message="t('errors.forbidden_message')"
      :action-label="t('errors.back_home')"
      action-icon="pi pi-home"
      @action="router.push('/')"
    />

    <template v-else>
      <div class="ui-admin-header">
        <h2 class="ui-admin-title">{{ t('ui_admin.titolo') }}</h2>
        <ListaCorrenteSelect />
      </div>

      <TabView v-if="canAccess" lazy :key="tabViewKey">
        <TabPanel v-if="canManagePreset" :header="t('ui_admin.tab_preset')">
          <ListaPresetPanel />
        </TabPanel>
        <TabPanel v-if="canManagePermesso" :header="t('ui_admin.tab_permessi')">
          <ListaColonnaPermessoPanel />
        </TabPanel>
      </TabView>
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

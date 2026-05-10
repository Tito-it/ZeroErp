<script setup>
// Scopo: Pagina tecnica "Personalizzazioni Liste — Tecnica" (Blocco F
//        Fase 2 — DEF-5b). SUPER_ADMIN-only: i CRUD operano su
//        `ui.lista_definizione` e `ui.lista_colonna`, schema tecnico
//        che richiede coordinamento con il team DB per le viste SQL.
//
//        Header: Select "Lista corrente" condiviso (usato dal tab
//        "Catalogo colonne" come master, ignorato dal tab "Definizioni"
//        che e' una lista globale). All'apertura ricarico le definizioni
//        del Select per assicurare freschezza dopo CRUD.
//
//        TabView lazy con due tab:
//          - Definizioni       (CRUD `ui.lista_definizione`)
//          - Catalogo colonne  (CRUD `ui.lista_colonna`, master = lista
//                               corrente)
//
//        Differenza vs `GestionePersonalizzazioniListeView` (Fase 1
//        sotto /config/...): qui niente azioni di processo, solo
//        SUPER_ADMIN. La voce sidebar e' `adminOnly: true`.
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import TabView from 'primevue/tabview'
import TabPanel from 'primevue/tabpanel'
import StatusPage from '../../core/components/StatusPage.vue'
import { useAuthStore } from '../../stores/auth'
import ListaCorrenteSelect from '../components/ListaCorrenteSelect.vue'
import ListaDefinizionePanel from '../components/ListaDefinizionePanel.vue'
import ListaColonnaPanel from '../components/ListaColonnaPanel.vue'
import { useUiAdminStore } from '../stores/uiAdmin'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const uiAdmin = useUiAdminStore()
const tabViewKey = ref(0)

const canAccess = computed(() => auth.isAdmin)

onMounted(() => {
  tabViewKey.value += 1
})

// Scopo: Quando una definizione viene creata/aggiornata/eliminata,
//        ricarico l'elenco del Select header per non lasciare voci
//        stale nel selettore "Lista corrente" condiviso col tab
//        catalogo colonne.
async function onDefinizioneChanged() {
  // Force reload del lookup Select header: una definizione disattivata
  // o eliminata deve sparire dal selettore "Lista corrente" condiviso
  // col tab Catalogo colonne.
  await uiAdmin.loadListe(true)
}
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
      <div class="ui-admin-tecnica-header">
        <h2 class="ui-admin-tecnica-title">{{ t('ui_admin.tecnica_titolo') }}</h2>
        <ListaCorrenteSelect />
      </div>

      <TabView lazy :key="tabViewKey">
        <TabPanel :header="t('ui_admin.tab_definizioni')">
          <ListaDefinizionePanel @definizione-changed="onDefinizioneChanged" />
        </TabPanel>
        <TabPanel :header="t('ui_admin.tab_catalogo_colonne')">
          <ListaColonnaPanel />
        </TabPanel>
      </TabView>
    </template>
  </div>
</template>

<style scoped>
.ui-admin-tecnica-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  padding: 0.5rem 0 0.75rem;
  border-bottom: 1px solid var(--app-drawer-section-border, transparent);
}
.ui-admin-tecnica-title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 600;
}
</style>

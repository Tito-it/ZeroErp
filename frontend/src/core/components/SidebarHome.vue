<script setup>
// Scopo: stato HOME della sidebar morfica — lista domini con icone.
// Click su un dominio imposta il dominio attivo e naviga alla pagina default.
//
// Preferiti: la lista preferiti NON sta più nella sidebar HOME. È accessibile
// dal kebab "preferenze utente" nella topbar (subito prima del logout, vedi
// AppTopbar.vue) e dal pannello tile in HomeView.
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import { useNavigationStore } from '../../stores/navigation'
import { HOME_ITEM } from '../navigation'
import SidebarItem from './SidebarItem.vue'

const { t } = useI18n()
const router = useRouter()
const auth = useAuthStore()
const nav = useNavigationStore()

const emit = defineEmits(['navigate'])

function handleDomainClick(domain) {
  if (nav.currentDomain === domain.key) {
    emit('navigate')
    return
  }
  nav.setDomain(domain.key)
  const defaultRoute = nav.getDefaultRoute(domain.key)
  if (defaultRoute) {
    router.push(defaultRoute)
  }
  // Se il dominio non ha voci menu, non navigare — la sidebar mostrera' il dominio vuoto
  emit('navigate')
}

function handleHomeClick() {
  nav.clearDomain()
  router.push(HOME_ITEM.to)
  emit('navigate')
}
</script>

<template>
  <div class="sidebar-home">
    <!-- Link diretto alla Home -->
    <SidebarItem
      :icon="HOME_ITEM.icon"
      :label="t('nav.home')"
      class="home-link"
      @click="handleHomeClick"
    />

    <div class="sidebar-divider"></div>

    <!-- Lista domini -->
    <SidebarItem
      v-for="domain in auth.visibleDomains"
      :key="domain.key"
      :icon="domain.icon"
      :label="t(`nav.${domain.key}`)"
      :active="nav.currentDomain === domain.key"
      @click="handleDomainClick(domain)"
    />
  </div>
</template>

<style scoped>
.sidebar-home {
  display: flex;
  flex-direction: column;
  gap: var(--app-sidebar-item-gap);
}
</style>

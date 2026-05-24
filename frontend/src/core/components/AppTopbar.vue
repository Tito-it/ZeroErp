<script setup>
// Scopo: topbar principale — emittente, area title, context chip, ricerca, user badge, data, logout.
// Su mobile mostra hamburger per aprire il drawer sidebar.
// Su schermi piccoli raggruppa dark/search/AI/lingua in un menu kebab (3 puntini).
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import Menu from 'primevue/menu'
import { useAuthStore } from '../../stores/auth'
import { useUiStore } from '../../stores/ui'
import { useContextStore } from '../../stores/context'
import { resolveTabLabel } from '../navigation'
import { getAIStatus } from '../api/ai-api'
import { setAppLanguage, SUPPORTED_LOCALES } from '../i18n'
import SearchDrawer from './SearchDrawer.vue'
import AiAssistantDrawer from './AiAssistantDrawer.vue'
import { menuItemClass } from '../utils/rowActions'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()
const context = useContextStore()

defineProps({
  showHamburger: { type: Boolean, default: false }
})
const emit = defineEmits(['toggle-menu'])

const areaTitle = computed(() => {
  return resolveTabLabel(route.meta, t) || ''
})

const companyName = computed(() => {
  // Per operatori e admin di emittente: identita 1-a-1 dal nuovo getter.
  // Per admin globali: leggiamo direttamente dal blocco emittente del
  // profilo (cascata 4b: gestore globale) come display informativo.
  if (auth.emittenteCorrente) {
    return auth.emittenteCorrente.ragioneSociale || ''
  }
  const em = auth.user?.emittente
  return em?.ragione_sociale_completa || em?.emittente_descrizione || ''
})

const formattedDate = computed(() => {
  const now = new Date()
  return now.toLocaleDateString(locale.value === 'it' ? 'it-IT' : 'en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric'
  })
})

// Iniziali utente (max 2 caratteri) per il badge non-admin
const userInitials = computed(() => {
  if (!auth.user) return '?'
  const soggetto = auth.user.soggetto
  if (soggetto?.nome && soggetto?.cognome) {
    return (soggetto.nome[0] + soggetto.cognome[0]).toUpperCase()
  }
  const utente = auth.user.utente
  if (utente?.first_name && utente?.last_name) {
    return (utente.first_name[0] + utente.last_name[0]).toUpperCase()
  }
  if (utente?.username) return utente.username.substring(0, 2).toUpperCase()
  return '?'
})

async function handleLogout() {
  await auth.logout()
  router.push('/login')
}

// Scopo: switch lingua IT/EN. Toggle sulla prossima locale supportata in
//        SUPPORTED_LOCALES; persistita in localStorage da setAppLanguage.
//        Le prossime chiamate axios invieranno Accept-Language aggiornato
//        (interceptor in core/api.js) che popola la GUC `myapp.user_language`.
function toggleLanguage() {
  const idx = SUPPORTED_LOCALES.indexOf(locale.value)
  const next = SUPPORTED_LOCALES[(idx + 1) % SUPPORTED_LOCALES.length]
  setAppLanguage(next)
}

const languageLabel = computed(() => locale.value.toUpperCase())
const languageTooltip = computed(() => {
  // Mostra "EN" se la lingua corrente è IT (e viceversa) per spiegare
  // su cosa si passerà al click.
  const next = SUPPORTED_LOCALES.find(l => l !== locale.value) || locale.value
  return `${t('common.switch_language')} · ${next.toUpperCase()}`
})

// Scopo: menu kebab per schermi piccoli. Raggruppa dark/ricerca/AI/lingua.
//        Il trigger è visibile solo su mobile (CSS @media <= 767px);
//        i pulsanti singoli sono nascosti alla stessa soglia.
const kebabMenu = ref(null)
// Scopo: voci kebab topbar. Tutte neutre/preferenze (dark/search/AI/lingua),
// nessuna severity esplicita -> fallback "action" (verde) coerente con il
// colore dei pulsanti inline `.topbar-icon-btn` (--p-primary-color).
const TOPBAR_MENU_CLASS = menuItemClass(undefined, 'app-menu-item-action')
const kebabItems = computed(() => {
  const items = [
    {
      label: ui.isDark ? t('common.light_mode') : t('common.dark_mode'),
      icon: ui.isDark ? 'pi pi-sun' : 'pi pi-moon',
      class: TOPBAR_MENU_CLASS,
      command: () => ui.toggleDarkMode()
    },
    {
      label: t('context.tooltip_search'),
      icon: 'pi pi-search',
      class: TOPBAR_MENU_CLASS,
      command: () => ui.openSearchDrawer()
    }
  ]
  if (ui.aiAvailable) {
    items.push({
      label: t('ai.title'),
      icon: 'pi pi-microchip-ai',
      class: TOPBAR_MENU_CLASS,
      command: () => ui.toggleAiDrawer()
    })
  }
  items.push({
    label: `${t('common.language')} · ${languageLabel.value}`,
    icon: 'pi pi-globe',
    class: TOPBAR_MENU_CLASS,
    command: () => toggleLanguage()
  })
  return items
})

function toggleKebab(event) {
  kebabMenu.value?.toggle(event)
}

// Scopo: Verifica disponibilita' AI al mount (best-effort, non blocca).
//        Solo se l'utente e' autenticato, per evitare 401 inutili.
onMounted(async () => {
  if (!auth.isAuthenticated) return
  try {
    const response = await getAIStatus()
    ui.aiAvailable = response.data?.data?.enabled === true
  } catch {
    ui.aiAvailable = false
  }
})
</script>

<template>
  <header class="app-topbar">
    <div class="topbar-left">
      <!-- Hamburger su mobile -->
      <Button
        v-if="showHamburger"
        icon="pi pi-bars"
        text
        rounded
        size="small"
        class="topbar-hamburger"
        @click="emit('toggle-menu')"
      />
      <i v-else class="pi pi-building"></i>
      <span v-if="companyName" class="topbar-company">{{ companyName }}</span>
    </div>

    <div class="topbar-center">
      <span class="topbar-area-title">{{ areaTitle }}</span>
    </div>

    <div class="topbar-right">
      <!-- Chip contesto globale -->
      <Chip
        v-if="context.hasContext"
        :label="context.contextLabel"
        removable
        class="context-chip"
        @remove="context.clearContext()"
      >
        <template #default>
          <i :class="context.contextIcon" class="context-chip-icon" />
          <span class="context-chip-label">{{ context.contextLabel }}</span>
        </template>
      </Chip>

      <!-- Gruppo azioni inline — nascosto su mobile (vedi media query) -->
      <div class="topbar-actions-inline">
        <!-- Toggle dark/light mode -->
        <button
          class="topbar-icon-btn"
          v-tooltip.bottom="ui.isDark ? t('common.light_mode') : t('common.dark_mode')"
          @click="ui.toggleDarkMode()"
        >
          <i :class="ui.isDark ? 'pi pi-sun' : 'pi pi-moon'"></i>
        </button>

        <!-- Pulsante ricerca universale -->
        <button
          class="topbar-icon-btn"
          v-tooltip.bottom="t('context.tooltip_search')"
          @click="ui.openSearchDrawer()"
        >
          <i class="pi pi-search"></i>
        </button>

        <!-- Pulsante assistente AI — visibile solo se AI disponibile -->
        <button
          v-if="ui.aiAvailable"
          class="topbar-icon-btn"
          v-tooltip.bottom="`${t('ai.title')} (Ctrl+.)`"
          @click="ui.toggleAiDrawer()"
        >
          <i class="pi pi-microchip-ai"></i>
        </button>

        <!-- Switch lingua IT/EN -->
        <button
          class="topbar-icon-btn topbar-lang-btn"
          v-tooltip.bottom="languageTooltip"
          @click="toggleLanguage()"
        >
          <span class="topbar-lang-label">{{ languageLabel }}</span>
        </button>
      </div>

      <!-- Menu kebab (3 puntini) — visibile solo su mobile -->
      <button
        class="topbar-icon-btn topbar-kebab-btn"
        v-tooltip.bottom="t('common.more_options')"
        @click="toggleKebab"
        aria-haspopup="true"
      >
        <i class="pi pi-ellipsis-v"></i>
      </button>
      <Menu ref="kebabMenu" :model="kebabItems" popup class="topbar-kebab-menu" />

      <!-- Badge SUPER_ADMIN o iniziali utente -->
      <Chip v-if="auth.isSuperAdmin" class="admin-chip" v-tooltip.bottom="auth.displayName">
        <template #default>
          <i class="pi pi-shield admin-chip-icon" />
          <span class="admin-chip-label">{{ t('auth.super_admin_badge') }}</span>
        </template>
      </Chip>
      <span v-else class="user-initials-badge" v-tooltip.bottom="auth.displayName">
        {{ userInitials }}
      </span>

      <span class="topbar-date">{{ formattedDate }}</span>

      <!-- Logout -->
      <button
        class="topbar-icon-btn topbar-logout-btn"
        v-tooltip.bottom="t('auth.logout')"
        @click="handleLogout"
      >
        <i class="pi pi-sign-out"></i>
      </button>
    </div>
  </header>

  <SearchDrawer v-model:visible="ui.searchDrawerVisible" />
  <AiAssistantDrawer v-model:visible="ui.aiDrawerVisible" />
</template>

<style scoped>
.app-topbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  height: var(--app-topbar-height);
  min-height: var(--app-topbar-height);
  padding: 0 var(--app-content-padding);
  background: var(--app-topbar-bg);
  border-bottom: 1px solid var(--app-topbar-border);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.topbar-left i {
  font-size: 0.9rem;
  color: var(--app-icon-color);
}

.topbar-hamburger {
  color: var(--app-topbar-breadcrumb-color);
}

.topbar-company {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.topbar-center {
  display: flex;
  align-items: center;
  justify-content: center;
}

.topbar-area-title {
  font-size: var(--app-font-size-base);
  font-weight: 500;
  color: var(--app-topbar-breadcrumb-active-color);
  white-space: nowrap;
}

.topbar-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  font-size: var(--app-font-size-sm);
  color: var(--app-topbar-breadcrumb-color);
}

.topbar-date {
  white-space: nowrap;
}

/* Gruppo azioni inline (dark/search/AI/lingua). Su mobile collassa nel menu kebab. */
.topbar-actions-inline {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

/* Kebab menu — visibile solo su mobile (inverso di .topbar-actions-inline).
   Selettore combinato .topbar-icon-btn.topbar-kebab-btn per specificita` piu`
   alta di .topbar-icon-btn singolo (altrimenti display: flex di quest'ultimo,
   dichiarato dopo, sovrascriverebbe display: none). */
.topbar-icon-btn.topbar-kebab-btn {
  display: none;
}

/* Switch lingua — mostra label testuale (IT/EN) anziche' icona */
.topbar-lang-btn {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.03em;
}

.topbar-lang-label {
  line-height: 1;
}

/* Bottone icona topbar — classe riutilizzabile per search, AI, logout */
.topbar-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.85rem;
  height: 1.85rem;
  font-size: 0.95rem;
  color: var(--p-primary-color);
  background: transparent;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: color var(--app-transition-fast), background var(--app-transition-fast);
}

.topbar-icon-btn:hover {
  color: var(--p-primary-700);
  background: var(--p-primary-50);
}

/* Chip contesto globale */
.context-chip {
  cursor: default;
  font-size: var(--app-font-size-sm);
}

.context-chip-icon {
  margin-right: 0.35rem;
  font-size: 0.8rem;
  color: var(--p-primary-color);
}

.context-chip-label {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  color: var(--p-primary-color);
}

/* Badge admin */
.admin-chip {
  cursor: default;
  font-size: var(--app-font-size-sm);
  background: color-mix(in srgb, var(--p-orange-500) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--p-orange-500) 30%, transparent);
  padding: 0.15rem 0.5rem;
}

.admin-chip-icon {
  font-size: 0.8rem;
  color: var(--p-orange-500);
}

.admin-chip-label {
  margin-left: 0.3rem;
  font-weight: 600;
  color: var(--p-orange-500);
}

/* Logout — override hover rosso (usa topbar-icon-btn come base) */
.topbar-logout-btn:hover {
  color: var(--p-red-500);
  background: var(--p-red-50);
}

/* Badge iniziali utente (non-admin) — sfondo celeste pastello */
.user-initials-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.75rem;
  height: 1.75rem;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--p-blue-600);
  background: var(--p-blue-50);
  border: 1px solid var(--p-blue-200);
  border-radius: 50%;
  cursor: default;
  user-select: none;
}

/* Mobile — nasconde data, azienda, azioni inline; mostra solo il kebab */
@media (max-width: 767px) {
  .topbar-company,
  .topbar-date {
    display: none;
  }

  .topbar-left i.pi-building {
    display: none;
  }

  .context-chip-label {
    max-width: 120px;
  }

  .admin-chip-label {
    display: none;
  }

  .admin-chip {
    padding: 0.15rem 0.35rem;
  }

  /* Collassa dark/search/AI/lingua nel menu kebab */
  .topbar-actions-inline {
    display: none;
  }

  /* Selettore specifico: vedi commento sopra su specificity ordering */
  .topbar-icon-btn.topbar-kebab-btn {
    display: flex;
  }
}

/* Tablet — il nome azienda si tronca con ellipsis */
@media (max-width: 1024px) and (min-width: 768px) {
  .topbar-company {
    max-width: 120px;
  }

  .context-chip-label {
    max-width: 120px;
  }
}
</style>

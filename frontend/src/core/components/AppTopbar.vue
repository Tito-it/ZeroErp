<script setup>
// Scopo: topbar principale — emittente, area title, context chip, badge
// utente, data, ricerca, AI assistant, kebab preferenze utente (preferiti +
// lingua + dark mode), logout. Su mobile mostra hamburger per aprire il
// drawer sidebar; ricerca+AI inline scompaiono e si promuovono come prime
// voci nello stesso kebab utente — un solo kebab per tutto.
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import Badge from 'primevue/badge'
import Chip from 'primevue/chip'
import TieredMenu from 'primevue/tieredmenu'
import { useAuthStore } from '../../stores/auth'
import { useUiStore } from '../../stores/ui'
import { useContextStore } from '../../stores/context'
import { DOMAINS, NAV_ICONS } from '../navigation'
import { getAIStatus } from '../api/ai-api'
import { setAppLanguage, SUPPORTED_LOCALES, intlLocale } from '../i18n'
import { MANAGE_ICONS, PROCESSI_TABS, READONLY_DOMAINS, STATUS_ICONS } from '../constants'
import SearchDrawer from './SearchDrawer.vue'
import AiAssistantDrawer from './AiAssistantDrawer.vue'
import CodeLavoroDrawer from './CodeLavoroDrawer.vue'
import EmittenteAttivoSelect from './EmittenteAttivoSelect.vue'
import SchedaUtentePopover from './SchedaUtentePopover.vue'
import { menuItemClass } from '../utils/rowActions'
import { useNavigationFavorites } from '../composables/useNavigationFavorites'
import { useQueueCountsPolling } from '../composables/useQueueCountsPolling'
import { usePresidiPolling } from '../composables/usePresidiPolling'
import { displayTime, displayOggiEsteso } from '../utils/date'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const ui = useUiStore()

// ⚠️ La ricerca si MONTA alla prima apertura, non con la topbar: legge le
//    misure di pagina (BB `core/misurePagina`) quando nasce, e la topbar sta
//    anche su pagine dove le misure non ci sono — la 404 o la forbidden di una
//    veste che non e' l'operatore, per cui il guard non le carica. Dopo la
//    prima apertura resta montata (la chiusura anima e lo stato si conserva).
const ricercaMontata = ref(false)
watch(() => ui.searchDrawerVisible, (aperta) => { if (aperta) ricercaMontata.value = true }, { immediate: true })
const context = useContextStore()
// La scheda dell'utente (badge): `toggle(event)`.
const schedaUtente = ref(null)

defineProps({
  showHamburger: { type: Boolean, default: false }
})
const emit = defineEmits(['toggle-menu'])

// Scopo: il titolo al centro della topbar e' L'AREA (il dominio della rotta),
//        con la sua icona — non la pagina.
// ⭐ Decisione di Tid, 2026-09-19: fino a quel giorno qui stava
//    `resolveTabLabel(route.meta)`, cioe' la stessa etichetta della scheda
//    attiva e dell'ultimo segmento del breadcrumb — «Contratti» tre volte in
//    verticale, e la topbar era l'unica delle tre che non aggiungeva niente.
//    Il dominio invece risponde a «in quale area sono», che a sidebar chiusa
//    (o su mobile) non lo dice nessun altro pezzo: topbar = area, scheda =
//    pagina, breadcrumb = il percorso intero.
// ⚠️ Segue la `route`, cioe' il pannello PRIMARIO: in split view il secondario
//    puo' essere di un altro dominio, e questo titolo — come il breadcrumb —
//    non lo racconta. E' coerenza, non dimenticanza.
// ⚠️ `home` (compresi «non trovato» e «vietato», che sono rotte di `home`) e
//    un `domain` assente danno «Home» con l'icona di casa: la chiave `nav.home`
//    esiste, e un titolo vuoto in cima sembrerebbe un errore di caricamento.
const areaDominio = computed(() => {
  const key = route.meta.domain || 'home'
  const dominio = DOMAINS.find(d => d.key === key)
  return {
    label: t(`nav.${key}`),
    icon: dominio?.icon ?? NAV_ICONS.HOME,
  }
})

// Il nome dell'emittente non e' piu' un computed di questo componente: dal
// 2026-08-04 lo rende `EmittenteAttivoSelect`, che per chi PUO' scegliere e'
// una combo (impersonazione di scope) e per l'operatore resta il testo di
// prima. Il vecchio fallback sul «gestore globale» del profilo e' caduto con
// esso: l'admin globale ora sceglie un emittente vero, non ne guarda uno
// informativo che non corrispondeva a cio' che stava usando.

// La data di OGGI dell'azienda, non del PC (T-1): la sede e' `date.js`.
const formattedDate = computed(() => displayOggiEsteso(intlLocale(locale.value)))

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
async function toggleLanguage() {
  const idx = SUPPORTED_LOCALES.indexOf(locale.value)
  const next = SUPPORTED_LOCALES[(idx + 1) % SUPPORTED_LOCALES.length]
  // setAppLanguage e' async: carica il chunk della locale prima di
  // attivarla (la prima volta che si passa a EN scarica en.json).
  await setAppLanguage(next)
}

const languageLabel = computed(() => locale.value.toUpperCase())

// Badge code di lavoro (D-B/D-C brief gestione-code): due segmenti — job vivi
// della coda lavori (propri) e stampe vive (per emittente). Polling lento 60s
// sospeso in background. ⭐ Solo per chi ha l'area `strumenti` (la porta
// dell'endpoint, `area_funzionale = "strumenti"`): gli altri non lo chiamano,
// invece di lasciare un permesso negato nel log di sicurezza a ogni accesso.
const {
  lavoriVivi, stampaVive, workerOk,
  disponibile: codeDisponibile,
} = useQueueCountsPolling({ ammesso: () => !auth.isAreaBlocked(READONLY_DOMAINS.STRUMENTI) })

// Il pallino dei presidi (decisione #8 di Tid, 2026-09-18): accanto al badge
// code perche' e' lo stesso genere di segnale — contatore ambientale sul
// SISTEMA, non «notifiche per te». Sempre visibile per chi passa la porta (SUPER_ADMIN: detto prima della chiamata),
// verde a zero (la giornaliera muta non sa dirlo), rosso col numero; click →
// «Processi automatici». Cadenza e politica sugli errori nel composable.
const {
  pallino: presidiPallino,
  lettoAlle: presidiLettoAlle,
  disponibile: presidiDisponibile,
} = usePresidiPolling({ ammesso: () => auth.isSuperAdmin })

const presidiTooltip = computed(() => {
  const p = presidiPallino.value
  if (!p) return t('amministrazione.processi.presidi_badge_attesa')
  const ora = displayTime(presidiLettoAlle.value)
  return p.ok
    ? t('amministrazione.processi.presidi_badge_tooltip_ok', { ora })
    : t('amministrazione.processi.presidi_badge_tooltip', {
        allarmi: p.allarmi, non_letti: p.nonLetti, ora,
      })
})

// ⭐ Il pallino porta GIÀ sulla scheda dei presidi: chi ci clicca ha visto
//    qualcosa di acceso, e la lista dei processi non è la sua notizia.
function apriProcessiAutomatici() {
  router.push({
    name: 'strumenti-diagnostica-processi-automatici',
    query: { tab: PROCESSI_TABS.PRESIDI },
  })
}

// Scopo: classe CSS standard per le voci del kebab topbar. Tutte neutre/
// preferenze (preferiti/lingua/dark + search/AI quando mobile) -> nessuna
// severity esplicita, fallback "action" (verde) coerente col colore dei
// pulsanti inline `.topbar-icon-btn` (--p-primary-color).
const TOPBAR_MENU_CLASS = menuItemClass(undefined, 'app-menu-item-action')
// === Kebab "preferenze utente" sempre visibile (pre-logout) ===
// Submenu Preferiti tramite TieredMenu (PrimeVue 4): voci preferiti
// risolte dal composable `useNavigationFavorites` (filtro permessi
// applicato). Stile coerente col kebab standard di lista via la classe
// `app-menu-item-action` (verde) — stesso pattern del kebab mobile.
const { visibleFavorites, navigateToFavorite } = useNavigationFavorites()
const userKebabMenu = ref(null)

function toggleUserKebab(event) {
  userKebabMenu.value?.toggle(event)
}

const favoritesSubmenu = computed(() => {
  if (visibleFavorites.value.length === 0) {
    return [{
      label: t('nav.preferiti_empty_short'),
      icon: STATUS_ICONS.INFO,
      disabled: true,
      class: TOPBAR_MENU_CLASS,
    }]
  }
  return visibleFavorites.value.map(fav => ({
    label: fav.label,
    icon: fav.icon,
    class: TOPBAR_MENU_CLASS,
    command: () => navigateToFavorite(fav),
  }))
})

// Voci del kebab utente. Su mobile (viewport < BREAKPOINTS.MOBILE) le icone
// inline ricerca+AI sono nascoste via CSS @media: vengono allora promosse
// dentro il kebab come prime voci, in modo che non serva un secondo kebab
// separato per gestire il responsive. Su desktop/tablet le inline sono
// visibili e quindi non duplicate qui.
const userKebabItems = computed(() => {
  const items = []
  if (ui.isMobile) {
    items.push({
      label: t('context.tooltip_search'),
      icon: MANAGE_ICONS.RICERCA,
      class: TOPBAR_MENU_CLASS,
      command: () => ui.openSearchDrawer(),
    })
    if (codeDisponibile.value) {
      items.push({
        label: t('strumenti.code.badge_tooltip'),
        icon: NAV_ICONS.CODE_LAVORO,
        class: TOPBAR_MENU_CLASS,
        command: () => ui.openCodeDrawer(),
      })
    }
    if (presidiDisponibile.value) {
      items.push({
        label: t('amministrazione.processi.presidi_badge_menu'),
        icon: NAV_ICONS.PROCESSI_AUTOMATICI,
        class: TOPBAR_MENU_CLASS,
        command: apriProcessiAutomatici,
      })
    }
    if (ui.aiAvailable) {
      items.push({
        label: t('ai.title'),
        icon: NAV_ICONS.ASSISTENTE_AI,
        class: TOPBAR_MENU_CLASS,
        command: () => ui.toggleAiDrawer(),
      })
    }
  }
  items.push({
    label: t('nav.preferiti'),
    icon: MANAGE_ICONS.PREFERITI,
    class: TOPBAR_MENU_CLASS,
    items: favoritesSubmenu.value,
  })
  items.push({
    label: `${t('common.language')} · ${languageLabel.value}`,
    icon: MANAGE_ICONS.LINGUA,
    class: TOPBAR_MENU_CLASS,
    command: () => toggleLanguage(),
  })
  items.push({
    label: ui.isDark ? t('common.light_mode') : t('common.dark_mode'),
    icon: ui.isDark ? MANAGE_ICONS.TEMA_CHIARO : MANAGE_ICONS.TEMA_SCURO,
    class: TOPBAR_MENU_CLASS,
    command: () => ui.toggleDarkMode(),
  })
  return items
})

// Scopo: Verifica disponibilita' AI al mount (best-effort, non blocca).
//        Solo se l'utente e' autenticato, per evitare 401 inutili.
// ⭐ Si legge `utilizzabile`, non `enabled`: l'AI puo' essere accesa e l'area
//    `ai_assistant` BLOCCATA per questo utente, e allora la chat
//    risponderebbe 403 alla prima domanda. Lo decide il backend con la stessa
//    regola di `/query/` (Tid, 2026-09-25).
onMounted(async () => {
  if (!auth.isAuthenticated) return
  try {
    const response = await getAIStatus()
    ui.aiAvailable = response.data?.data?.utilizzabile === true
  } catch {
    ui.aiAvailable = false
  }
})
</script>

<template>
  <header class="app-topbar">
    <div class="topbar-left">
      <i v-if="!showHamburger" class="topbar-emittente-icon" :class="MANAGE_ICONS.BUILDING"></i>
      <EmittenteAttivoSelect />

      <!-- Operatore: iniziali (piu' il chip SUPER_ADMIN), subito dopo l'emittente.
           ⭐ Decisione di Tid, 2026-09-21: la topbar si legge a tre blocchi —
           sinistra = CHI (emittente + operatore che lo sta usando, la coppia
           «sistema + utente» in testa allo schermo AS/400), centro = DOVE
           (l'area), destra = COSA (contesto, data, strumenti, uscita). Fino a
           quel giorno il badge stava a destra tra il chip contesto e la data,
           cioe' tra cose che non descrivono l'identita'. -->
      <!-- ⭐ Il badge apre la scheda dell'utente: chi e' e le azioni sul
           proprio accesso (cambio password, Sicurezza). Decisione di Tid,
           2026-10-03: prima «Sicurezza» stava nel kebab delle preferenze. -->
      <button
        type="button"
        class="topbar-utente-btn"
        v-tooltip.bottom="auth.displayName"
        :aria-label="t('auth.account.apri_scheda')"
        aria-haspopup="true"
        @click="schedaUtente?.toggle($event)"
      >
        <!-- ⭐ Le iniziali ci sono sempre, anche per il super-amministratore:
             dicono CHI e' l'operatore. Il chip accanto dice solo che e' super
             admin. Decisione di Tid, 2026-10-18: prima il super admin aveva
             la corona al posto delle iniziali. Le iniziali stanno DENTRO il
             pulsante: cliccandole si apre la scheda, anche su mobile, dove il
             chip sparisce e al suo posto resta la corona rossa. -->
        <span class="user-initials-badge">
          {{ userInitials }}
        </span>
        <i
          v-if="auth.isSuperAdmin"
          class="admin-crown-mobile"
          :class="MANAGE_ICONS.SUPER_ADMIN"
          aria-hidden="true"
        />
        <Chip v-if="auth.isSuperAdmin" class="admin-chip">
          <template #default>
            <span class="admin-chip-label">{{ t('auth.super_admin_badge') }}</span>
          </template>
        </Chip>
      </button>
      <SchedaUtentePopover ref="schedaUtente" />
    </div>

    <div class="topbar-center">
      <span class="topbar-area-title">
        <i :class="areaDominio.icon" class="topbar-area-icon" aria-hidden="true"></i>
        {{ areaDominio.label }}
      </span>
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

      <span class="topbar-date">{{ formattedDate }}</span>

      <!-- Gruppo azioni inline — dark mode e lingua sono nel kebab utente
           (subito dopo). Qui restano solo ricerca universale e assistente AI,
           azioni di lavoro che vivono tra la data e il kebab utente. -->
      <div class="topbar-actions-inline">
        <!-- Badge code di lavoro: due segmenti (lavori · stampa), warn se un
             worker e' giu'. Visibile solo se l'endpoint conteggi e' accessibile
             (area core). Click → drawer rapido. -->
        <button
          v-if="codeDisponibile"
          class="topbar-icon-btn topbar-contatore-btn"
          v-tooltip.bottom="workerOk === false
            ? t('strumenti.code.badge_worker_giu')
            : t('strumenti.code.badge_tooltip')"
          @click="ui.openCodeDrawer()"
        >
          <i :class="[NAV_ICONS.CODE_LAVORO, { 'topbar-code-icon-warn': workerOk === false }]"></i>
          <Badge
            v-if="lavoriVivi > 0"
            :value="lavoriVivi"
            severity="info"
            class="topbar-contatore-badge topbar-contatore-badge-alto"
          />
          <Badge
            v-if="stampaVive > 0"
            :value="stampaVive"
            severity="warn"
            class="topbar-contatore-badge topbar-contatore-badge-basso"
          />
        </button>

        <!-- Pallino dei presidi (#8): l'icona e' sempre visibile per chi passa
             la porta; a zero (`ok`) resta la sola icona, senza badge — come il
             badge code (richiesta di Tid, 2026-10-11). Il «visto e vuoto» lo
             dice il tooltip. Un segmento per allarmi (danger) e uno per non
             letti (warn), stesse classi del badge code (`topbar-contatore-*`).
             Click → «Processi automatici», che c'e' gia'. -->
        <button
          v-if="presidiDisponibile"
          class="topbar-icon-btn topbar-contatore-btn"
          v-tooltip.bottom="presidiTooltip"
          @click="apriProcessiAutomatici"
        >
          <i :class="NAV_ICONS.PROCESSI_AUTOMATICI"></i>
          <Badge
            v-for="(seg, i) in presidiPallino && !presidiPallino.ok ? presidiPallino.segmenti : []"
            :key="seg.chiave"
            :value="seg.valore"
            :severity="seg.severity"
            class="topbar-contatore-badge"
            :class="i === 0 ? 'topbar-contatore-badge-alto' : 'topbar-contatore-badge-basso'"
          />
        </button>

        <!-- Pulsante ricerca universale -->
        <button
          class="topbar-icon-btn"
          v-tooltip.bottom="t('context.tooltip_search')"
          @click="ui.openSearchDrawer()"
        >
          <i :class="MANAGE_ICONS.RICERCA"></i>
        </button>

        <!-- Pulsante assistente AI — visibile solo se AI disponibile -->
        <button
          v-if="ui.aiAvailable"
          class="topbar-icon-btn"
          v-tooltip.bottom="`${t('ai.title')} (Ctrl+.)`"
          @click="ui.toggleAiDrawer()"
        >
          <i :class="NAV_ICONS.ASSISTENTE_AI"></i>
        </button>
      </div>

      <!-- Hamburger su mobile: a destra, subito prima del kebab. -->
      <button
        v-if="showHamburger"
        class="topbar-icon-btn"
        @click="emit('toggle-menu')"
      >
        <i :class="MANAGE_ICONS.MENU"></i>
      </button>

      <!-- Kebab utente: preferiti (submenu) + lingua + dark/light.
           Standard di kebab (stessa palette `app-menu-item-action`).
           Sempre visibile, subito prima del logout. -->
      <button
        class="topbar-icon-btn"
        v-tooltip.bottom="t('common.altre_azioni')"
        aria-haspopup="true"
        @click="toggleUserKebab"
      >
        <i :class="MANAGE_ICONS.KEBAB"></i>
      </button>
      <TieredMenu ref="userKebabMenu" :model="userKebabItems" popup />

      <!-- Logout -->
      <button
        class="topbar-icon-btn topbar-logout-btn"
        v-tooltip.bottom="t('auth.logout')"
        @click="handleLogout"
      >
        <i :class="MANAGE_ICONS.LOGOUT"></i>
      </button>
    </div>
  </header>

  <SearchDrawer v-if="ricercaMontata" v-model:visible="ui.searchDrawerVisible" />
  <AiAssistantDrawer v-model:visible="ui.aiDrawerVisible" />
  <CodeLavoroDrawer v-model:visible="ui.codeDrawerVisible" />
</template>

<style scoped>
/* Tre colonne: ali UGUALI e titolo al centro per costruzione. ⛔ `1fr` nudo
   non basta: un item di grid ha `min-width: auto`, quindi a schermo stretto
   l'ala destra (chip, data, pulsanti) si allargava oltre il suo 1fr, la
   sinistra cedeva e il titolo scivolava fino ad appiccicarsi all'emittente.
   Con `minmax(0, 1fr)` ogni ala tronca il PROPRIO contenuto invece di rubare
   spazio all'altra (Tid, 2026-09-21). */
.app-topbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  column-gap: 0.75rem;
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

/* La combo emittente e' del figlio (scoped): qui si impone solo che si
   stringa con l'ala invece di tenere i suoi 16rem e spingere fuori il resto.
   Il badge operatore invece non cede mai: e' gia' al minimo. */
.topbar-left :deep(.topbar-emittente-select) {
  min-width: 0;
  flex: 0 1 auto;
}
.topbar-left .admin-chip,
.topbar-left .user-initials-badge {
  flex: none;
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
  min-width: 0;
}

.topbar-area-title {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
  font-size: var(--app-font-size-base);
  font-weight: 500;
  color: var(--app-topbar-breadcrumb-active-color);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.topbar-area-icon {
  flex: none;
  font-size: 0.95em;
  opacity: 0.85;
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

/* Bottone icona topbar — classe riutilizzabile per hamburger, search, AI, kebab, logout */
.topbar-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.85rem;
  height: 1.85rem;
  font-size: 0.95rem;
  color: var(--app-accent-color);
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
  color: var(--app-accent-color);
}

.context-chip-label {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
  color: var(--app-accent-color);
}

/* Badge admin */
/* Il badge e' un pulsante (apre la scheda dell'utente): senza il chrome del
   bottone, il badge resta com'era. Il margine raddoppia il gap dell'ala
   (0.5rem → 1rem) solo tra emittente e operatore. */
.topbar-utente-btn {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  margin-left: 0.5rem;
  padding: 0;
  border: none;
  background: none;
  cursor: pointer;
  border-radius: var(--app-border-radius);
}

.topbar-utente-btn:focus-visible {
  outline: 2px solid var(--app-focus-ring);
  outline-offset: 2px;
}

.admin-chip {
  cursor: pointer;
  font-size: var(--app-font-size-sm);
  background: color-mix(in srgb, var(--app-warning-color) 12%, transparent);
  border: 1px solid color-mix(in srgb, var(--app-warning-color) 30%, transparent);
  padding: 0.15rem 0.5rem;
}

/* La corona del super admin: solo su mobile, al posto del chip (vedi la
   media query). ⛔ Col prefisso `.topbar-left`: senza, vince `.topbar-left i`
   (piu' specifica) e la corona prende il colore delle icone. */
.topbar-left .admin-crown-mobile {
  display: none;
  font-size: 0.85rem;
  color: var(--app-severity-danger);
}

.admin-chip-label {
  font-weight: 600;
  color: var(--app-warning-color);
}

/* Contatori ambientali della topbar (badge code, pallino presidi): stessa
   geometria per tutti — pulsante relativo, segmento «alto» in alto a destra
   (lavori · allarmi, o lo zero verde), segmento «basso» in basso a destra
   (stampa · non letti); pattern AlertScadenzeWidget. ⛔ UNA famiglia di
   classi: fino al 2026-09-19 il pallino ne aveva una copia identica riga per
   riga con un altro nome. */
.topbar-contatore-btn {
  position: relative;
}
.topbar-contatore-badge {
  position: absolute;
  font-size: 0.6rem;
  min-width: 1rem;
  height: 1rem;
  line-height: 1rem;
}
.topbar-contatore-badge-alto {
  top: -4px;
  right: -6px;
}
.topbar-contatore-badge-basso {
  bottom: -4px;
  right: -6px;
}
.topbar-code-icon-warn {
  color: var(--app-severity-danger);
}

/* Logout — override hover rosso (usa topbar-icon-btn come base) */
.topbar-logout-btn:hover {
  color: var(--p-red-500);
  background: var(--p-red-50);
}

/* Badge iniziali operatore (ogni operatore, super admin compreso) — sfondo celeste pastello */
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
  cursor: inherit;
  user-select: none;
}

/* Mobile — nasconde data, azienda, azioni inline; mostra solo il kebab */
@media (max-width: 767.98px) {
  /* ⛔ Le ali uguali della grid qui non reggono: l'ala sinistra e' piu'
     stretta di emittente + badge, il badge (che non cede) sborda dalla sua
     colonna e finisce sotto il titolo. In flex il titolo prende lo spazio
     TRA le ali, centrato li', e tronca lui e l'emittente invece di
     sovrapporsi (Tid, 2026-10-03). */
  .app-topbar {
    display: flex;
    gap: 0.75rem;
  }

  .topbar-left {
    flex: 0 1 auto;
  }

  .topbar-center {
    flex: 1 1 auto;
  }

  .topbar-right {
    flex: none;
  }

  .topbar-company,
  .topbar-date {
    display: none;
  }

  .topbar-emittente-icon {
    display: none;
  }

  .context-chip-label {
    max-width: 120px;
  }

  /* Su mobile il chip non ci sta: accanto alle iniziali resta la corona
     rossa a dire «super admin», la scritta la da' la scheda utente. */
  .topbar-left .admin-chip {
    display: none;
  }

  .topbar-left .admin-crown-mobile {
    display: inline-block;
  }

  /* Su mobile le icone inline ricerca+AI sono nascoste:
     le voci compaiono allora nel kebab utente (vedi userKebabItems). */
  .topbar-actions-inline {
    display: none;
  }
}

/* Tablet — il nome azienda si tronca con ellipsis */
@media (max-width: 1023.98px) and (min-width: 768px) {
  .topbar-company {
    max-width: 120px;
  }

  .context-chip-label {
    max-width: 120px;
  }
}
</style>

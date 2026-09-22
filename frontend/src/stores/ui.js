import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { BREAKPOINTS } from '../core/constants'
import { local, STORAGE_KEYS, userScopedKey } from '../core/storage'

export const useUiStore = defineStore('ui', () => {
  const storedValue = local.get(STORAGE_KEYS.SIDEBAR_COLLAPSED)
  const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1280)

  // ID utente corrente per la risoluzione delle chiavi localStorage
  // user-scoped (dark mode, lingua). Null/0 = nessun utente loggato →
  // fallback chiave "device default" (STORAGE_KEYS.<BASE>). Valorizzato
  // da `syncUserPreferences(userId)` chiamata da `auth.fetchProfile`
  // dopo aver popolato `user.value`.
  const currentUserId = ref(null)

  // Layout mode: mobile / tablet / desktop
  const layoutMode = computed(() => {
    if (windowWidth.value < BREAKPOINTS.MOBILE) return 'mobile'
    if (windowWidth.value < BREAKPOINTS.TABLET) return 'tablet'
    return 'desktop'
  })

  const isTablet = computed(() => layoutMode.value === 'tablet')
  const isMobile = computed(() => layoutMode.value === 'mobile')
  const isDesktop = computed(() => layoutMode.value === 'desktop')

  // ⭐ MODALITA' COMPATTA — la soglia in UNA sede (decisione D1 di Tid,
  //    2026-09-22): sotto il tablet **oppure** su un dispositivo senza hover.
  //    La leggono le superfici che cambiano FORMA, non solo dimensione: i
  //    filtri della lista (`FiltriLista`, drawer dal basso) e, per contratto,
  //    chiunque debba concordare con loro.
  // ⛔ La larghezza da sola non basta, ed e' il difetto che questa computed
  //    esiste per non avere: un iPad Pro in orizzontale e' largo 1366px e non
  //    ha hover, quindi `isDesktop` dice «desktop» mentre `RowActionsMenu` e
  //    `PageActionsBar` — che leggono `@media (hover: none), (max-width: 1024px)`
  //    in main.css — si sono gia' compressi. Appendere i filtri alla sola
  //    larghezza avrebbe prodotto una schermata mezza compatta e mezza no.
  // ⚠️ `matchMedia` e non un `ontouchstart`: la domanda non e' «c'e' un dito»
  //    ma «esiste l'hover», cioe' se un tooltip puo' essere l'unica etichetta
  //    di un pulsante. Un portatile con schermo touch ha entrambi, e per noi
  //    e' un desktop.
  const senzaHover = ref(false)
  if (typeof window !== 'undefined' && window.matchMedia) {
    const mqHover = window.matchMedia('(hover: none)')
    senzaHover.value = mqHover.matches
    const onHoverChange = (e) => { senzaHover.value = e.matches }
    mqHover.addEventListener('change', onHoverChange)
    if (import.meta.hot) {
      import.meta.hot.dispose(() => mqHover.removeEventListener('change', onHoverChange))
    }
  }
  const isCompatto = computed(
    () => windowWidth.value < BREAKPOINTS.TABLET || senzaHover.value,
  )

  // La sidebar inline si mostra solo su desktop e tablet (su mobile e' overlay/drawer)
  const sidebarInline = computed(() => layoutMode.value !== 'mobile')

  // Se non c'e' preferenza salvata e siamo su tablet, parte collassata
  const sidebarCollapsed = ref(
    storedValue !== null ? storedValue === 'true' : !isDesktop.value
  )

  // Su tablet la sidebar e' sempre collassata, indipendentemente dalla preferenza
  const effectiveSidebarCollapsed = computed(() =>
    isTablet.value ? true : sidebarCollapsed.value
  )

  // Search drawer — stato condiviso tra AppLayout (shortcut) e AppTopbar (pulsante)
  const searchDrawerVisible = ref(false)

  function openSearchDrawer() { searchDrawerVisible.value = true }

  // AI assistant drawer — stato condiviso tra AppTopbar (pulsante) e shortcut
  const aiDrawerVisible = ref(false)
  const aiAvailable = ref(false)

  // Drawer rapido code di lavoro (badge top bar → drawer, D-B brief
  // gestione-code-lavori-stampa).
  const codeDrawerVisible = ref(false)

  function openCodeDrawer() { codeDrawerVisible.value = true }

  // Dark/Light mode — persistito in localStorage, applicato su <html> class.
  // Chiave "device default" al boot (pre-login); sovrascritta dalla chiave
  // user-specific quando `syncUserPreferences(userId)` viene chiamata dopo
  // il login (vedi auth.js). Garantisce che utente A e B sullo stesso
  // browser abbiano temi indipendenti.
  const storedDarkMode = local.get(STORAGE_KEYS.DARK_MODE)
  const isDark = ref(storedDarkMode !== null ? storedDarkMode === 'true' : true)

  // Applica la classe al DOM all'inizializzazione
  function _applyDarkMode() {
    if (isDark.value) {
      document.documentElement.classList.add('p-dark')
    } else {
      document.documentElement.classList.remove('p-dark')
    }
  }
  _applyDarkMode()

  function toggleDarkMode() {
    isDark.value = !isDark.value
    // Quando loggato, la preferenza e' personale (chiave user-scoped).
    // Nessun utente corrente = scrive sul "device default" (es. durante
    // la pagina di login pre-auth).
    const key = userScopedKey(STORAGE_KEYS.DARK_MODE, currentUserId.value)
    local.set(key, isDark.value)
    _applyDarkMode()
  }

  // Stato espanso/collassato del pannello "I tuoi preferiti" in HomeView.
  // Stesso pattern di isDark: chiave user-scoped post-login, fallback "device
  // default" pre-login (rara — la HomeView non e' visibile pre-auth).
  const storedFavoritesExpanded = local.get(STORAGE_KEYS.FAVORITES_EXPANDED)
  const favoritesExpanded = ref(
    storedFavoritesExpanded !== null ? storedFavoritesExpanded === 'true' : false
  )

  function setFavoritesExpanded(value) {
    favoritesExpanded.value = !!value
    const key = userScopedKey(STORAGE_KEYS.FAVORITES_EXPANDED, currentUserId.value)
    local.set(key, favoritesExpanded.value)
  }

  function toggleFavoritesExpanded() {
    setFavoritesExpanded(!favoritesExpanded.value)
  }

  // Scopo: sincronizza le preferenze user-scoped (tema) con quelle salvate
  //        per l'utente fornito. Chiamata da `auth.fetchProfile` dopo il
  //        login o restore sessione.
  //
  //        Precedenza lookup:
  //          1) chiave user-scoped `dark_mode_user_<id>` → scelta personale
  //          2) fallback prodotto: dark (true)
  //
  //        NON si usa la chiave globale `dark_mode` come fallback: quella
  //        e' promiscua — puo' essere stata scritta in passato da qualsiasi
  //        utente (pre-fix user-scoped) o da interazioni sulla login page
  //        pre-auth, e farla ereditare a un nuovo utente comporta leak
  //        cross-user del tema. La chiave globale resta persistita solo
  //        per la pagina di login (pre-auth) e non e' mai consultata nel
  //        sync utente.
  function syncUserPreferences(userId) {
    currentUserId.value = userId ?? null
    if (userId == null) return

    const userKey = userScopedKey(STORAGE_KEYS.DARK_MODE, userId)
    const userValue = local.get(userKey)
    const resolved = userValue !== null ? userValue === 'true' : true
    isDark.value = resolved
    _applyDarkMode()

    // Stato pannello preferiti — chiave personale, fallback collassato.
    const favKey = userScopedKey(STORAGE_KEYS.FAVORITES_EXPANDED, userId)
    const favValue = local.get(favKey)
    favoritesExpanded.value = favValue !== null ? favValue === 'true' : false
  }

  function openAiDrawer() { aiDrawerVisible.value = true }
  function toggleAiDrawer() { aiDrawerVisible.value = !aiDrawerVisible.value }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
    local.set(STORAGE_KEYS.SIDEBAR_COLLAPSED, sidebarCollapsed.value)
  }

  function updateWindowWidth() {
    const prevMode = layoutMode.value
    windowWidth.value = window.innerWidth
    // Collassa automaticamente quando si passa a tablet
    if (prevMode === 'desktop' && layoutMode.value === 'tablet') {
      sidebarCollapsed.value = true
    }
  }

  // Listener resize con cleanup HMR
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateWindowWidth, { passive: true })
    if (import.meta.hot) {
      import.meta.hot.dispose(() => window.removeEventListener('resize', updateWindowWidth))
    }
  }

  // Scopo: reset transient state al logout (contratto plugin autoReset).
  //        Chiude i drawer di sessione e azzera `currentUserId`, MA
  //        preserva le preferenze device/user (`isDark`, `sidebarCollapsed`)
  //        e il tema applicato al DOM — quelle non sono stato di sessione.
  //        Questo risolve il bug "AI drawer resta aperto al cambio utente"
  //        (2026-04-23).
  function clearUserState() {
    searchDrawerVisible.value = false
    aiDrawerVisible.value = false
    aiAvailable.value = false
    codeDrawerVisible.value = false
    currentUserId.value = null
    // isDark, sidebarCollapsed, layoutMode: intatti.
    // Al prossimo login, `syncUserPreferences` applichera' la preferenza
    // personale dell'utente che entra (se salvata).
  }

  return {
    windowWidth,
    layoutMode,
    isTablet,
    isMobile,
    isDesktop,
    isCompatto,
    sidebarInline,
    sidebarCollapsed,
    effectiveSidebarCollapsed,
    searchDrawerVisible,
    openSearchDrawer,
    aiDrawerVisible,
    aiAvailable,
    openAiDrawer,
    toggleAiDrawer,
    codeDrawerVisible,
    openCodeDrawer,
    toggleSidebar,
    isDark,
    toggleDarkMode,
    favoritesExpanded,
    setFavoritesExpanded,
    toggleFavoritesExpanded,
    currentUserId,
    syncUserPreferences,
    clearUserState
  }
}, {
  userScoped: true
})

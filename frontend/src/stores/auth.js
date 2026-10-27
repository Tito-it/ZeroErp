import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { rinnovaAccess } from '../core/api'
import { redirectToLogin } from '../core/uscitaSessione'
import { DOMAINS } from '../core/navigation'
import { local, STORAGE_KEYS, ritiraTokenDalLocalStorage } from '../core/storage'
import {
  EVENTO_SESSIONE,
  MOTIVO_USCITA,
  accessValido,
  annunciaAlleAltreSchede,
  azzeraAccess,
  impostaAccess,
  suEventoAltraScheda
} from '../core/sessione'
import {
  RUOLO_APPLICATIVO,
  LIVELLO_ACCESSO,
  CANALE_LOGIN,
  OBBLIGO_CREDENZIALE,
  resolveCanaleLogin
} from '../core/constants'
import { resetAllUserScopedStores } from '../core/pinia-plugins/auto-reset'
import { syncUserLanguage } from '../core/i18n'
import { useUiStore } from './ui'
import { useNavigationStore } from './navigation'
import { switchEmittenteAttivo } from '../core/api/emittenteAttivo'
import { cambiaPassword as apiCambiaPassword } from '../core/api/password'
import { secondoPassoLogin } from '../core/api/secondoFattore'
import { impostaFusoAziendale } from '../core/utils/date'

export const useAuthStore = defineStore('auth', () => {
  // ⛔ I token non stanno più in localStorage (brief sicurezza §2, dal
  //    2026-09-28): il refresh è in un cookie HttpOnly che il JavaScript non
  //    vede, l'access solo in memoria (`core/sessione`). Si tolgono quelli
  //    rimasti da prima, perché un refresh leggibile lì è il rischio chiuso.
  ritiraTokenDalLocalStorage()

  // §8.5.2: canale di login corrente. Restored da localStorage al boot
  // (sopravvive al page reload), default ADMIN per sessioni pre-multi-face
  // e per retrocompat. Determina quale endpoint `/{admin|portale|shop}/token/`
  // usare per login + refresh.
  const loginChannel = ref(
    local.get(STORAGE_KEYS.LOGIN_CHANNEL) || CANALE_LOGIN.ADMIN.key
  )

  // Profilo utente caricato dall'endpoint /me/
  // Struttura JSONB: { utente, is_super_admin, ruolo_applicativo,
  // risorse_umane, soggetto, emittente, permessi_area, azioni_abilitate,
  // deve_cambiare_password, is_admin_globale }
  const user = ref(null)

  // Flag cambio password obbligatorio (impostato al login se deve_cambiare_password = true)
  const passwordChangeRequired = ref(false)

  // Scopo: c'è in memoria un access non scaduto (firma non verificata
  //        client-side). ⚠️ Al ricaricamento della pagina l'access non c'è
  //        MAI, anche con una sessione viva nel cookie: chi deve sapere se
  //        la sessione esiste chiama `ripristinaSessione()`, non questo.
  //        `accessValido` legge il ref reattivo di `core/sessione`, quindi il
  //        computed si aggiorna quando l'access cambia (anche da un'altra
  //        scheda).
  const isAuthenticated = computed(() => accessValido())

  // Nome visualizzato: priorità soggetto.nome > utente.first_name > username
  const displayName = computed(() => {
    if (!user.value) return ''
    const soggetto = user.value.soggetto
    if (soggetto?.nome) {
      return [soggetto.nome, soggetto.cognome].filter(Boolean).join(' ')
    }
    const utente = user.value.utente
    if (utente?.first_name || utente?.last_name) {
      return [utente.first_name, utente.last_name].filter(Boolean).join(' ')
    }
    return utente?.username || ''
  })

  // Scopo: riparte dal boot con un ricaricamento completo. ⭐ Unica sede
  //        dell'eccezione dichiarata in frontend-standards («Regole di
  //        sicurezza»): la usano il cambio emittente e l'apertura di una
  //        sessione diversa in un'altra scheda — due casi in cui ciò che la
  //        pagina tiene in memoria (KeepAlive, cache di modulo) non appartiene
  //        più alla sessione, e solo il boot garantisce di non mostrarlo.
  function ripartiDalBoot(destinazione = '/') {
    window.location.assign(destinazione)
  }

  // Scopo: garantisce un access valido in memoria. Se c'è, true; altrimenti
  //        rinnova dal cookie del refresh — al ricaricamento della pagina è
  //        sempre così. false = nessuna sessione (cookie assente, scaduto o
  //        revocato): chi chiama porta al login.
  async function ripristinaSessione() {
    if (accessValido()) return true
    try {
      await rinnovaAccess()
      return true
    } catch {
      azzeraAccess()
      return false
    }
  }

  // Scopo: Memorizza il canale di login scelto. Chiamato da `login()`;
  // separato per consentire test/debug di imposta canale senza fare login.
  function setLoginChannel(canaleKey) {
    const canale = resolveCanaleLogin(canaleKey)
    loginChannel.value = canale.key
    local.set(STORAGE_KEYS.LOGIN_CHANNEL, canale.key)
  }

  // Scopo: azzera lo stato auth di questo store (tokens + user + flag).
  //        Esposto come `clearUserState` (contratto autoReset plugin):
  //        il reset centralizzato al logout lo invoca durante l'iterazione
  //        degli store user-scoped. Non tocca gli altri store — di quelli
  //        si occupa il plugin iterando.
  //
  //        Il canale di login NON viene pulito: dopo il logout il
  //        LoginView riusa la stessa selezione (ADMIN/PORTALE/SHOP) e
  //        `setLoginChannel` lo sovrascrivera' al prossimo login.
  //        Il cookie del refresh non si tocca da qui (HttpOnly): lo cancella
  //        il backend col logout.
  function clearAuthTokensOnly() {
    azzeraAccess()
    user.value = null
    passwordChangeRequired.value = false
  }

  // Scopo: azzera lo stato utente completo dell'intera app.
  //        Unico punto di pulizia post-logout: delega a
  //        `resetAllUserScopedStores()` che itera tutti gli store
  //        marcati `userScoped: true` e chiama il loro `clearUserState`
  //        (o fallback $resetToInitial). Include auth stesso.
  //        Chiamato da `logout()` e dal flow 401/refresh-fallito.
  function clearTokens() {
    resetAllUserScopedStores()
  }

  async function fetchProfile() {
    try {
      const response = await api.get('/core/me/')
      user.value = response.data.data
      if (!user.value) {
        throw new Error('Profilo vuoto: risposta API senza dati utente')
      }
      // Il fuso dell'AZIENDA per «oggi» e per le ore a video (`core/utils/date`,
      // brief un-solo-fuso-aziendale F-1): un dato del DB, non il fuso del PC.
      impostaFusoAziendale(user.value.fuso_aziendale)
      // Applica preferenze personali dell'utente (tema + lingua UI + preferiti).
      // Chiavi localStorage user-scoped: evita che la scelta di un altro
      // utente sullo stesso browser persista al login successivo.
      // NB: il response /me/ espone `utente.auth_user_id` (non `utente.id`),
      // vedi test_me_view._PROFILE_FULL. Usare la chiave sbagliata qui faceva
      // saltare l'intera sincronizzazione user-scoped al login — i preferiti
      // restavano sulla chiave base globale (cross-user leak).
      const uid = user.value.utente?.auth_user_id ?? null
      if (uid != null) {
        useUiStore().syncUserPreferences(uid)
        useNavigationStore().syncUserFavorites(uid)
        syncUserLanguage(uid)
      }
    } catch (err) {
      user.value = null
      throw err
    }
  }

  // Scopo: Login multi-canale (§8.5.2). `canaleKey` opzionale per retrocompat:
  // se omesso, usa la key gia' salvata (default ADMIN). Il canale determina
  // quale endpoint token chiamare (`/admin/token/` | `/portale/token/` |
  // `/shop/token/`) e viene persistito per il successivo refresh.
  //        ⭐ Col secondo fattore attivo la password non basta: il backend
  //        risponde con una SFIDA e nessun token (brief sicurezza §3.4-bis).
  //        Ritorna `{ secondoPasso: true, sfida }`, e la view chiede il codice
  //        (`completaSecondoPasso`); altrimenti `{ secondoPasso: false }`.
  //        `identificativo` è la chiave d'ingresso del canale (`campoIngresso`:
  //        nome utente per ADMIN, email per PORTALE e SHOP — L-4).
  async function login(identificativo, password, canaleKey) {
    if (canaleKey) {
      setLoginChannel(canaleKey)
    }
    const canale = resolveCanaleLogin(loginChannel.value)
    const response = await api.post(canale.tokenPath, {
      [canale.campoIngresso]: identificativo,
      password
    })
    if (response.data?.two_factor_required) {
      return { secondoPasso: true, sfida: response.data.sfida }
    }
    await apriSessione(response.data.access, response.data.password_change_required)
    return { secondoPasso: false }
  }

  // Scopo: il secondo passo del login: la sfida del primo e la prova
  //        (`{ codice }` dell'app o `{ codiceRecupero }`). Apre la sessione e
  //        ritorna quanti codici di recupero restano, se se n'è usato uno.
  async function completaSecondoPasso(sfida, prova) {
    const canale = resolveCanaleLogin(loginChannel.value)
    const response = await secondoPassoLogin(canale.secondoFattorePath, sfida, prova)
    const data = response.data?.data || {}
    await apriSessione(data.access, data.password_change_required)
    return { codiciRecuperoRimasti: data.codici_recupero_rimasti ?? null }
  }

  // Scopo: apre la sessione appena data dal backend (il refresh è già nel
  //        cookie, qui arriva l'access). ⭐ Una sede per i due passi del
  //        login (regola del 2).
  async function apriSessione(access, cambioPassword) {
    impostaAccess(access, { annuncia: false })
    // Il cookie ora è di QUESTA sessione, per tutte le schede: quelle aperte
    // su un'altra ripartono dal boot invece di mostrarne i dati.
    annunciaAlleAltreSchede({ tipo: EVENTO_SESSIONE.SESSIONE_NUOVA })
    // Controlla flag cambio password dal backend
    passwordChangeRequired.value = !!cambioPassword
    try {
      await fetchProfile()
    } catch (err) {
      clearTokens()
      throw err
    }
  }

  async function logout() {
    // Invalida la sessione lato server (il refresh lo porta il cookie, e il
    // backend lo cancella); se il logout server fallisce si pulisce comunque.
    try {
      await api.post('/auth/logout/')
    } catch {
      // Se il logout server fallisce, procedi comunque con la pulizia locale
    }
    // Il cookie è condiviso: anche le altre schede sono uscite.
    annunciaAlleAltreSchede({ tipo: EVENTO_SESSIONE.LOGOUT })
    clearTokens()
  }

  // Eventi delle altre schede (l'access nuovo lo gestisce `core/sessione` da
  // solo). Registrato una volta: lo store si crea una volta per pagina.
  suEventoAltraScheda(evento => {
    if (evento.tipo === EVENTO_SESSIONE.LOGOUT) {
      // La sessione non è scaduta: l'ha chiusa l'operatore da un'altra scheda,
      // e il login lo dice (prima: «sessione scaduta», rilievo di Tid).
      redirectToLogin(MOTIVO_USCITA.USCITA_ALTRA_SCHEDA)
    } else if (evento.tipo === EVENTO_SESSIONE.SESSIONE_NUOVA) {
      // Si resta sulla pagina corrente: il boot rifà il giro del guard con la
      // sessione nuova (e porta al login o alla home del suo namespace).
      ripartiDalBoot(window.location.href)
    }
  })

  // Multi-face auth Stage B: i nuovi campi nativi di /me/.
  // - isSuperAdmin: true se l'utente ha binding al profilo SUPER_ADMIN
  //   (profilo id 9100). ⛔ Fino al 2026-09-12 esisteva anche l'alias
  //   `isAdmin`, «legacy» dal cutover multi-face e con DIECI consumer vivi:
  //   il modello ADMIN/OPERATIVO e' morto in Fase 7 e l'alias teneva vivo
  //   il vocabolario vecchio (analisi-software-per-dati-morti §2.8).
  //   Rinominati i consumer, alias tolto: il presidio e' il grep a zero.
  // - ruoloApplicativo: categoria dell'identita' attiva
  //   (OPERATORE | CLIENTE_PORTALE | FORNITORE_PORTALE | SHOP_CUSTOMER |
  //    API_CLIENT | null).
  const isSuperAdmin = computed(() => user.value?.is_super_admin === true)
  const ruoloApplicativo = computed(() => user.value?.ruolo_applicativo || null)

  // §8.5.3: id dell'identita attiva del JWT corrente. Post-§8.3.6 il /me/
  // espone il blocco `identita` con la veste risolta dal claim. Consumer:
  // FE che devono passare `identita_id` a endpoint che ne hanno bisogno
  // (es. flussi cross-veste in PR-C), o mostrare la veste corrente in UI.
  const identitaId = computed(() => user.value?.identita?.id || null)

  // Helpers ortogonali per namespace multi-face. Utili per router guard,
  // navigazione condizionale e feature flag lato UI.
  const isOperatoreInterno = computed(
    () => ruoloApplicativo.value === RUOLO_APPLICATIVO.OPERATORE
  )
  const isClientePortale = computed(
    () => ruoloApplicativo.value === RUOLO_APPLICATIVO.CLIENTE_PORTALE
  )
  const isFornitorePortale = computed(
    () => ruoloApplicativo.value === RUOLO_APPLICATIVO.FORNITORE_PORTALE
  )
  const isShopCustomer = computed(
    () => ruoloApplicativo.value === RUOLO_APPLICATIVO.SHOP_CUSTOMER
  )

  // Refactor operatore-emittenti (Q1): admin globale = ADMIN senza riga
  // in user_emittenti_fiscali. Il flag e' calcolato lato backend dalla
  // /core/me/ view. Per operatori e' sempre false.
  const isAdminGlobale = computed(() => !!user.value?.is_admin_globale)

  // Refactor operatore-emittenti: emittente fiscale 1-a-1 dell'utente
  // corrente. Per admin globale ritorna null perche' il blocco `emittente`
  // del profilo riflette il "gestore globale" (cascata fallback di
  // fn_get_user_profile) e NON l'emittente personale dell'utente.
  //
  // Esposte DUE chiavi FK distinte perche' il modello le differenzia:
  //   - id                → anagrafiche.emittenti_fiscali.id (PK reale, usato
  //     ad es. da pratiche.emittente_fiscale_id)
  //   - soggettoRuoloId   → anagrafiche.soggetti_ruoli.id (usato ad es. da
  //     vendite.listini.emittente_soggetto_ruolo_id)
  // La differenza non e' ovvia dal nome e va rispettata. Vedi
  // feedback_emittente_pk_vs_soggetto_ruolo.md.
  const emittenteCorrente = computed(() => {
    if (isAdminGlobale.value) return null
    const ef = user.value?.emittente
    if (!ef) return null
    return {
      id: ef.emittente_fiscale_id ?? null,
      // Il blocco `emittente` e' il merge tra i campi `emittente_*` e l'output
      // di fn_get_soggetto_dati_by_ruolo, che espone il ruolo come
      // `soggetto_ruolo_id` (senza prefisso). E' la PK verso soggetti_ruoli.
      soggettoRuoloId: ef.soggetto_ruolo_id ?? null,
      // Il SOGGETTO dell'emittente (uuid di `anagrafiche.soggetti`), dallo
      // stesso merge: serve a chi sceglie fra gli indirizzi dell'azienda (il
      // magazzino sta a un indirizzo del soggetto emittente, Q-2 del piano
      // anagrafiche-fuori-dal-pannello-config).
      soggettoId: ef.soggetto_id ?? null,
      codice: ef.emittente_codice ?? null,
      // `ragione_sociale_completa` arriva dal merge con
      // fn_get_soggetto_dati_by_ruolo ed e' sempre presente: il vecchio fallback
      // su `emittente_descrizione` (etichetta interna dell'emittente, in via di
      // eliminazione) era codice morto — tolto il 2026-08-02, vedi
      // `brief-emittente-ragione-sociale-dal-soggetto.md`.
      ragioneSociale: ef.ragione_sociale_completa ?? null,
    }
  })

  // Impersonazione di scope: dentro quale emittente sta lavorando QUESTA
  // sessione. Arriva da /me/ (blocco `emittente_attivo`), che lo legge dal
  // claim JWT — non dalla preferenza salvata: dopo un passaggio a «Tutti gli
  // emittenti» i due valori divergono, e comanda il claim.
  //
  // ⚠️ Da non confondere con `emittenteCorrente`, che resta l'emittente di
  // PERMESSO dell'operatore (la sua riga in user_emittenti_fiscali). Per un
  // operatore i due coincidono sempre; per il super admin il primo e' una
  // scelta e il secondo e' null.
  const emittenteAttivo = computed(() => user.value?.emittente_attivo ?? null)

  // Mostra o no la combo in topbar: l'operatore non sceglie, il suo emittente
  // e' un permesso.
  const puoScegliereEmittente = computed(
    () => emittenteAttivo.value?.puo_scegliere === true
  )

  // Scelta mai fatta (o decaduta): il FE impone il dialog iniziale. Distinto
  // da «ha scelto Tutti», che non deve riproporre nulla.
  const deveScegliereEmittente = computed(
    () => emittenteAttivo.value?.deve_scegliere === true
  )

  // Perimetro EFFETTIVO: sta guardando piu' di un emittente? Alimenta le
  // etichette di perimetro su contatori e ricerca (P-2c, brief
  // perimetro-emittente): «Da fatturare: 240.000 € — tutti gli emittenti» e'
  // informazione completa, lo stesso numero senza etichetta non lo e'.
  //
  // ⚠️ Lo DERIVA IL BACKEND (`perimetro_multi_emittente` in /me/): e' l'unico
  //    che conosce la cardinalita' dello scope. Non si ricalcola qui da
  //    `modalita_globale`, che e' una cosa diversa: un OPERATORE senza
  //    emittente attivo e' in modalita' globale ma vede un solo emittente —
  //    l'etichetta gli direbbe una cosa falsa.
  //
  // ⚠️ Chiave assente -> `false`: il POST di cambio emittente non la manda
  //    (li' descriverebbe la sessione precedente), e in quel momento la
  //    pagina si sta comunque ricaricando.
  const perimetroMultiEmittente = computed(
    () => emittenteAttivo.value?.perimetro_multi_emittente === true
  )

  // Scopo: l'emittente su cui questa sessione SCRIVE — il valore da mettere in
  //        `emittente_fiscale_id` quando si crea qualcosa.
  //
  // ⭐ DUE SORGENTI, UN VALORE, ed e' il punto: per l'OPERATORE e' il suo
  //    emittente di permesso (ne ha sempre uno, e non lo sceglie); per il SUPER
  //    ADMIN e' quello che ha scelto per la sessione. Prima questa domanda non
  //    aveva una risposta sola — `useEmittenteFiscaleField` guardava solo la
  //    prima sorgente e per il super admin rispondeva `null` **anche dopo che
  //    aveva scelto**, cioe' il drawer gli richiedeva una scelta gia' fatta.
  //
  // ⚠️ Le due chiavi sono la STESSA famiglia di id — la PK di
  //    `anagrafiche.emittenti_fiscali` — verificato su entrambe le sorgenti
  //    (`user_emittenti_fiscali.emittente_fiscale_id` e `ef.id` delle opzioni
  //    selezionabili). Non e' il `soggetto_ruolo_id`, che vive accanto e non si
  //    puo' scambiare (`feedback_emittente_pk_vs_soggetto_ruolo`).
  //
  // ⛔ `null` NON e' un default innocuo: vuol dire «questa sessione non ha un
  //    emittente su cui scrivere», ed e' lo stato in cui i verbi di creazione
  //    vanno spenti — non uno in cui compilare una form fino in fondo e farsi
  //    rifiutare dal database alla scrittura.
  const emittenteScritturaId = computed(
    () => emittenteCorrente.value?.id
      ?? emittenteAttivo.value?.emittente_fiscale_id
      ?? null
  )

  // Scopo: dello STESSO emittente di scrittura, il ruolo (`soggetti_ruoli.id`)
  //        e il nome. Stesse due sorgenti, stessa precedenza.
  // ⚠️ Il ruolo NON e' la PK (`feedback_emittente_pk_vs_soggetto_ruolo`): e'
  //    la chiave dei listini (`emittente_soggetto_ruolo_id`). Per il super
  //    admin arriva da `/me/` (`emittente_attivo.soggetto_ruolo_id`, dal
  //    2026-09-26): prima non c'era, e il listino gli restava non creabile
  //    anche dopo aver scelto l'emittente.
  const emittenteScritturaSoggettoRuoloId = computed(
    () => emittenteCorrente.value?.soggettoRuoloId
      ?? emittenteAttivo.value?.soggetto_ruolo_id
      ?? null
  )
  const emittenteScritturaNome = computed(
    () => emittenteCorrente.value?.ragioneSociale
      ?? emittenteAttivo.value?.ragione_sociale
      ?? null
  )

  // Scopo: Domini visibili. Filtri applicati:
  //   - adminOnly: solo SUPER_ADMIN (es. Amm. Software).
  //   - non adminOnly: solo operatori interni (OPERATORE). I portali e lo
  //     shop hanno namespace dedicati /portale/ e /shop/ e non vedono i
  //     domini operativi.
  //   - BLOCCATO: nascosto a tutti (tranne SUPER_ADMIN via bypass DB).
  // I domini adminOnly hanno il loro guard — non applicare il check livello.
  const visibleDomains = computed(() => {
    return DOMAINS.filter(d => {
      if (d.adminOnly) return isSuperAdmin.value
      if (!isOperatoreInterno.value) return false
      if (d.schemaDb && isAreaBlocked(d.schemaDb)) return false
      return true
    })
  })

  // Mappa permessi area: { anagrafiche: 'TUTTO', vendite: 'LETTURA', ... }
  // Popolata da /me/ campo permessi_area (fn_get_user_permissions_map)
  const permessiArea = computed(() => user.value?.permessi_area || {})

  // Livello accesso per area funzionale (TUTTO | LETTURA | BLOCCATO).
  // SUPER_ADMIN ha bypass totale su tutte le aree (pattern identico a isActionAllowed).
  function getLivelloArea(schemaDb) {
    if (isSuperAdmin.value) return LIVELLO_ACCESSO.TUTTO
    return permessiArea.value[schemaDb] || LIVELLO_ACCESSO.BLOCCATO
  }

  // Scopo: Area in sola lettura? (livello LETTURA)
  function isAreaReadonly(schemaDb) {
    return getLivelloArea(schemaDb) === LIVELLO_ACCESSO.LETTURA
  }

  // Scopo: Area bloccata? (livello BLOCCATO — nessun accesso)
  function isAreaBlocked(schemaDb) {
    return getLivelloArea(schemaDb) === LIVELLO_ACCESSO.BLOCCATO
  }

  // Mappa livelli EFFETTIVI per oggetto: { 'anagrafiche.conto_bancario': 'LETTURA', ... }
  // Popolata da /me/ campo permessi_oggetto (fn_get_user_object_permissions_map).
  // ⭐ Dal 2026-10-04 (brief-db-permessi-tetto-area) la mappa copre TUTTO il
  //    catalogo `area_model_overrides` col livello gia' deciso dal DB: override,
  //    area dell'oggetto e tetto d'area. Prima portava i soli override grezzi e
  //    la catena si riscriveva qui (override ?? area): col tetto quella copia
  //    avrebbe dato TUTTO su un oggetto di un'area BLOCCATA.
  const permessiOggetto = computed(() => user.value?.permessi_oggetto || {})

  // Scopo: Livello accesso per singolo model. Si LEGGE la mappa del DB; un
  //        oggetto fuori catalogo vale la sua area, che per un oggetto fuori
  //        catalogo e' l'app_label (stessa regola di `script.fn_area_di_oggetto`).
  // ⛔ Non ricalcolare qui override o tetto: la regola ha una sede sola, il DB.
  function getLivelloOggetto(appLabel, modelName) {
    const key = `${appLabel}.${modelName}`
    return permessiOggetto.value[key] ?? getLivelloArea(appLabel)
  }

  // Scopo: Model in sola lettura? (livello effettivo LETTURA, gia' col tetto)
  function isObjectReadonly(appLabel, modelName) {
    return getLivelloOggetto(appLabel, modelName) === LIVELLO_ACCESSO.LETTURA
  }

  // Scopo: Model bloccato? (livello effettivo BLOCCATO, gia' col tetto)
  function isObjectBlocked(appLabel, modelName) {
    return getLivelloOggetto(appLabel, modelName) === LIVELLO_ACCESSO.BLOCCATO
  }

  // Mappa azioni abilitate: { genera_fatture_lotti: true, numera_fatture_lotti: false, ... }
  // Popolata da /me/ campo azioni_abilitate (fn_get_user_actions_map)
  const azioniAbilitate = computed(() => user.value?.azioni_abilitate || {})

  // Scopo: Azione di processo abilitata? SUPER_ADMIN ha bypass totale, default false.
  function isActionAllowed(codename) {
    if (isSuperAdmin.value) return true
    return azioniAbilitate.value[codename] === true
  }

  // Scopo: Cambia la password dell'operatore collegato. Il BE apre una
  //        sessione NUOVA (le vecchie sono revocate): il refresh lo scrive nel
  //        cookie, qui arriva l'access. Tenerlo e' compito dello store, come
  //        per il cambio emittente — una view che lo scrive a mano e' una
  //        seconda sede della sessione. Ritorna la response axios; un errore
  //        risale al chiamante, che lo mostra dove serve.
  async function cambiaPassword({ oldPassword, newPassword, newPasswordConfirm }) {
    const response = await apiCambiaPassword({ oldPassword, newPassword, newPasswordConfirm })
    const data = response.data?.data || response.data
    if (data?.access) {
      // Stessa persona, stessa veste: le altre schede prendono l'access nuovo
      // (il cookie è già quello della sessione nuova).
      impostaAccess(data.access)
      passwordChangeRequired.value = false
      // Ricarica il profilo per aggiornare `deve_cambiare_password`.
      try { await fetchProfile() } catch { /* non blocca il flusso */ }
    }
    return response
  }

  // Scopo: Cambia l'emittente attivo di sessione e riparte pulito.
  //        `emittenteFiscaleId = null` = «Tutti gli emittenti».
  //
  //        L'emittente attivo vive in un claim JWT: il backend riscrive il
  //        refresh nel cookie col claim nuovo e restituisce l'access. Le altre
  //        schede ripartono anche loro (SESSIONE_NUOVA): con l'access vecchio
  //        in memoria continuerebbero a lavorare nell'emittente precedente.
  //
  //        Il ricaricamento e' un `window.location.assign('/')` deliberato, non
  //        una navigazione del router: cambiare emittente cambia CIO' CHE SI
  //        VEDE ovunque, e mezza applicazione ha stato in cache (KeepAlive
  //        delle viste, store user-scoped, cache lookup a livello di modulo).
  //        Ripartire dal boot e' l'unico modo per non lasciare in giro dati
  //        dell'emittente precedente, ed e' esattamente il rischio che
  //        l'impersonazione esiste per evitare. Costa un secondo.
  async function cambiaEmittenteAttivo(emittenteFiscaleId) {
    const esito = await switchEmittenteAttivo(emittenteFiscaleId)
    if (!esito?.access) {
      throw new Error('Cambio emittente senza token: sessione non aggiornata')
    }
    impostaAccess(esito.access, { annuncia: false })
    annunciaAlleAltreSchede({ tipo: EVENTO_SESSIONE.SESSIONE_NUOVA })
    ripartiDalBoot('/')
  }

  // Scopo: Getter per determinare se l'operatore deve cambiare password.
  const mustChangePassword = computed(() =>
    passwordChangeRequired.value || !!user.value?.deve_cambiare_password
  )

  // Scopo: il secondo fattore è obbligatorio e non ancora configurato. Lo
  //        dice il backend (`obblighi_pendenti` di `/core/me/`, la stessa
  //        regola del cancello): qui non si ricalcola niente. Dopo la
  //        configurazione si rilegge il profilo (`fetchProfile`).
  const mustConfigureSecondFactor = computed(() =>
    (user.value?.obblighi_pendenti || []).includes(OBBLIGO_CREDENZIALE.SECONDO_FATTORE)
  )

  return {
    user,
    isAuthenticated,
    ripristinaSessione,
    isSuperAdmin,
    ruoloApplicativo,
    identitaId,
    isOperatoreInterno,
    isClientePortale,
    isFornitorePortale,
    isShopCustomer,
    isAdminGlobale,
    emittenteCorrente,
    emittenteAttivo,
    emittenteScritturaSoggettoRuoloId,
    emittenteScritturaNome,
    emittenteScritturaId,
    perimetroMultiEmittente,
    puoScegliereEmittente,
    deveScegliereEmittente,
    cambiaEmittenteAttivo,
    cambiaPassword,
    completaSecondoPasso,
    mustChangePassword,
    mustConfigureSecondFactor,
    passwordChangeRequired,
    displayName,
    visibleDomains,
    permessiArea,
    getLivelloArea,
    isAreaReadonly,
    isAreaBlocked,
    permessiOggetto,
    getLivelloOggetto,
    isObjectReadonly,
    isObjectBlocked,
    azioniAbilitate,
    isActionAllowed,
    loginChannel,
    setLoginChannel,
    login,
    logout,
    clearTokens,
    fetchProfile,
    // Contratto plugin autoReset: clearUserState e` la primitiva che il
    // reset centralizzato chiama sullo store auth. Delega alla pulizia
    // tokens-only (no ricorsione su resetAllUserScopedStores, che e' il
    // chiamante). Equivalente al vecchio clearTokens pre-refactor.
    clearUserState: clearAuthTokensOnly
  }
}, {
  userScoped: true
})

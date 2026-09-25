# Piano BE/FE — Accessi: una credenziale, più vesti, un ciclo di vita solo

> **Tipo documento**: piano di lavoro backend + frontend (`dev/backend-tid`).
>
> **Data**: 2026-09-24 · **Stato**: 🟡 **IN CORSO** — ✅ L-0 fatto
> (2026-09-24, §2); ✅ L-1 fatto (2026-09-25, §3.1-bis); gli altri lotti da fare.
> Le tre domande di §6 sono decise (Tid, 2026-09-24).
>
> **Da dove viene**: [analisi-accessi-credenziale-e-vesti.md](analisi-accessi-credenziale-e-vesti.md)
> (inventario, difetti M-4/M-5/M-6 e A-1…A-9, decisioni D-1…D-10) e
> [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md)
> (la forma DB di tentativi, blocco, cambio password obbligatorio ed email,
> con le decisioni D-B1…D-B5). Questo piano non ripete il perché: lo rimanda.
>
> **Regola di lettura**: ogni lotto dice **da cosa dipende** (changeSet del
> brief, oppure nulla) e **cosa chiude** (le sigle dell'analisi). Un lotto che
> dipende dal DB non parte prima del suo changeSet
> (memoria di progetto: BE/FE solo con i prerequisiti DB pronti).

---

## 1. I lotti in una tabella

| Lotto | Cosa | Dipende da | Chiude |
| --- | --- | --- | --- |
| **L-0** | L'IP del chiamante, fidato | niente (§6 Q-1) | prerequisito di L-1 |
| **L-1** | Login su tentativi, freno, attesa; cambio password obbligatorio per credenziale; azzeramento al reset | brief **P-1** (§2–§4) — **stessa PR del DB** | M-4, D-1, D-2, D-7 |
| **L-2** | Blocco e sblocco dell'admin | brief **P-1** (§3.3) | D-1 (blocco vero) |
| **L-3** | Una persona, una credenziale; invito e attivazione operatore sulla regola unica; ultimo accesso | brief **P-2** (§5) + **richieste DB nuove** (§5 R-1, R-2) | D-6, D-8, A-1, A-2, A-3, A-4, A-9 |
| **L-4** | Portale e shop entrano con l'email; il nome utente nell'invito operatore | brief **P-2** (indice email) + §5 R-3 | D-9 |
| **L-5** | Disattivazione per veste, niente riattivazione diretta, revoca che tiene, sessioni per veste | §5 R-4, R-5 | M-5, M-6, D-3, D-4, D-5, A-5, A-6 |
| **L-6** | Validità della veste al login e a ogni richiesta; cambio password obbligatorio che funzioni col JWT | niente | A-7, A-8 |

⭐ L-0 e L-6 non aspettano nessuno. L-1 e L-2 viaggiano col changeSet P-1.

---

## 2. L-0 — L'IP del chiamante, fidato

**Il difetto trovato scrivendo il piano (✅ verificato 2026-09-24).**
`apps/core/services/request_context.get_client_ip` restituisce il **primo**
valore di `X-Forwarded-For`, cioè quello che scrive il **client**. Oggi finisce
solo negli audit (13 chiamanti), ma col brief diventa la **provenienza** del
freno: chi attacca cambierebbe l'IP dichiarato a ogni tentativo e il freno non
scatterebbe mai; peggio, potrebbe dichiarare l'IP di qualcun altro e farlo
frenare.

**Cosa si fa.** La regola «quale hop è fidato» sta in **un** posto, il building
block `get_client_ip` stesso (tutti i 13 chiamanti ne beneficiano, nessuna
seconda copia):

- `0` proxy dichiarati → `REMOTE_ADDR`, e `X-Forwarded-For` **ignorato**;
- N proxy fidati (setting obbligatorio, §6 Q-1; `1` con Nginx) → l'N-esimo
  valore **da destra**, cioè quello aggiunto dal primo proxy fidato.

Il valore torna come stringa valida per `inet`, o `None` se non si ricava; il
login con `None` **non** chiama le funzioni del freno con `NULL` (il brief lo
rifiuta, §2.1): risponde con un errore tecnico, fail-closed.

**Test**: header forgiato ignorato senza proxy; con un proxy, il valore giusto
fra tre; header malformato.

**✅ Fatto (2026-09-24).**

- `get_client_ip` applica la regola e valida con `ipaddress` (forma canonica,
  IPv6 compreso). Con N > 0, header **assente** o con **meno di N valori** →
  `None`: la richiesta non è passata dalla catena dichiarata, e non si ripiega
  su `REMOTE_ADDR` (sarebbe l'IP del proxy).
- Setting `TRUSTED_PROXY_COUNT` in `settings.py` da `DJANGO_TRUSTED_PROXY_COUNT`,
  obbligatorio, intero ≥ 0. `1` in `env.sh` e `.env.systemd` di sviluppo, `0`
  in CI (`ci-validate.yaml`, smoke Docker di `ci.yaml`: niente proxy davanti) e
  nel comando «prova locale come la CI» di api.md; guide `configurazione-django`,
  `backend-dev`, playbook §6 con la riga «se cambia la catena, si aggiorna».
- ⭐ **Seconda sede trovata e ritirata**: i throttle DRF (`LoginRateThrottle`,
  `PasswordResetRateThrottle`, `SearchBurstRateThrottle`) leggevano l'IP con
  `get_ident` di DRF, che senza `NUM_PROXIES` usa l'header **intero**: chi lo
  cambiava a ogni richiesta aveva un contatore nuovo, cioè il throttle del
  login era aggirabile. Ora passano da `get_client_ip` (`_ClientIpIdentMixin`);
  IP non ricavabile → un contatore comune (`ip-sconosciuto`), fail-closed.
- Test: `apps/core/tests/services/test_request_context.py` (0, 1, 2 proxy;
  forgiato, assente, malformato, IPv6; ident dei tre throttle). I due test di
  `test_session_audit_service` che fissavano il «primo valore» sono ritirati lì.
- ✅ **Una sola catena anche in sviluppo** (Tid, 2026-09-25): il dev server
  Vite era in ascolto su tutte le interfacce e passava `/api` direttamente a
  Django, cioè una seconda strada senza Nginx (IP `None` con `1`: il login di
  L-1 l'avrebbe rifiutato). Scelto di **passare sempre da Nginx** invece di
  `xfwd: true` in Vite: con `xfwd`, lo stesso `1` avrebbe voluto dire «Vite» in
  sviluppo e «Nginx» in produzione, una coincidenza che si rompe in silenzio.
  Vite su `127.0.0.1`, senza proxy `/api`, HMR su 443; vhost: `/api/` a Gunicorn,
  `/` a Vite (configurazione-django.md, «Nginx (vhost finale)»).
  `FRONTEND_URL` diventa **obbligatorio** (il default `localhost:5173` puntava
  alla strada chiusa, e ripetuto con `getattr` in tre servizi: ritirati).

---

## 3. L-1 e L-2 — Il login e la credenziale (P-1 del brief)

### 3.1 L-1 — Backend

| Pezzo | Dove | Cosa cambia |
| --- | --- | --- |
| Check e registrazione | `core/db/auth_repository.py` `check_blocco_login`, `registra_tentativo_login`; `core/api/auth_views.py` | nuova firma con la provenienza (L-0); il ritorno porta `attesa_secondi` |
| Codici nuovi | catalogo (dal DB) → `genera_error_policies`; `error_messages_fallback.py` | `E_CREDENZIALE_BLOCCATA`, `E_LOGIN_ATTESA`, **classe `NON_PERMESSO` (403)** come `E_UTENTE_BLOCCATO` — non 429 (nota nel brief §2.4) |
| Cambio password obbligatorio | `AuthRepository.get/set_deve_cambiare_password` | diventano chiamate a `fn_get_deve_cambiare_password` / `fn_imposta_deve_cambiare_password`: **niente SQL diretto, niente `identita_id`** (D-7). Chiamanti: login, `PasswordChangeRequiredMiddleware`, `apply_new_password` (cambio, reset, attivazioni), invito operatore |
| Azzeramento | `core/api/password_reset_views.py` (conferma) | dopo il reset riuscito, `fn_azzera_tentativi_credenziale` (D-2). Il blocco dell'admin resta (D-B3) |
| Colonne tolte a `identita_digitali` | `portale_repository.find_identita_portale` (`:95`), `create_identita_portale`, `ProfileActivateShopView`, `invito_portale_service`, `anagrafiche/models.py` (`IdentitaDigitale`) | via `deve_cambiare_password`, `tentativi_falliti`, `bloccato_fino_a`, `totp_obbligatorio` |
| Doc | `api_multi_veste_token.md`, `api_password_reset.md`, `api_token_cambio_password.md`, guida `architettura-multi-face-auth.md` §3.1 | le tre regole del brief §2; ⚠️ scrivere che `LoginRateThrottle` (5/5 min per IP, contro chi inonda l'endpoint) e il freno per provenienza (5 fallimenti, contro chi prova una credenziale) sono **due regole** anche se i numeri coincidono |

⛔ **Stessa PR del DB in `Tito-dev`** (brief §4): tolte le colonne, il login
attuale si rompe finché `auth_repository` non è allineato. I test col mock non
lo vedono: serve un test sul DB provvisto (`richiedi_db_provvisto`) che faccia
un login vero con un fallimento e un successo.

### 3.1-bis ✅ L-1 fatto (2026-09-25)

Sul P-1 applicato a dbdev (brief §11). Cosa c'e':

- `AuthRepository`: `check_blocco_login(uid, provenienza=)`,
  `registra_tentativo_login(uid, provenienza=, successo=)` (ritorna anche
  `attesa_secondi`), `azzera_tentativi_credenziale(uid)` nuovo,
  `get/set_deve_cambiare_password(uid)` sulle funzioni del DB — niente SQL
  diretto, niente `identita_id`. `apply_new_password` perde `identita_id`
  (cinque chiamanti).
- Login: provenienza da `get_client_ip`; se manca, `E_AUTH_CHIAMATA_NON_VALIDA`
  **prima** di cercare lo username (nessuna differenza fra utente esistente e
  no). Reset riuscito → azzeramento nella stessa transazione (D-2).
- Colonne tolte da `PortaleRepository` (`find_identita_portale`,
  `create_identita_portale` senza `deve_cambiare_password`), dai due chiamanti,
  dal model `IdentitaDigitale` (quattro campi).
- Policy rigenerate (5 codici), ripieghi dei 5 codici.
- ⭐ **Difetto preesistente trovato dal test sul DB vero**: la view
  intercettava `AuthenticationFailed` di **SimpleJWT**, sottoclasse di quello
  di DRF che il serializer solleva davvero ⇒ **nessuna password sbagliata
  arrivata dall'API e' mai stata contata**, prima del P-1 come dopo. Il test
  col mock era verde perche' sollevava la sottoclasse. Corretto l'import;
  test unitario ora sulla classe vera.
- ⭐ **Envelope vero** (non ipotizzato): `E_LOGIN_ATTESA` porta i secondi in
  `message`, e `detail` e' la **causa** del catalogo; `E_UTENTE_BLOCCATO` e' una
  frase chiusa, i minuti non arrivano all'envelope (restano nel contesto del
  DB). Il FE leggeva `detail || message`: con l'attesa avrebbe perso i secondi.
- Test: `apps/core/tests/db/test_login_credenziale_db.py` (8, DB vero, casi
  costruiti), `test_auth_views` (+3: provenienza assente, fallimento e successo
  con la provenienza), `test_password_reset` (+1: la view vera azzera dentro la
  transazione; prova di mutazione fatta).
- Doc: guida `architettura-multi-face-auth` §3.1 riscritta + §3.1-bis (le tre
  regole e il throttle come regola distinta); manual `auth_views_audit`,
  `api_multi_veste_token`, `api_password_reset`, `api_token_cambio_password`,
  `api_throttling`.
- ⚠️ **Resta aperto** (non L-1): `PasswordChangeRequiredMiddleware` e' inerte
  col JWT (A-8, L-6); i minuti del freno non arrivano al messaggio (servirebbe
  un `%s` nel messaggio di `E_UTENTE_BLOCCATO`, richiesta al DB se la si vuole);
  il testo di `E_UTENTE_BLOCCATO` dice «Account … bloccato» mentre ora e' frenata
  la sola provenienza (testo del catalogo, del DB: il login operatore usa ora
  la chiave i18n, §3.2, ma il catalogo resta da correggere per ogni altro
  lettore).
- ⚠️ **Oracolo sull'esistenza dello username** (preesistente, non introdotto
  da L-1): lo username inesistente non conta nulla, quindi resta 401 per
  sempre, mentre uno esistente dopo la soglia risponde 403 `E_UTENTE_BLOCCATO`.
  Chi prova sei password capisce se l'utente esiste. Il passo 0 del login
  (provenienza prima di cercare l'utente) chiude solo il suo caso.
  ✅ Tid, 2026-09-25: si corregge sul modello → §5 **R-7**; il testo del
  catalogo → §5 **R-8**.
- ⚠️ **Il login riuscito del test sul DB vero usa ancora un superuser
  esistente** (con `skip` dichiarato). ✅ Tid, 2026-09-25: va costruito, ma
  **si fa in L-3**: il caso si costruisce con la madre `fn_crea_operatore_v2`,
  e la madre cambia firma col P-2 (sotto).
- ⛔ **Il P-2 è già applicato su dbdev ma non è nel repo** (trovato il
  2026-09-25 costruendo il caso sopra): sul DB `fn_crea_operatore_v2` non ha
  più `p_attivo` e ritorna `TABLE(auth_user_id, username, credenziale_riusata)`,
  mentre `AmmSoftwareRepository.crea_operatore` e la doc auto-gen in git hanno
  ancora la firma vecchia ⇒ **la creazione di un operatore dall'app oggi
  fallisce su dbdev** («la funzione non esiste»). È il caso previsto «stessa PR
  del DB» di L-3: il BE non si allinea a una firma che non è in git; si
  allinea col changeSet del P-2.

### 3.2 L-1 — Frontend

✅ Fatto (2026-09-25), `core/views/LoginView.vue` `resolveLoginError`:

- `E_CREDENZIALE_BLOCCATA` → chiave i18n («Accesso bloccato
  dall'amministratore: contattalo»);
- `E_LOGIN_ATTESA` → `message` del DB, che porta i secondi (chiave di ripiego);
- `E_UTENTE_BLOCCATO` → chiave i18n: è una frase chiusa, il `message` del DB
  non porta nessun dato in più e non è tradotto. Il testo dice «da questa
  postazione» — il freno è sulla coppia, non sull'account;
- 5xx **e nessuna risposta** (rete, server spento) → messaggio tecnico, non
  più «accesso non autorizzato» né «credenziali errate»;
- chiavi i18n it/en.

**Revisione critica di L-1 (2026-09-25, a lavoro fatto).** Correzioni:
log `security.login_blocked` col **codice** del DB (prima un guasto e un
rifiuto davano la stessa riga di sicurezza) e `security.login_attesa` con la
provenienza; test sul DB vero: il savepoint si conferma solo su 200/401 (un
500 inatteso avvelenava le asserzioni successive), il caso «da un'altra
provenienza non è frenata» ora usa la password **giusta** e si ferma a
`E_VESTE_NON_ATTIVA` (prima usava quella sbagliata, e il commento diceva il
contrario), e la dipendenza dai parametri (tetto > soglia) è dichiarata con
uno `skip` invece di essere assunta.

### 3.3 L-2 — Blocco e sblocco dell'admin

**Backend** — `amm_software` (`AdminAPIView`, SUPER_ADMIN: la stessa regola
del verbo, D-B1):

- `POST /amm-software/operatori/<id>/blocca-credenziale/` `{motivo}` →
  `fn_blocca_credenziale`, poi **blacklist di tutte le sessioni** della
  credenziale; `Idempotency-Key` obbligatoria;
- `POST …/sblocca-credenziale/` → `fn_sblocca_credenziale`;
- il dettaglio operatore espone lo stato del blocco (`bloccata_at`,
  `bloccata_da`, `motivo_blocco`) — lettura attraverso una funzione del DB
  (le tabelle sono chiuse all'app, brief §2.2): ⚠️ **il brief non la elenca**
  → §5 R-6;
- `E_PROFILO_ULTIMO_SUPER_ADMIN` (anti-lockout) tradotto come oggi per la
  disattivazione.

⚠️ La porta sta nella scheda **operatore**, ma la credenziale è di chiunque:
un cliente portale senza veste operatore non si raggiunge da lì. Per ora va
bene (la gestione accessi è `amm_software`), ed è scritto qui perché non
sembri una scelta: la porta per le credenziali senza veste operatore si decide
col roll-out portale/shop.

**Frontend** — `amministrazione/components/OperatoreDrawer.vue` (+ store
`operatori.js`, api `amministrazione.js`): pulsanti «Blocca accesso» (con
dialog che chiede il motivo) e «Sblocca», etichetta «Accesso bloccato il … da
… — motivo» quando lo è. Il pulsante di blocco resta **spento col motivo** se
l'operatore è l'ultimo SUPER_ADMIN (capability, non un 409 a sorpresa).

---

## 4. L-3 … L-6

### 4.1 L-3 — Una persona, una credenziale; invito e attivazione operatore

| Pezzo | Cosa cambia |
| --- | --- |
| `AmmSoftwareService.create_operatore` | gestisce la credenziale **riusata** (ritorno della madre, brief §5.2): se riusata, la password inserita dall'admin è ignorata e la risposta lo dice |
| FE `OperatoreDrawer` (creazione) | se la credenziale è stata riusata: avviso «questa persona ha già un accesso: userà la sua password; riceverà l'invito per attivare la veste operatore» |
| `anagrafiche/services/invito_operatore_service.py` | ⛔ **non sovrascrive più la password** (A-1); flusso scelto sulla credenziale come il portale (password vera → attivazione con un clic, altrimenti scelta della password); reinvio con invalidazione **nella stessa transazione** (A-4) |
| `core/api/attivazione_view.py` | l'attivazione **accende la veste** nella stessa transazione del consumo (A-3), come portale e shop; `identita_id` del token **obbligatorio** (oggi facoltativo, con azzeramento su tutte le vesti) |
| Guard «ha già accesso» (D-8) | «veste OPERATORE già attiva → rifiuto» al posto di `last_login` → §5 R-1 |
| Ultimo accesso (D-8) | il login riuscito scrive `auth_user.last_login` (SimpleJWT `UPDATE_LAST_LOGIN`, o esplicito nella view: la scelta dipende da quale dei due passa dal serializer multi-veste — da verificare nel lotto) |
| FE | «Ultimo accesso» nel dettaglio operatore |

⭐ **Regola del 2 da dichiarare prima di scrivere** (memoria di progetto):
invito operatore e invito portale/shop diventano la **stessa** logica (credenziale,
veste spenta, token, reinvio atomico). La sede naturale è un building block unico
d'invito veste in `core`, con la configurazione per veste (`_VESTE_CONFIG`
esiste già) — e con lui le **due** view di attivazione portale/shop, oggi copie
all'80% (debito già dichiarato nel catalogo), più quella operatore. Si propone
a Tid all'apertura del lotto, con l'elenco delle copie che si ritirano.

### 4.2 L-4 — Chiave d'ingresso per porta (D-9)

- **Backend**: i serializer di `portale/token/` e `shop/token/` accettano
  l'**email** (confronto senza maiuscole, sull'indice unico del brief §5.1);
  `admin/token/` resta sul nome utente. Il reset password accetta l'email per
  le credenziali che hanno una veste portale/shop.
- **Nome utente nell'invito operatore**: variabile nel template email
  `INVITO_OPERATORE`, che sta a DB → §5 R-3.
- **Frontend**: oggi l'unica pagina di login è quella operatore
  (`LoginView`, canale ADMIN forzato); portale e shop **non hanno ancora una
  pagina di login**. ⇒ La parte FE di D-9 nasce con quelle pagine; qui si
  aggiornano la pagina di attivazione conclusa (portale/shop: «entra con la tua
  email») e il reset password (campo «nome utente o email»).
- ⚠️ Prima che il DB applichi l'indice unico: il controllo **a mano** delle
  coppie di email sui dati di sviluppo (brief §5.1, §7).

### 4.3 L-5 — Disattivazione per veste, revoca, sessioni (M-5, M-6, D-3, D-4, D-5)

| Pezzo | Cosa cambia |
| --- | --- |
| `amm_software_repository.disabilita_operatore` | tocca **solo la veste OPERATORE** (oggi tutte le identità della credenziale, M-5); `ruolo_applicativo` **invariato** (§6 Q-2); la risorsa umana resta com'è oggi |
| `riattiva_operatore` + endpoint `…/riattiva/` | **ritirati** (D-3, chiude M-6): si riattiva col reinvio. FE: il pulsante «Riattiva» diventa «Reinvia invito» |
| Revoca (D-4) | disattivare **dall'admin** marca la veste come revocata → §5 R-4; `ProfileActivateShopView` rifiuta una veste revocata; FE `AttivaAccessoShopButton` spento col motivo, `PortaleAccessoPanel` mostra «revocato» |
| Sessioni (D-5) | un BB unico «chiudi le sessioni di una veste»: blacklist degli `OutstandingToken` della credenziale il cui claim `identita_id` è quello della veste. Usato da operatore, portale e shop. ⚠️ oggi `disabilita_operatore` chiude **tutte** le sessioni, portale/shop **nessuna** |
| Stessi effetti per tutte le vesti (A-5) | invalidazione dei token d'invito pendenti **e** della cache permessi anche su portale/shop (oggi solo operatore la seconda, solo portale/shop la prima) |
| Test | ⭐ M-6 **costruito**: credenziale con veste operatore + cliente portale → disattiva operatore → il portale resta attivo, il cliente entra; reinvio → attivazione → operatore di nuovo attivo, cliente intatto. Sul DB provvisto |

### 4.4 L-6 — Validità al login e cambio password obbligatorio (A-7, A-8)

- `AuthRepository.find_identita_attiva_for_ruoli` e la CTE di `set_jwt_gucs`
  aggiungono la **finestra** `valido_dal`/`valido_al` (oggi solo `attivo`):
  una veste scaduta non entra, anche se la credenziale ha un'altra veste valida.
  ⚠️ Stessa espressione in due sedi Python-SQL: si estrae un frammento comune,
  non si riscrive due volte.
- `PasswordChangeRequiredMiddleware` è inerte col JWT (a `process_view` il
  `request.user` è anonimo — stesso schema di S-2). Il controllo si sposta
  **dopo** l'autenticazione DRF, nella sede che conosce utente e veste
  (`JwtAuditAuthentication`, o una permission comune): prima una **prova reale**
  che oggi non scatti, poi la correzione. Resta la whitelist (cambio password,
  logout, `/me/`).

---

## 5. Richieste al team DB **non** ancora nel brief

Il brief ha escluso di proposito la parte «per veste» (§10). R-1…R-6 servono ai
lotti L-3, L-4, L-5 e L-2; vanno in un secondo brief, da scrivere all'apertura
di quei lotti. R-7 e R-8 sono nate dalla revisione di L-1 (2026-09-25) e non
dipendono dalle vesti: possono partire da sole.

| # | Richiesta | Per |
| --- | --- | --- |
| R-1 | `script.fn_check_operatore_invitabile`: via la condizione `last_login IS NULL` e «veste OPERATORE già attiva» come rifiuto; ⚠️ oggi pretende l'identità **attiva** per invitare — con la veste che nasce spenta va rovesciata | L-3, D-8 |
| R-2 | La madre `fn_crea_operatore_v2` crea la veste OPERATORE **non attiva** anche per una credenziale **nuova** (il brief §5.2 lo chiede solo per quella riusata) | L-3 |
| R-3 | Template `INVITO_OPERATORE` con la variabile del nome utente | L-4, D-9 |
| R-4 | La veste ricorda di essere stata **revocata** dall'admin (chi, quando), e la riattivazione self-service la rifiuta (sede della regola: DB) | L-5, D-4 |
| R-5 | `DISABILITATO` **si ritira** come valore di `ruolo_applicativo` (§6 Q-2, deciso): la sua sorte nel tipo `config.ruolo_applicativo` e nei lettori (`fn_is_super_admin`, catena permessi, `trgfn_identita_digitali_guard_coerenza` che oggi lo esenta); le righe che oggi lo portano tornano al ruolo che avevano (dati di sviluppo, a mano) | L-5 |
| R-6 | Una funzione di lettura dello stato di blocco dell'admin (`bloccata_at`, `bloccata_da`, `motivo_blocco`) per il dettaglio operatore: le tabelle sono chiuse all'app | L-2 |
| R-7 | **La risposta del login non dipende dall'esistenza dello username** (✅ Tid, 2026-09-25). Oggi il freno e l'attesa hanno per chiave la **credenziale**: un nome inesistente non conta nulla e resta 401 per sempre, uno esistente dopo la soglia risponde 403 `E_UTENTE_BLOCCATO` (e oltre il tetto `E_LOGIN_ATTESA`) ⇒ chi prova sei password sa se l'utente esiste. La regola, sul modello: **il freno e l'attesa valgono per il NOME TENTATO**, esista o no. Per un nome inesistente, stessa soglia, stesso tetto, stessi codici, stesse due chiamate (check prima, registrazione dopo), così nemmeno il numero di chiamate al DB distingue i due casi. Vincoli: ⛔ il nome **non** si salva in chiaro (nel campo username finiscono anche delle password digitate lì per sbaglio): un hash del nome **normalizzato con la stessa regola del lookup** (oggi uguaglianza esatta sullo username; con L-4 email senza maiuscole, e la normalizzazione deve seguirla); righe con `cleanup_at` come `credenziali_provenienze`; nessuna riga in `config.credenziali` per un nome che non è una credenziale. La forma (tabella a parte o parametro nuovo delle stesse funzioni) la sceglie il DB. ⚠️ Due punti da decidere col brief: (a) hash semplice o HMAC con una chiave del backend: l'hash semplice di una password finita nel campo username si può attaccare offline; (b) `E_CREDENZIALE_BLOCCATA` continua a rivelare che il nome esiste, ma solo per una credenziale bloccata dall'admin, e al titolare quella frase serve per sapere a chi rivolgersi: proposta, **accettarlo e dichiararlo** | L-1 (chiusura) |
| R-8 | Testo di `E_UTENTE_BLOCCATO` in `messaggi_errore.csv` (✅ Tid, 2026-09-25): oggi dice «Account temporaneamente bloccato per troppi tentativi.», ma il freno riguarda la sola **coppia credenziale + provenienza**, e da un'altra postazione si entra. Proposta: «Troppi tentativi non riusciti da questa postazione: accesso sospeso per qualche minuto.» (lo stesso testo della chiave i18n del login, §3.2). Il BE poi riallinea il ripiego in `error_messages_fallback.py`, **dopo** il changeSet: mai prima, o il ripiego sarebbe avanti rispetto al catalogo | L-1 (chiusura) |

---

## 6. Domande a Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| Q-1 | **Quanti proxy stanno davanti al backend** in produzione? Serve a sapere di quale hop di `X-Forwarded-For` fidarsi (L-0) | ✅ **Tid, 2026-09-24**: niente produzione; si prevede **Nginx come nell'ambiente di sviluppo**, quindi **1**. ⭐ Nginx (playbook) *aggiunge* l'IP vero in coda (`$proxy_add_x_forwarded_for`): il valore fidato è l'N-esimo **da destra**. ⛔ Il numero sbagliato è un difetto **muto** nei due versi: troppo basso ⇒ tutti gli utenti hanno l'IP di Nginx, e 5 errori di chiunque frenano **tutti**; troppo alto ⇒ si torna a fidarsi di un valore del client. ⇒ Setting **obbligatorio** in `env.sh` (nessun default: senza, il backend non parte), `1` nell'ambiente di sviluppo, e una riga nel playbook: *se cambia la catena davanti al backend (un secondo proxy, un bilanciatore), si aggiorna questo numero* |
| Q-2 | Con la disattivazione per veste, `ruolo_applicativo = 'DISABILITATO'` non serve più (la veste spenta è `attivo = false`, e il ruolo resta quello che era). Lo si ritira? | ✅ **Tid, 2026-09-24: sì, si ritira** — oggi la stessa informazione vive in due campi (`attivo` e il ruolo), ed è così che la riattivazione ha perso il ruolo originale (M-6). Sorte del valore nel tipo e nei lettori: §5 R-5 |
| Q-3 | La parte FE di D-9 (login per email) aspetta le pagine di login di portale e shop, che non esistono ancora? | ✅ **Tid, 2026-09-24: sì** — qui solo attivazione conclusa e reset |

---

## 7. Ordine proposto

1. **L-0** e **L-6** subito (nessuna dipendenza).
2. **L-1 + L-2** col changeSet P-1, in un'unica PR con il DB.
3. **L-3 + L-4** col P-2 e con R-1…R-3.
4. **L-5** con R-4, R-5.

Ogni lotto chiude le sue righe nell'analisi e i «⚠️ Difetto noto» nelle doc
`manual/` che rimandano a M-4, M-5, M-6.

---
{% include-markdown "signature-core.md" %}

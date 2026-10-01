# Piano BE/FE — Accessi: una credenziale, più vesti, un ciclo di vita solo

> **Tipo documento**: piano di lavoro backend + frontend (`dev/backend-tid`).
>
> **Data**: 2026-09-24 · **Stato** (riallineato il 2026-09-28): 🟡 **IN
> CORSO** — ✅ L-0 fatto (2026-09-24, §2); ✅ L-1 fatto (2026-09-25, §3.1-bis);
> 🟡 L-3 fatto tranne il consenso al riuso (A-9, §4.1-bis), **sbloccato**: la
> rev `-51` è in git dal `64a1ad2f4`; ⏳ **L-2, L-4, L-5, L-6 da fare**. ✅ R-3,
> R-7, R-9 lato BE/FE scritti il 2026-09-25 (brief DB §13–§15 e registro).
> ⏳ R-4, R-5, R-6 aspettano il **secondo brief DB**, non ancora scritto (§5).
> Le tre domande di §6 sono decise (Tid, 2026-09-24).
>
> ⭐ **Questo piano è la sede unica del lavoro che resta** del cantiere accessi:
> l'analisi è chiusa (2026-09-28) e sta in `work-done/`. Le sigle ancora aperte
> sono riassunte qui sotto, §0.
>
> **Da dove viene**: [analisi-accessi-credenziale-e-vesti.md](../work-done/analisi-accessi-credenziale-e-vesti.md)
> (inventario, difetti M-4/M-5/M-6 e A-1…A-9, decisioni D-1…D-10) e
> [brief-db-blocco-login-per-credenziale.md](../work-done/brief-db-blocco-login-per-credenziale.md)
> (la forma DB di tentativi, blocco, cambio password obbligatorio ed email,
> con le decisioni D-B1…D-B5). Questo piano non ripete il perché: lo rimanda.
>
> **Regola di lettura**: ogni lotto dice **da cosa dipende** (changeSet del
> brief, oppure nulla) e **cosa chiude** (le sigle dell'analisi). Un lotto che
> dipende dal DB non parte prima del suo changeSet
> (memoria di progetto: BE/FE solo con i prerequisiti DB pronti).

---

## 0. Le sigle ancora aperte (2026-09-28)

Il perché di ognuna sta nell'[analisi](../work-done/analisi-accessi-credenziale-e-vesti.md)
§3 e §5; qui solo **cosa** e **dove si chiude**.

| Sigla | Cosa | Lotto |
| --- | --- | --- |
| **M-5** | Disattivare un operatore spegne **tutte** le vesti della credenziale e le rinomina `DISABILITATO`. ⚠️ **Due strade**, non una (verifica 2026-09-28, [analisi difetti core](analisi-be-difetti-emersi-verifica-doc-api-core.md) M-5): `disabilita_operatore` **e** `update_operatore` con `attivo=False` via `_set_identita_state` — quella **viva**, l'interruttore di `OperatoreDrawer.vue`. §4.3 va letto per tutte e due | L-5 |
| **M-6** | Riattivare un operatore porta a `OPERATORE` tutte le sue identità (con una veste cliente i vincoli la fanno fallire). Anche qui due strade: `riattiva_operatore` **e** `update_operatore` con `attivo=True`. Prova con caso costruito prima della correzione | L-5 |
| **A-5** | Revoca asimmetrica: blacklist, token d'invito e cache permessi presenti in un flusso e assenti nell'altro | L-5 |
| **A-6** | Lo shop si riattiva da solo (`ProfileActivateShopView`) anche dopo una revoca dell'admin (D-4) | L-5 (R-4) |
| **A-7** | `valido_dal`/`valido_al` della veste non applicati al login né a ogni richiesta | L-6 |
| **A-8** | `PasswordChangeRequiredMiddleware` inerte col JWT: il cambio obbligatorio lo fa rispettare solo il FE | ➡️ **T-0** del [brief sicurezza](brief-be-fe-sicurezza-header-token-mfa.md) §3.4-bis (Tid, 2026-09-30): un cancello degli obblighi per cambio password **e** secondo fattore. In L-6 resta A-7 |
| **A-9** | Resta il consenso dell'admin al riuso della credenziale (rev `-51`, già in git) | L-3 (coda) |
| **D-1** | Il blocco **vero** è un verbo dell'admin: nessun endpoint `blocca-credenziale` ancora | L-2 (R-6) |
| **D-9** | Portale e shop entrano con l'email; nome utente nell'invito operatore | L-4 |

⭐ **L-6 non dipende dal DB** (§7): si può fare subito.

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

> ⛔ **Stato al 2026-09-25 (verificato su dbdev dopo il P-2, commit
> `acc6385d5`)**: il DB di L-3 è pronto (R-1, R-2, brief §12.4 B-1…B-5), il
> backend no, e su dbdev **l'ingresso di un operatore nuovo è rotto in tre
> punti in fila**, non in uno:
> 1. **creazione** — `AmmSoftwareRepository.crea_operatore` passa `p_attivo` e
>    legge un `integer`: «la funzione non esiste» (B-1);
> 2. **invito** — `fn_check_operatore_invitabile` ora dice «invitabile» solo con
>    la veste **spenta**, ma `InvitoOperatoreService.invia_invito` cerca poi la
>    veste con `find_identita_attiva_for_ruoli`, cioè **attiva**: le due regole
>    si escludono, e ogni invito risponde `E_INVITO` «Identita operatore non
>    trovata o non attiva». ⚠️ Il brief (B-2) non lo nomina;
> 3. **attivazione** — `AttivazioneView` non accende la veste (A-3): anche
>    sistemati 1 e 2, l'operatore non entrerebbe mai.
>
> ⇒ B-1 da solo non basta: 1, 2 e 3 escono **insieme**. E con il riuso della
> credenziale già vivo, l'invito che sovrascrive la password (A-1) oggi
> distruggerebbe quella di un cliente portale: stessa urgenza.

| Pezzo | Cosa cambia |
| --- | --- |
| `AmmSoftwareService.create_operatore` | gestisce la credenziale **riusata** (ritorno della madre, brief §5.2): se riusata, la password inserita dall'admin è ignorata e la risposta lo dice |
| FE `OperatoreDrawer` (creazione) | se la credenziale è stata riusata: avviso «questa persona ha già un accesso: userà la sua password; riceverà l'invito per attivare la veste operatore» |
| `anagrafiche/services/invito_operatore_service.py` | ⛔ **non sovrascrive più la password** (A-1); flusso scelto sulla credenziale come il portale (password vera → attivazione con un clic, altrimenti scelta della password); reinvio con invalidazione **nella stessa transazione** (A-4) |
| `core/api/attivazione_view.py` | l'attivazione **accende la veste** nella stessa transazione del consumo (A-3), come portale e shop; `identita_id` del token **obbligatorio** (oggi facoltativo, con azzeramento su tutte le vesti) |
| Guard «ha già accesso» (D-8) | «veste OPERATORE già attiva → rifiuto» al posto di `last_login` → §5 R-1 |
| Ultimo accesso (D-8) | il login riuscito scrive `auth_user.last_login` (SimpleJWT `UPDATE_LAST_LOGIN`, o esplicito nella view: la scelta dipende da quale dei due passa dal serializer multi-veste — da verificare nel lotto) |
| FE | «Ultimo accesso» nel dettaglio operatore |

⭐ **Regola del 2** — ✅ building block unico, ok Tid 2026-09-25.

### 4.1-bis 🟡 L-3 fatto, tranne il consenso al riuso (2026-09-25)

**Il building block** (`apps/core/services/invito_veste.py` +
`apps/core/api/attivazione_veste_views.py`; FE `AttivazioneVestePage` +
`core/api/attivazioneVeste.js`): operatore, portale e shop passano da una strada
sola; fra le vesti cambia la **porta** (token, template, link, codici). Copie
ritirate e dettaglio nel catalogo BB backend, sezione «Invito e attivazione di
una veste».

| Pezzo | Fatto |
| --- | --- |
| Creazione (B-1) | `crea_operatore` sulla madre P-2 (`SELECT … FROM fn_crea_operatore_v2`, senza `p_attivo`); la risposta porta `credenziale_riusata`. ⛔ L'admin **non sceglie più la password**: credenziale nuova col segnaposto non utilizzabile (regola unica §4.2 dell'analisi), `password` nel payload rifiutato; FE senza campi password e con l'avviso di riuso |
| Invito (B-2, A-1, A-4) | sulla veste OPERATORE **spenta** (l'unica: più d'una → rifiuto), nessuna password toccata, flusso sulla credenziale, reinvio con i token **della veste** invalidati nella stessa transazione |
| Attivazione (A-3) | accende la veste; `identita_id` obbligatorio; flusso con un clic anche per l'operatore (token nuovo `ATTIVAZIONE_OPERATORE_CROSS`) |
| B-3 | `PortaleRepository.find_auth_user_by_email` → `script.fn_get_auth_user_id_for_email` |
| B-4 | policy e ripieghi dei due codici P-2: già fatti dall'altra sessione |
| D-8 | il login riuscito scrive `last_login` (nella view, **dopo** il controllo della veste: `UPDATE_LAST_LOGIN` lo scriverebbe anche per chi ha la password giusta e nessuna porta); FE «Ultimo accesso» |
| FE drawer | «Invia invito» sulla capability `can_invite` del DB (il FE ricopiava `!last_login && is_active`, che con la veste spenta non era **mai** vero), motivo del DB se non invitabile |

⭐ **Difetti trovati facendolo** (tutti chiusi nello stesso giro):

- l'invalidazione dei token e lo stato «PENDING» erano **per credenziale**:
  cliente e fornitore portale della stessa persona condividono i tipi, e il
  reinvio dell'uno spegneva l'invito dell'altro → per **veste**
  (`meta.identita_id`);
- un token INVITO su una credenziale che **nel frattempo** ha una password
  vera la sovrascriveva → la credenziale decide anche all'attivazione
  (`richiede_password`);
- le tre pagine FE di attivazione dicevano «link non valido» (e toglievano il
  form) anche per una **password rifiutata dalla policy**: stesso codice
  d'errore → la pagina ri-verifica il token;
- `"azienda": "ZeroErp"` scritto a mano in quattro punti → `NOME_SISTEMA_EMAIL`.

**Prove**: `apps/core/tests/services/test_invito_veste.py` (BB, 20),
`test_invito_operatore` riscritto, cablaggio per porta nei test di portale e
shop, `test_amm_software_service` / `test_crea_operatore` sul contratto nuovo;
⭐ **sul DB vero** `test_login_credenziale_db.CicloOperatoreDbTests`: madre →
invito → attivazione → login 200 + `last_login`, tutto costruito (chiude anche il
«login riuscito preso da un superuser esistente» di §3.1-bis).

⏸️ **Resta: il consenso al riuso (rev -51 della madre, brief §12.7).** Su
dbdev la madre ha già `p_riusa_auth_user_id` ed `E_CREDENZIALE_DA_CONFERMARE` /
`E_CREDENZIALE_ALTRA_PERSONA`, in git **non ancora**. Il backend chiama la madre
per nome senza quel parametro, quindi va con tutte e due le versioni; oggi su
dbdev una email già usata risponde `E_CREDENZIALE_DA_CONFERMARE`. Quando la -51
è in git: `riusa_auth_user_id` nel payload di creazione → madre; FE dialog «questa
email è di X: usare il suo accesso?» sul contesto del codice; il test
`test_credenziale_riusata_un_clic_e_password_intatta` (oggi `skip` dichiarato)
esercita il consenso.

⭐ **Revisione critica del lotto (2026-09-25)** — quattro difetti, chiusi:

- ⛔ **il «per veste» era vero solo coi mock**: `TokenRepository.create`
  invalidava ancora per **tipo e credenziale**, quindi l'invito della veste
  fornitore portale spegneva quello pendente della veste cliente della stessa
  persona — il difetto che il lotto dichiarava chiuso. `create` ora non
  invalida niente; l'emissione del BB invalida **sempre** i token della veste
  (primo invito o reinvio: un link vivo per veste, via il flag `reinvio`), il
  reset password invalida da sé nella propria transazione. Prova sul DB vero:
  `apps/core/tests/db/test_token_veste_db.py`, **rossa** sul codice di prima;
  chiude anche l'altra metà di F-3 (`invita` lasciava due link validi);
- drawer operatore: il motivo del «non invitabile» si nascondeva con `u.attivo`,
  che nel dettaglio è `risorse_umane.attivo` e non la veste — cioè proprio per
  l'operatore appena creato. Ora si mostra sempre quando l'invito non è
  ammesso (anche «veste già attiva»): vedi R-9;
- pagina di attivazione: dopo il successo il pulsante restava attivo, e un
  secondo clic, ri-verificando il token consumato, sostituiva l'esito con
  «link non valido»;
- pulizia: SQL di lettura del nome fuori dal service (`AuthRepository.get_nomi_credenziale`,
  seconda copia di `_get_user_names` dell'operatore), `codiceErrore` morto in
  `PORTE_ATTIVAZIONE`, `conPassword` restituito e mai letto, codice
  `E_INVITO_PORTALE` riscritto a mano invece che preso dalla porta.

⚠️ **Richieste nuove al DB** → §5 R-3 (esteso), R-9.

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
- ➡️ **Spostato in T-0** del brief sicurezza §3.4-bis (Tid, 2026-09-30): il
  cancello nasce per due obblighi, cambio password e secondo fattore. Il testo
  sotto resta come origine.
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
| R-1 | `script.fn_check_operatore_invitabile`: via la condizione `last_login IS NULL` e «veste OPERATORE già attiva» come rifiuto; ⚠️ oggi pretende l'identità **attiva** per invitare — con la veste che nasce spenta va rovesciata. ✅ **Consegnata nel P-2** (`20260925-43`, brief §12) | L-3, D-8 |
| R-2 | La madre `fn_crea_operatore_v2` crea la veste OPERATORE **non attiva** anche per una credenziale **nuova** (il brief §5.2 lo chiede solo per quella riusata). ✅ **Consegnata nel P-2** (`20260925-42`, brief §12) | L-3 |
| R-3 | Template `INVITO_OPERATORE` con la variabile del nome utente. ⚠️ **Esteso** (L-3, 2026-09-25): i template `INVITO_OPERATORE` e `INVITO_PORTALE` dicono sempre «imposta la password», anche nel flusso con un clic; il backend passa `is_cross` a tutti e tre (`INVITO_SHOP` lo dichiara già fra le variabili, ma il testo non lo usa). Serve il ramo «attiva l'accesso con le credenziali che hai già» | L-4, D-9, L-3 |
| R-4 | La veste ricorda di essere stata **revocata** dall'admin (chi, quando), e la riattivazione self-service la rifiuta (sede della regola: DB) | L-5, D-4 |
| R-5 | `DISABILITATO` **si ritira** come valore di `ruolo_applicativo` (§6 Q-2, deciso): la sua sorte nel tipo `config.ruolo_applicativo` e nei lettori (`fn_is_super_admin`, catena permessi, `trgfn_identita_digitali_guard_coerenza` che oggi lo esenta); le righe che oggi lo portano tornano al ruolo che avevano (dati di sviluppo, a mano) | L-5 |
| R-6 | Una funzione di lettura dello stato di blocco dell'admin (`bloccata_at`, `bloccata_da`, `motivo_blocco`) per il dettaglio operatore: le tabelle sono chiuse all'app | L-2 |
| R-7 | **La risposta del login non dipende dall'esistenza dello username** (✅ Tid, 2026-09-25). Oggi il freno e l'attesa hanno per chiave la **credenziale**: un nome inesistente non conta nulla e resta 401 per sempre, uno esistente dopo la soglia risponde 403 `E_UTENTE_BLOCCATO` (e oltre il tetto `E_LOGIN_ATTESA`) ⇒ chi prova sei password sa se l'utente esiste. La regola, sul modello: **il freno e l'attesa valgono per il NOME TENTATO**, esista o no. Per un nome inesistente, stessa soglia, stesso tetto, stessi codici, stesse due chiamate (check prima, registrazione dopo), così nemmeno il numero di chiamate al DB distingue i due casi. Vincoli: ⛔ il nome **non** si salva in chiaro (nel campo username finiscono anche delle password digitate lì per sbaglio): un hash del nome **normalizzato con la stessa regola del lookup** (oggi uguaglianza esatta sullo username; con L-4 email senza maiuscole, e la normalizzazione deve seguirla); righe con `cleanup_at` come `credenziali_provenienze`; nessuna riga in `config.credenziali` per un nome che non è una credenziale. La forma (tabella a parte o parametro nuovo delle stesse funzioni) la sceglie il DB. ⚠️ Due punti da decidere col brief: (a) hash semplice o HMAC con una chiave del backend: l'hash semplice di una password finita nel campo username si può attaccare offline; (b) `E_CREDENZIALE_BLOCCATA` continua a rivelare che il nome esiste, ma solo per una credenziale bloccata dall'admin, e al titolare quella frase serve per sapere a chi rivolgersi: proposta, **accettarlo e dichiararlo** | L-1 (chiusura) |
| R-8 | Testo di `E_UTENTE_BLOCCATO` in `messaggi_errore.csv` (✅ Tid, 2026-09-25): oggi dice «Account temporaneamente bloccato per troppi tentativi.», ma il freno riguarda la sola **coppia credenziale + provenienza**, e da un'altra postazione si entra. Proposta: «Troppi tentativi non riusciti da questa postazione: accesso sospeso per qualche minuto.» (lo stesso testo della chiave i18n del login, §3.2). Il BE poi riallinea il ripiego in `error_messages_fallback.py`, **dopo** il changeSet: mai prima, o il ripiego sarebbe avanti rispetto al catalogo | L-1 (chiusura) |
| R-9 | `script.fn_get_operatore_detail` porti lo stato della **veste** OPERATORE (es. `veste_attiva`): oggi `attivo` è quello della risorsa umana e `is_active` quello della credenziale (derivato da **tutte** le vesti), e il FE non ha come distinguere «veste già attiva» dagli altri motivi del non invitabile se non leggendo il testo. ⚠️ La join sulla veste OPERATORE è senza filtro: con più vesti OPERATORE spente (il modello le ammette) il dettaglio restituisce più righe | L-3 (drawer) |

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

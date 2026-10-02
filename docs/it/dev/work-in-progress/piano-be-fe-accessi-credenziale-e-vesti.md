# Piano BE/FE — Accessi: una credenziale, più vesti, un ciclo di vita solo

> **Tipo documento**: piano di lavoro backend + frontend (`dev/backend-tid`).
>
> **Data**: 2026-09-24 · **Stato** (riallineato al codice e al DB il
> 2026-10-02): 🟡 **IN CORSO** — ✅ **L-0** (2026-09-24, §2), ✅ **L-1**
> (2026-09-25, §3.1-bis), ✅ **L-3** intero, consenso al riuso compreso (A-9:
> B-20/F-4 il 2026-09-27, collaudo a video eseguito il 2026-10-02, §4.1-bis);
> ✅ **A-8** chiuso fuori dal piano dal **T-0** del brief sicurezza
> (`af9c6f659`, 2026-10-01); ✅ R-1, R-2, R-3, R-7, R-8, R-9 consegnati dal DB
> e allineati dal BE/FE (§5). 🟡 **L-5 iniziato**: i comandi dell'operatore
> toccano la sola veste operatore (2026-10-02, §4.3).
> ⏳ **Da fare**: L-2, L-4, il resto di L-5, L-6 (solo A-7).
> ⏳ **R-4, R-5, R-6 aspettano il secondo brief DB, ancora non scritto**
> (verificato il 2026-10-02: nessun brief in `work-in-progress/` né in
> `work-done/`; sul DB `DISABILITATO` è ancora nel tipo, `identita_digitali`
> non ha la revoca, nessuna funzione legge lo stato del blocco).
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

## 0. Le sigle ancora aperte (2026-10-02)

Il perché di ognuna sta nell'[analisi](../work-done/analisi-accessi-credenziale-e-vesti.md)
§3 e §5; qui solo **cosa** e **dove si chiude**.

| Sigla | Cosa resta | Lotto |
| --- | --- | --- |
| **M-5** | 🟡 Metà chiusa il 2026-10-02: le due strade (`disabilita_operatore` e `update_operatore` con `attivo=False`, l'interruttore di `OperatoreDrawer.vue`) toccano ora la **sola veste operatore** (`_VESTE_OPERATORE`, §4.3). Resta: la veste spenta prende ancora `ruolo_applicativo = DISABILITATO` (R-5), e le sessioni non sono per veste (D-5) | L-5 (R-5) |
| **M-6** | 🟡 Il difetto («tutte le identità a `OPERATORE`») è chiuso dallo stesso `_VESTE_OPERATORE`, con caso costruito. Resta la decisione D-3: **ritirare la riattivazione diretta** — `riattiva_operatore` **e** `update_operatore` con `attivo=True` — e riattivare col reinvio | L-5 |
| **A-5** | Revoca asimmetrica: `disabilita_operatore` chiude le sessioni (tutte quelle della credenziale) e la cache, ma non i token d'invito pendenti; l'interruttore (`update_operatore`, `attivo=False`) solo la cache; portale/shop invalidano i token d'invito, ma non chiudono sessioni né cache | L-5 |
| **A-6** | Lo shop si riattiva da solo (`ProfileActivateShopView`) anche dopo una revoca dell'admin (D-4) | L-5 (R-4) |
| **A-7** | `valido_dal`/`valido_al` della veste non applicati al login né a ogni richiesta | L-6 |
| **D-1** | Il blocco **vero** è un verbo dell'admin: i verbi DB ci sono (`fn_blocca_credenziale`, `fn_sblocca_credenziale`), l'endpoint e il FE no | L-2 (R-6) |
| **D-9** | Portale e shop entrano con l'email; il reset accetta l'email. ✅ Il nome utente nell'invito operatore è fatto (R-3, B-15) | L-4 |

✅ **Chiuse dopo il 2026-09-28**: **A-8** dal T-0 del
[brief sicurezza](../work-done/brief-be-fe-sicurezza-header-token-mfa.md)
§3.4-bis (`apps/core/api/cancello_obblighi.py`, `PasswordChangeRequiredMiddleware`
ritirato; `af9c6f659`, 2026-10-01); **A-9** dal
[brief credenziale per email](../work-done/brief-db-credenziale-per-email.md)
(B-20, F-4; `e7be8858b`, 2026-09-27; collaudo eseguito il 2026-10-02).

⭐ **L-6 non dipende dal DB** (§4.4): si può fare subito. **L-4** nemmeno: il
suo prerequisito DB (indice unico sull'email, P-2) è in vigore.

---

## 1. I lotti in una tabella

| Lotto | Cosa | Dipende da | Chiude | Stato (2026-10-02) |
| --- | --- | --- | --- | --- |
| **L-0** | L'IP del chiamante, fidato | niente (§6 Q-1) | prerequisito di L-1 | ✅ 2026-09-24 |
| **L-1** | Login su tentativi, freno, attesa; cambio password obbligatorio per credenziale; azzeramento al reset | brief **P-1** | M-4, D-1 (il freno), D-2, D-7 | ✅ 2026-09-25, con R-7 e R-8 |
| **L-2** | Blocco e sblocco dell'admin | P-1 (§3.3, ✅ a DB) + **R-6** | D-1 (blocco vero) | ⏳ aspetta R-6 |
| **L-3** | Una persona, una credenziale; invito e attivazione operatore sulla regola unica; ultimo accesso | P-2, R-1, R-2, R-9, brief credenziale per email | D-6, D-8, A-1, A-2, A-3, A-4, A-9 | ✅ 2026-09-27 (collaudo 2026-10-02) |
| **L-4** | Portale e shop entrano con l'email; il nome utente nell'invito operatore | P-2 (indice email, ✅) + R-3 (✅) | D-9 | 🟡 nome utente nell'invito fatto; login e reset per email da fare, nessuna dipendenza |
| **L-5** | Disattivazione per veste, niente riattivazione diretta, revoca che tiene, sessioni per veste | **R-4, R-5** | M-5, M-6, D-3, D-4, D-5, A-5, A-6 | 🟡 sola veste operatore fatta (2026-10-02); il resto aspetta il secondo brief DB |
| **L-6** | Validità della veste al login e a ogni richiesta | niente | A-7 (A-8 ➡️ T-0, ✅) | ⏳ da fare |

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

✅ Fatto: il disegno (tabella dei pezzi e «stessa PR del DB») è stato eseguito
il 2026-09-25 ed è nel brief DB §7; qui resta il resoconto, §3.1-bis.
~~La tabella dei pezzi~~ è stata tolta il 2026-10-02: nominava ancora
`PasswordChangeRequiredMiddleware` fra i chiamanti, ritirato dal T-0.

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
- ✅ **Le code di L-1, chiuse** (verifica 2026-10-02):
  - ~~`PasswordChangeRequiredMiddleware` inerte col JWT~~ → chiuso dal T-0 del
    brief sicurezza (`apps/core/api/cancello_obblighi.py`, chiamato da
    `JwtAuditAuthentication`; `af9c6f659`, 2026-10-01);
  - ~~i minuti del freno non arrivano al messaggio~~ e ~~il testo «Account …
    bloccato»~~ → R-8 (`20260925-52`, `48291b801`) e B-8/F-1 (2026-09-27): il
    `message` di `E_UTENTE_BLOCCATO` porta i minuti, il login lo mostra;
  - ~~oracolo sull'esistenza dello username~~ → R-7 (`20260925-55…-62`,
    `7f3208a58`) e B-9…B-12 (`e7dbbad73`, 2026-09-25): check e registrazione
    sempre, col digest del nome tentato (`apps/core/services/nome_tentato.py`,
    `AuthRepository.check_blocco_login` / `registra_tentativo_login`);
  - ~~il login riuscito del test sul DB vero usa un superuser esistente~~ →
    costruito in L-3 (`CicloOperatoreDbTests`, §4.1-bis);
  - ~~il P-2 è su dbdev ma non nel repo~~ → in git (`acc6385d5`, `64a1ad2f4`),
    `crea_operatore` allineato in L-3.

### 3.2 L-1 — Frontend

✅ Fatto (2026-09-25), `core/views/LoginView.vue` `resolveLoginError`:

- `E_CREDENZIALE_BLOCCATA` → chiave i18n («Accesso bloccato
  dall'amministratore: contattalo»);
- `E_LOGIN_ATTESA` → `message` del DB, che porta i secondi (chiave di ripiego);
- ~~`E_UTENTE_BLOCCATO` → chiave i18n: è una frase chiusa~~ → superato da F-1
  (2026-09-27): dal `20260925-52` il `message` porta i minuti, e il login lo
  mostra come `E_LOGIN_ATTESA` (chiave di ripiego);
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

> ⏳ **Stato 2026-10-02: da fare.** A DB i verbi ci sono
> (`script.fn_blocca_credenziale`, `fn_sblocca_credenziale`, anti-lockout nel
> trigger `trgfn_credenziali_guard_ultimo_super_admin`); manca la lettura dello
> stato (**R-6**, secondo brief DB non scritto), e nel BE/FE non c'è niente
> (nessun endpoint `blocca-credenziale`). Senza R-6 si potrebbero fare i due
> verbi, ma il drawer non saprebbe dire se la credenziale è bloccata.

**Backend** — `amm_software` (`AdminAPIView`, SUPER_ADMIN: la stessa regola
del verbo, D-B1):

- `POST /amm-software/operatori/<id>/blocca-credenziale/` `{motivo}` →
  `fn_blocca_credenziale`, poi **blacklist di tutte le sessioni** della
  credenziale; `Idempotency-Key` obbligatoria;
- `POST …/sblocca-credenziale/` → `fn_sblocca_credenziale`;
- il dettaglio operatore espone lo stato del blocco (`bloccata_at`,
  `bloccata_da`, `motivo_blocco`) — lettura attraverso una funzione del DB
  (le tabelle sono chiuse all'app, brief §2.2) → §5 R-6;
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

> ✅ **Fatto** (2026-09-25 → 09-27, resoconto in §4.1-bis). ~~Lo stato del
> 2026-09-25, «l'ingresso di un operatore nuovo è rotto in tre punti»~~
> (creazione, invito, attivazione) è superato: i tre punti sono usciti insieme
> in L-3. La tabella sotto è il disegno, eseguito.

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

### 4.1-bis ✅ L-3 fatto (2026-09-25; consenso al riuso 2026-09-27)

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

✅ **Il consenso al riuso (A-9), fatto il 2026-09-27.** ~~«Quando la -51 è in
git…»~~: la `-51` è in git (`64a1ad2f4`); `riusa_auth_user_id` va da view a
madre, e il dialog legge i dati da `script.fn_get_credenziale_per_email`
(`AmmSoftwareRepository.get_credenziale_per_email`), la stessa funzione del
rifiuto — B-20 e F-4 del
[brief credenziale per email](../work-done/brief-db-credenziale-per-email.md)
(`e7be8858b`). `test_login_credenziale_db` prova i due tempi sul DB vero (non più
sospeso). Collaudo a video
[eseguito](../work-done/collaudo-in-app-consenso-riuso-credenziale.md) il
2026-10-02, compreso il caso «email di chi è già operatore»
(`E_CREDENZIALE_GIA_OPERATORE`, il rimedio è il reinvito).

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

✅ **Richieste nate dal lotto** → §5 R-3 (esteso), R-9: consegnate e allineate
(B-13…B-16, F-2; poi i motivi come codici, brief DB §16, B-17…B-19, F-3).

### 4.2 L-4 — Chiave d'ingresso per porta (D-9)

> 🟡 **Stato 2026-10-02.** ✅ Nome utente nell'invito operatore (R-3 a DB,
> B-15: `InvitoOperatoreService` passa `username`; template `_CROSS` per il
> flusso con un clic, `PortaInvito.template_cross`). ⏳ Il resto è da fare e
> non aspetta nessuno: `PortaleTokenSerializer` / `ShopTokenSerializer`
> ereditano ancora lo `username` di SimpleJWT, `AuthLoginView._find_user`
> cerca per `username`, il reset (`password_reset_views.py`) per `username`.

- **Backend**: i serializer di `portale/token/` e `shop/token/` accettano
  l'**email** (confronto senza maiuscole, sull'indice unico del brief §5.1);
  `admin/token/` resta sul nome utente. Il reset password accetta l'email per
  le credenziali che hanno una veste portale/shop.
- ~~**Nome utente nell'invito operatore**: variabile nel template email
  `INVITO_OPERATORE`, che sta a DB → §5 R-3.~~ ✅ Fatto (2026-09-25).
- **Frontend**: oggi l'unica pagina di login è quella operatore
  (`LoginView`, canale ADMIN forzato); portale e shop **non hanno ancora una
  pagina di login**. ⇒ La parte FE di D-9 nasce con quelle pagine; qui si
  aggiornano la pagina di attivazione conclusa (portale/shop: «entra con la tua
  email») e il reset password (campo «nome utente o email»).
- ~~Prima che il DB applichi l'indice unico: il controllo a mano delle coppie
  di email~~ → superato: l'indice è in vigore col P-2
  (`django.ix_auth_user_email_lower_unique`, `lower(email)` dove non vuota).
- ⚠️ Il nome tentato del freno (R-7) si normalizza **con la stessa regola del
  lookup** (`nome_tentato.py`): passando all'email, lookup e impronta cambiano
  insieme (commento in `auth_views.py`, «Con l'email (L-4) si cambia il campo»).

### 4.3 L-5 — Disattivazione per veste, revoca, sessioni (M-5, M-6, D-3, D-4, D-5)

> 🟡 **Stato 2026-10-02.** ✅ **Fatto oggi**:
> `_VESTE_OPERATORE` in `amm_software/db/amm_software_repository.py` —
> aggiornare (`_set_identita_state`, cioè l'interruttore), disabilitare,
> riattivare e il binding SUPER_ADMIN toccano la **sola veste operatore**
> della credenziale (prima tutte). Prova sul DB vero, caso costruito:
> `apps/amm_software/tests/db/test_operatore_altre_vesti_db.py` (salvare,
> disabilitare e riattivare non toccano una veste shop; il SUPER_ADMIN si lega
> alla sola veste operatore). ⏳ **Il resto aspetta R-4 e R-5**, cioè il
> secondo brief DB, non ancora scritto: va scritto **prima** di riprendere il
> lotto.

| Pezzo | Cosa cambia |
| --- | --- |
| `disabilita_operatore` **e** `update_operatore` con `attivo=False` | ✅ tocca **solo la veste OPERATORE** (2026-10-02). ⏳ `ruolo_applicativo` **invariato** (§6 Q-2): oggi tutte e due le strade scrivono ancora `DISABILITATO` → aspetta R-5 |
| `riattiva_operatore`, endpoint `…/riattiva/` **e** `update_operatore` con `attivo=True` | ⏳ **ritirati** (D-3): si riattiva col reinvio. Catena ancora in piedi: service `riattiva_operatore`, `OperatoriRiattivaView`, rotta `operatori/<id>/riattiva/`, FE `riattivaOperatore` e azione store `riattiva`. ~~FE: il pulsante «Riattiva» diventa «Reinvia invito»~~ → superato: nessun `.vue` ha più un pulsante «Riattiva»; la strada viva è l'**interruttore** «attivo» di `OperatoreDrawer.vue` (PATCH), ed è quello che va riportato al reinvio |
| Revoca (D-4) | disattivare **dall'admin** marca la veste come revocata → §5 R-4; `ProfileActivateShopView` rifiuta una veste revocata; FE `AttivaAccessoShopButton` spento col motivo, `PortaleAccessoPanel` mostra «revocato» |
| Sessioni (D-5) | un BB unico «chiudi le sessioni di una veste»: blacklist degli `OutstandingToken` della credenziale il cui claim `identita_id` è quello della veste. Usato da operatore, portale e shop. ⭐ Il BB della revoca esiste dal 2026-09-26 (`apps/core/services/revoca_token.blocca_token_sessioni`, filtro per `sid`): si estende con il filtro per veste, non se ne scrive un secondo. ⚠️ oggi `disabilita_operatore` chiude **tutte** le sessioni della credenziale (anche quelle di una veste shop che ora resta accesa), `update_operatore` con `attivo=False` **nessuna**, portale/shop **nessuna** |
| Stessi effetti per tutte le vesti (A-5) | invalidazione dei token d'invito pendenti **e** della cache permessi anche su portale/shop (oggi solo operatore la seconda, solo portale/shop la prima) |
| Test | ⭐ M-6 **costruito**: credenziale con veste operatore + cliente portale → disattiva operatore → il portale resta attivo, il cliente entra; reinvio → attivazione → operatore di nuovo attivo, cliente intatto. Sul DB provvisto. 🟡 Metà fatta (2026-10-02): `test_operatore_altre_vesti_db` prova disattiva/riattiva con una veste shop; mancano il login del cliente dopo la disattivazione e il giro col reinvio, che nasce con D-3 |

### 4.4 L-6 — Validità della veste al login e a ogni richiesta (A-7)

> ⏳ **Stato 2026-10-02: da fare**, nessuna dipendenza.

- La **finestra** `valido_dal`/`valido_al` della veste (oggi solo `attivo`):
  una veste scaduta non entra, anche se la credenziale ha un'altra veste
  valida. ⚠️ Dal secondo fattore le sedi Python-SQL sono **quattro**, non due
  (verifica 2026-10-02): `AuthRepository.find_identita_attiva_for_ruoli`
  (login), la CTE di `set_jwt_gucs` (ogni richiesta), il secondo passo
  (`secondo_fattore_token_views.py`, `get_identita_dettaglio` + `attivo`) e il
  cambio password (`change_password_view.py`, idem). Si estrae un frammento
  comune, non si riscrive quattro volte.
- ⭐ Fatto trovato nella verifica: a DB la finestra c'è già in una sede,
  `script.fn_get_user_profile` (`E_UTENTE_NON_ATTIVO` / `E_UTENTE_SCADUTO`), ma
  solo per la veste OPERATORE e solo per `/me/` e l'assistente AI. Il lotto
  decide se la regola comune è quella, prima di scriverne un'altra.
- ~~`PasswordChangeRequiredMiddleware` è inerte col JWT … il controllo si
  sposta dopo l'autenticazione DRF~~ → ✅ fatto come **T-0** del brief
  sicurezza §3.4-bis (`apps/core/api/cancello_obblighi.py`, chiamato da
  `JwtAuditAuthentication`; middleware ritirato; `af9c6f659`, 2026-10-01).
  Obblighi in vigore: cambio password e secondo fattore.

---

## 5. Richieste al team DB **non** ancora nel brief

**Stato 2026-10-02.** ✅ R-1, R-2 (P-2), R-3, R-7, R-8, R-9 consegnate nel
[brief DB](../work-done/brief-db-blocco-login-per-credenziale.md) (§12–§15,
chiuso il 2026-09-27) e allineate dal BE/FE. ⏳ **R-4, R-5, R-6 restano**: vanno
nel **secondo brief DB**, che **non esiste ancora** (né in `work-in-progress/`
né in `work-done/`). Si scrive prima di riprendere L-5 (R-4, R-5) e L-2 (R-6).

| # | Richiesta | Per |
| --- | --- | --- |
| R-1 | `script.fn_check_operatore_invitabile`: via la condizione `last_login IS NULL` e «veste OPERATORE già attiva» come rifiuto; ⚠️ oggi pretende l'identità **attiva** per invitare — con la veste che nasce spenta va rovesciata. ✅ **Consegnata nel P-2** (`20260925-43`, brief §12) | L-3, D-8 ✅ |
| R-2 | La madre `fn_crea_operatore_v2` crea la veste OPERATORE **non attiva** anche per una credenziale **nuova** (il brief §5.2 lo chiede solo per quella riusata). ✅ **Consegnata nel P-2** (`20260925-42`, brief §12) | L-3 ✅ |
| R-3 | Template `INVITO_OPERATORE` con la variabile del nome utente. ⚠️ **Esteso** (L-3, 2026-09-25): i template `INVITO_OPERATORE` e `INVITO_PORTALE` dicono sempre «imposta la password», anche nel flusso con un clic; il backend passa `is_cross` a tutti e tre (`INVITO_SHOP` lo dichiara già fra le variabili, ma il testo non lo usa). Serve il ramo «attiva l'accesso con le credenziali che hai già». ✅ **Consegnata** (brief §15, `7f3208a58`): `username` in `INVITO_OPERATORE`, tre template `_CROSS`; BE B-15, B-16 | L-4, D-9, L-3 ✅ |
| R-4 | La veste ricorda di essere stata **revocata** dall'admin (chi, quando), e la riattivazione self-service la rifiuta (sede della regola: DB). ⏳ Secondo brief DB | L-5, D-4 |
| R-5 | `DISABILITATO` **si ritira** come valore di `ruolo_applicativo` (§6 Q-2, deciso): la sua sorte nel tipo `config.ruolo_applicativo` e nei lettori (`fn_is_super_admin`, catena permessi, `trgfn_identita_digitali_guard_coerenza` che oggi lo esenta); le righe che oggi lo portano tornano al ruolo che avevano (dati di sviluppo, a mano). ⏳ Secondo brief DB. ⚠️ Lettore in più, trovato il 2026-10-02: `script.fn_get_user_profile` (guard `ruolo_applicativo = 'DISABILITATO'`) | L-5 |
| R-6 | Una funzione di lettura dello stato di blocco dell'admin (`bloccata_at`, `bloccata_da`, `motivo_blocco`) per il dettaglio operatore: le tabelle sono chiuse all'app. ⏳ Secondo brief DB | L-2 |
| R-7 | **La risposta del login non dipende dall'esistenza dello username** (✅ Tid, 2026-09-25). Oggi il freno e l'attesa hanno per chiave la **credenziale**: un nome inesistente non conta nulla e resta 401 per sempre, uno esistente dopo la soglia risponde 403 `E_UTENTE_BLOCCATO` (e oltre il tetto `E_LOGIN_ATTESA`) ⇒ chi prova sei password sa se l'utente esiste. La regola, sul modello: **il freno e l'attesa valgono per il NOME TENTATO**, esista o no. Per un nome inesistente, stessa soglia, stesso tetto, stessi codici, stesse due chiamate (check prima, registrazione dopo), così nemmeno il numero di chiamate al DB distingue i due casi. Vincoli: ⛔ il nome **non** si salva in chiaro (nel campo username finiscono anche delle password digitate lì per sbaglio): un hash del nome **normalizzato con la stessa regola del lookup** (oggi uguaglianza esatta sullo username; con L-4 email senza maiuscole, e la normalizzazione deve seguirla); righe con `cleanup_at` come `credenziali_provenienze`; nessuna riga in `config.credenziali` per un nome che non è una credenziale. La forma (tabella a parte o parametro nuovo delle stesse funzioni) la sceglie il DB. ⚠️ Due punti da decidere col brief: (a) hash semplice o HMAC con una chiave del backend: l'hash semplice di una password finita nel campo username si può attaccare offline; (b) `E_CREDENZIALE_BLOCCATA` continua a rivelare che il nome esiste, ma solo per una credenziale bloccata dall'admin, e al titolare quella frase serve per sapere a chi rivolgersi: proposta, **accettarlo e dichiararlo**. ✅ **Consegnata** (brief §13, `20260925-55…-62`, `7f3208a58`); BE B-9…B-12 (`e7dbbad73`) | L-1 ✅ |
| R-8 | Testo di `E_UTENTE_BLOCCATO` in `messaggi_errore.csv` (✅ Tid, 2026-09-25): oggi dice «Account temporaneamente bloccato per troppi tentativi.», ma il freno riguarda la sola **coppia credenziale + provenienza**, e da un'altra postazione si entra. Proposta: «Troppi tentativi non riusciti da questa postazione: accesso sospeso per qualche minuto.» (lo stesso testo della chiave i18n del login, §3.2). Il BE poi riallinea il ripiego in `error_messages_fallback.py`, **dopo** il changeSet: mai prima, o il ripiego sarebbe avanti rispetto al catalogo. ✅ **Consegnata** (`20260925-52`, `48291b801`); BE/FE B-8, F-1 (2026-09-27) | L-1 ✅ |
| R-9 | `script.fn_get_operatore_detail` porti lo stato della **veste** OPERATORE (es. `veste_attiva`): oggi `attivo` è quello della risorsa umana e `is_active` quello della credenziale (derivato da **tutte** le vesti), e il FE non ha come distinguere «veste già attiva» dagli altri motivi del non invitabile se non leggendo il testo. ⚠️ La join sulla veste OPERATORE è senza filtro: con più vesti OPERATORE spente (il modello le ammette) il dettaglio restituisce più righe. ✅ **Consegnata** (brief §14, `20260925-53`, `-54`); BE/FE B-13, B-14, F-2 | L-3 ✅ |

---

## 6. Domande a Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| Q-1 | **Quanti proxy stanno davanti al backend** in produzione? Serve a sapere di quale hop di `X-Forwarded-For` fidarsi (L-0) | ✅ **Tid, 2026-09-24**: niente produzione; si prevede **Nginx come nell'ambiente di sviluppo**, quindi **1**. ⭐ Nginx (playbook) *aggiunge* l'IP vero in coda (`$proxy_add_x_forwarded_for`): il valore fidato è l'N-esimo **da destra**. ⛔ Il numero sbagliato è un difetto **muto** nei due versi: troppo basso ⇒ tutti gli utenti hanno l'IP di Nginx, e 5 errori di chiunque frenano **tutti**; troppo alto ⇒ si torna a fidarsi di un valore del client. ⇒ Setting **obbligatorio** in `env.sh` (nessun default: senza, il backend non parte), `1` nell'ambiente di sviluppo, e una riga nel playbook: *se cambia la catena davanti al backend (un secondo proxy, un bilanciatore), si aggiorna questo numero* |
| Q-2 | Con la disattivazione per veste, `ruolo_applicativo = 'DISABILITATO'` non serve più (la veste spenta è `attivo = false`, e il ruolo resta quello che era). Lo si ritira? | ✅ **Tid, 2026-09-24: sì, si ritira** — oggi la stessa informazione vive in due campi (`attivo` e il ruolo), ed è così che la riattivazione ha perso il ruolo originale (M-6). Sorte del valore nel tipo e nei lettori: §5 R-5 |
| Q-3 | La parte FE di D-9 (login per email) aspetta le pagine di login di portale e shop, che non esistono ancora? | ✅ **Tid, 2026-09-24: sì** — qui solo attivazione conclusa e reset |

---

## 7. Ordine proposto

Riscritto il 2026-10-02 sul lavoro che resta (L-0, L-1, L-3 sono fatti):

1. **L-6** (A-7) e **L-4** (login e reset per email): nessuna dipendenza.
2. Il **secondo brief DB** con R-4, R-5, R-6.
3. **L-2** con R-6; **L-5** (il resto) con R-4, R-5.

Ogni lotto chiude le sue righe nell'analisi e i «⚠️ Difetto noto» nelle doc
`manual/` che rimandano a M-4, M-5, M-6.

---
{% include-markdown "signature-core.md" %}

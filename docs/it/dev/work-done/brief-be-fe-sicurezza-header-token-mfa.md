# Brief BE/FE — Sicurezza: header HTTPS, token fuori da `localStorage`, secondo fattore, ruff `B`

> **Destinatari:** team backend e frontend (`dev/backend-tid`); chi gestisce nginx per §1;
> team DB (`dev/db-tid`) per la sola §3.3.
>
> **Tipo:** quattro lavori indipendenti, raccolti qui perché nascono dalla stessa revisione
> di sicurezza del 2026-09-26. Si possono fare in qualunque ordine; l'ordine consigliato è in §5.
>
> **Stato:** ✅ **CHIUSO il 2026-10-02 e archiviato.** Le quattro parti sono fatte:
> §1 header HTTPS (HSTS, redirect, CSP applicata in Nginx, 28-09); §2 token fuori da
> `localStorage` (refresh nel cookie `HttpOnly`, collaudo a video il 29-09); §3 secondo
> fattore, DB il 29-09 ([brief-db-secondo-fattore-totp.md](brief-db-secondo-fattore-totp.md),
> archiviato con questo) e BE/FE coi lotti T-0 → T-5 di §3.4-bis (30-09 → 02-10, collaudo di
> Tid il 02-10); §3.5 chiave di cifratura separata e §4 ruff `B` (28-09). Decisioni 1 → 10 di §6
> tutte prese. **Commit:** §3.5 e §4 in `077ade022`; §1-§2 in `2356ed65c`; T-0 → T-2 in
> `af9c6f659`; T-1 (rotazione), T-3, T-4, T-5 e il BB degli smoke da committare
> (`dev/backend-tid`).
>
> **Residui, con la loro sede** (nessuno resta solo qui):
> 1. ✅ **la scheda rimasta col frontend di una versione precedente** (§2.5): non si ripara da
>    sola, esce a ogni scadenza finché non la si ricarica. **Decisione di Tid (2026-10-02): non
>    serve un avviso** — non c'è produzione, e in sviluppo dopo un rilascio si ricarica;
> 2. ✅ **i due collaudi a video, superati il 2026-10-02** (Tid, con l'operatore `pochi`): il segno
>    «richiede il secondo fattore» sul reparto marketing ha portato `pochi` alla configurazione
>    (obbligo motivo PROFILO, device ATTIVO), e la disattivazione da amministratore col motivo ha
>    lasciato `TOTP_DISABILITATO` con `motivo` e `chi_agisce`. Emersi e corretti strada facendo: la
>    sezione del drawer non compariva mai (`OperatoreSecondoFattore` leggeva `res.data.data` da
>    `execute`, che restituisce gia' il contenuto — ora con la sua spec), e il salvataggio di un
>    operatore che e' anche cliente dello shop toccava TUTTE le vesti della credenziale
>    (`_VESTE_OPERATORE` in `amm_software_repository`, test sul DB vero);
> 3. ✅ [brief-db-totp-ricifra-segreto.md](brief-db-totp-ricifra-segreto.md): DB consegnato e
>    BE fatto (T-1); archiviato il 2026-10-02, quando la versione del team DB (`26749ed5b`) è
>    arrivata in `dev/backend-tid` col merge di `Tito-dev`.
>
> **Contesto:** [Sicurezza e qualità statica](../sicurezza-e-qualita-statica.md), sezione
> «Aperto». Registro del debito: [migliorie generali](migliorie-generali-BE-FE-da-test-valutazione.md),
> voce D3-c per §1.

---

## 1. Header HTTPS: HSTS, redirect, Content-Security-Policy

### 1.1 Cosa manca

| Header / impostazione | Oggi | Cosa protegge |
| --- | --- | --- |
| `Strict-Transport-Security` (HSTS) | assente | il browser non prova più l'HTTP in chiaro dopo la prima visita: chiude la finestra del primo `http://` intercettabile |
| `SECURE_SSL_REDIRECT` | assente in Django; nginx fa già `308` da 80 a 443 | il redirect non dipende da un solo strato |
| `Content-Security-Policy` | assente, né in nginx né in `index.html` | limita da dove la pagina può caricare script, stili, frame e connessioni: uno script iniettato non parte, o non riesce a spedire fuori ciò che legge |

`check --deploy` in CI accetta oggi `security.W004` (HSTS) e `security.W008` (redirect) nel suo
elenco a cricchetto (`ci-validate.yaml`, passo «Django check --deploy (sicurezza)»). **Chiusa §1, le
due voci si tolgono da quell'elenco.**

⭐ La CSP è l'argomento più pesante: i token JWT stanno in `localStorage` (§2), quindi leggibili da
qualunque script giri nella pagina. Oggi la postura regge perché la superficie è a zero
(`v-html` assente e presidiato da eslint, un solo client HTTP), ma nessun header limita il danno
se la superficie si aprisse.

### 1.2 Dove si mettono

* **HSTS e redirect → in Django** (`settings.py`, ramo non-DEBUG), guidati da variabili
  d'ambiente. Sono versionati, li verifica `check --deploy`, e valgono qualunque proxy ci sia
  davanti. nginx può ripeterli, ma la sede è una.
* **CSP → in nginx.** La CSP serve sulla pagina HTML, e la pagina HTML non la serve Django (in
  sviluppo la serve Vite, in produzione la build statica): Django serve solo JSON. La
  configurazione di nginx va quindi **documentata** in
  [configurazione-django.md](../backend/configurazione-django.md) (vhost), che è la sua sede.

### 1.3 HSTS — attenzione prima di accenderlo

⛔ HSTS dice al browser di **rifiutare** il sito se il certificato non è valido, senza più il
pulsante «procedi comunque». La macchina di sviluppo usa oggi un certificato **auto-firmato**
(vhost in `configurazione-django.md`): con HSTS acceso, il sito diventa irraggiungibile da ogni
browser che l'ha visitato, fino alla scadenza di `max-age`.

Proposta:

* `SECURE_HSTS_SECONDS` da env (`DJANGO_SECURE_HSTS_SECONDS`), **obbligatoria quando
  `DEBUG=0`**, senza default: chi mette in piedi una macchina deve scegliere. In CI si imposta al
  valore di produzione, così `check --deploy` la vede.
* Si parte con un valore **breve** (`300` secondi), si verifica, poi si sale (un anno).
* `SECURE_HSTS_INCLUDE_SUBDOMAINS` e `SECURE_HSTS_PRELOAD` **spenti**: il preload è di fatto
  irreversibile e riguarda il dominio intero, non ZeroErp.
* ✅ **Decisione di Tid (2026-09-28):** la macchina di sviluppo resta con il certificato
  auto-firmato e `DJANGO_SECURE_HSTS_SECONDS=0` **dichiarato** nel suo ambiente. In CI il
  valore di produzione, per `check --deploy`. Un certificato valido (`tailscale cert`) resta
  possibile più avanti, senza toccare il codice.
* Nota: secondo la RFC 6797 §8.1 il browser **ignora** l'header HSTS ricevuto su una
  connessione con errori di certificato; il rischio descritto sopra vale quando l'auto-firmato è
  stato reso fidato nel sistema operativo. Con `0` dichiarato non si pone.

### 1.4 Redirect HTTPS — il caso `/health`

`SECURE_SSL_REDIRECT = True` dietro nginx funziona grazie a `SECURE_PROXY_SSL_HEADER`, già
impostato. Ma una chiamata **diretta** a Gunicorn in HTTP (un controllo locale su
`http://127.0.0.1:8000/health`, un worker, uno script) riceverebbe un `301` invece della risposta.

* `SECURE_REDIRECT_EXEMPT = [r"^health$"]`, e si cercano gli altri chiamanti locali prima di
  accendere (`grep` su `backend/bin/`, `scripts/`, unit systemd, `ci.yaml` smoke test).
* Da env come HSTS (`DJANGO_SECURE_SSL_REDIRECT`), default acceso con `DEBUG=0`.

### 1.5 CSP — la politica di partenza

Ricavata da ciò che il frontend usa oggi (verificato sul codice il 2026-09-26):

* **`blob:` nei frame** — l'anteprima PDF (`DocumentoEmissioneDialog.vue`) carica un
  `URL.createObjectURL` in un `<iframe>`;
* **`srcdoc` con `sandbox=""`** — l'anteprima email (`EmailTemplateDrawer.vue`): è già isolata,
  la CSP non la tocca;
* **stili inline** — PrimeVue inietta elementi `<style>` a runtime: serve `'unsafe-inline'` in
  `style-src` (o un nonce, che PrimeVue supporta ma chiede lavoro sul render dell'HTML);
* nessun `eval`, nessun `new Function`, nessuna risorsa esterna in `index.html`.

```nginx
# Produzione (build statica). Prima come Report-Only, poi applicata.
add_header Content-Security-Policy-Report-Only "
  default-src 'self';
  script-src 'self';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: blob:;
  font-src 'self' data:;
  connect-src 'self';
  frame-src 'self' blob:;
  object-src 'none';
  base-uri 'self';
  form-action 'self';
  frame-ancestors 'none'
" always;
add_header Referrer-Policy "same-origin" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
```

* **Sviluppo (Vite)**: l'HMR apre un websocket sulla stessa porta della pagina e inietta script
  e stili: `connect-src 'self' wss:` e `script-src 'self' 'unsafe-inline'` sul solo blocco di
  sviluppo. ⚠️ Due politiche vuol dire due posti da tenere allineati: vanno scritte una accanto
  all'altra nel vhost documentato, con la differenza commentata.
* **Passi**: `Report-Only` per un giro di collaudo a video su tutte le aree (le violazioni
  compaiono nella console del browser), poi `Content-Security-Policy`.
* `frame-ancestors 'none'` sostituisce l'`X-Frame-Options: DENY` che Django già manda sulle
  risposte API.

### 1.6 Verifica

* `check --deploy --tag security` verde **senza** W004/W008 nell'elenco accettati;
* test Django: con `DEBUG=0` le risposte portano `Strict-Transport-Security`; `/health` in HTTP
  diretto non viene rediretto;
* a mano: `curl -kI https://<host>/` mostra la CSP; collaudo a video senza violazioni in console.

✅ **HSTS e redirect fatti il 2026-09-28** (BE, `dev/backend-tid`):

* `settings.py`: `SECURE_HSTS_SECONDS` da `DJANGO_SECURE_HSTS_SECONDS` (`parse_hsts_seconds`:
  obbligatoria con `DEBUG=0`, senza default, intero ≥ 0); sottodomini e preload spenti;
  `SECURE_SSL_REDIRECT` da `DJANGO_SECURE_SSL_REDIRECT`, default acceso con `DEBUG=0`;
  `SECURE_REDIRECT_EXEMPT = [r"^health$"]`;
* **chiamanti diretti di Gunicorn** (§1.4), cercati: `/health` (smoke del container in
  `ci.yaml`) è esente; i **35 smoke bash** si dichiarano HTTPS come Nginx con il BB
  `backend/scripts/tests/_smoke_https.sh` (scelta di Tid, 2026-09-28: header, non redirect spento
  su `backend-dev`); i test Django lo trovano spento dal runner (`test_runner.py`). Gli smoke
  Python girano in-process e non passano da HTTP; i timer usano comandi di gestione;
* test: `apps/core/tests/api/test_https_header.py` (10: redirect, `/health`, richiesta da Nginx,
  header HSTS, variabile d'ambiente, ogni smoke bash include il BB);
* CI: `check --deploy` gira coi valori di produzione (un anno, redirect acceso) e **W004/W008
  sono tolti** dall'elenco accettato; al loro posto `W005`/`W021`, sottodomini e preload spenti
  per scelta (§1.3), che non sono debito. Nel job e nello smoke del container
  `DJANGO_SECURE_HSTS_SECONDS=0`;
* `backend-dev`: `DJANGO_SECURE_HSTS_SECONDS=0` dichiarato in `env.sh` e `.env.systemd`
  (decisione §1.3). ⚠️ Va riavviato con `sudo systemctl restart zeroerp-gunicorn`: un `HUP` non
  rilegge `.env.systemd` e i worker non partirebbero;
* doc: `.env.example`, `configurazione-django.md` (settings, vhost, test di validazione),
  `sicurezza-e-qualita-statica.md` § «HSTS e redirect HTTPS», api.md (smoke bash), catalogo BB.
* Emerso nel giro, fuori perimetro: `smoke-test-pratiche.sh` aveva un errore di sintassi (una
  virgoletta non chiusa nel riepilogo finale), quindi non partiva: corretto.

✅ **CSP applicata il 2026-09-28** su `backend-dev`, con `Referrer-Policy` e `Permissions-Policy`
(la politica di sviluppo, con le due eccezioni di Vite; quella di produzione è accanto nel vhost
documentato). Passi: script con backup e `nginx -t`, prima `Content-Security-Policy-Report-Only`;
collaudo a video di Tid (anteprime PDF ed email, gestione documenti con upload e download, websocket
di Vite): console senza violazioni. Prova che la console le mostri: un `fetch` verso un sito esterno,
segnalato in `Report-Only` («bloccherebbero … connect-src») e poi, applicata, bloccato. Il vhost
documentato in `configurazione-django.md` è allineato. **§1 è chiusa**; D3-c chiusa nel registro.

---

## 2. Token JWT fuori da `localStorage`

### 2.1 Il problema

`frontend/src/core/storage.js` tiene **access e refresh token in `localStorage`**. Qualunque script
che giri nella pagina li legge e li può spedire altrove; il refresh vale un giorno
(`REFRESH_TOKEN_LIFETIME`) e con la rotazione si rinnova. È la ragione per cui §1 pesa.

### 2.2 La forma proposta

| Token | Oggi | Proposta |
| --- | --- | --- |
| **refresh** | `localStorage` | cookie `HttpOnly; Secure; SameSite=Strict`, con `Path` ristretto all'endpoint di refresh **del proprio canale** (`/api/v1/admin/token/refresh/`, `…/portale/…`, `…/shop/…`). Lo script della pagina non lo vede mai |
| **access** | `localStorage` | **solo in memoria** (variabile del modulo di `core/api.js`). Al ricaricamento della pagina si ottiene con un refresh silenzioso |
| durata access | 60 minuti, commentata «Per sviluppo» | 5–15 minuti: col refresh silenzioso non costa niente all'utente |

Il canale di login (`LOGIN_CHANNEL`) resta in `localStorage`: non è un segreto, serve a scegliere
l'endpoint di refresh dopo un ricaricamento.

### 2.3 Backend

* Le view di login e di refresh dei tre canali (`zeroerp_backend/urls.py`) scrivono il refresh
  nel cookie invece che nel corpo della risposta, e la view di refresh lo **legge dal cookie**.
  Il corpo restituisce il solo access token.
* Logout e revoca (`logout_view`, `revoca_token`) mettono in blacklist **e** cancellano il cookie.
* **CSRF**: un endpoint che si autentica con un cookie è esposto al CSRF. `SameSite=Strict` lo
  chiude sui browser attuali; in più il refresh pretende un header custom (per esempio
  `X-Requested-With`), che un form di un altro sito non può mandare.
* I token multi-veste (`api_multi_veste_token`) e il claim `sid` seguono la stessa forma: da
  verificare uno per uno, con i test.

### 2.4 Frontend

* `storage.js`: tolte le chiavi dei due token; `core/api.js` tiene l'access in memoria e fa il
  refresh silenzioso all'avvio e su 401 (la coda esiste già).
* ⚠️ **Più schede aperte.** Oggi le schede condividono i token tramite `localStorage`. Con il
  refresh in cookie e la **rotazione con blacklist** accesa, due schede che rinnovano insieme
  presentano lo stesso refresh: la seconda trova il token già in blacklist e l'utente viene
  buttato fuori. Serve una di queste, da decidere:
  * coordinamento fra schede con `BroadcastChannel` (una sola scheda rinnova, le altre ricevono
    il nuovo access);
  * oppure un breve periodo di tolleranza lato backend sul refresh appena ruotato.
* `guard:pinia` e il reset al logout restano come sono.

### 2.5 Verifica

* test Django: login → nel corpo nessun refresh, cookie con i quattro attributi; refresh senza
  cookie → 401; refresh con header mancante → 403; logout → cookie cancellato e token in blacklist;
* test FE (vitest): nessun token scritto in `localStorage`;
* collaudo a video: ricarica pagina, due schede aperte per più di una durata dell'access, logout
  da una scheda.

✅ **Fatto il 2026-09-28** (BE + FE, `dev/backend-tid`). Decisioni di Tid dello stesso giorno:
più schede con la strada **A** (le schede si coordinano), access a **10 minuti**, cookie su
`Path=/api/v1/` (non il solo endpoint di refresh: lo usano anche logout, cambio emittente e cambio
password, che stanno altrove).

* **BE**: BB `apps/core/api/refresh_cookie.py` — cookie `zeroerp_refresh`, `HttpOnly`,
  `SameSite=Strict`, `Path=/api/v1/`, `Secure` = `REFRESH_COOKIE_SECURE` (segue
  `SESSION_COOKIE_SECURE`), durata del token. Login e refresh dei tre canali, cambio password e
  cambio emittente spostano il refresh dal corpo al cookie; refresh, logout e cambio emittente lo
  leggono dal cookie; il logout lo cancella in ogni risposta. Il refresh pretende
  `X-Requested-With: XMLHttpRequest` (403 `E_PERMISSION_DENIED`), senza cookie è 401. Nessun
  codice d'errore nuovo: bastavano quelli a catalogo. `ACCESS_TOKEN_LIFETIME` = 10 minuti.
* **FE**: BB `core/sessione.js` — access solo in memoria; `rinnovaCoordinato` = una volta per
  scheda (promise condivisa) e una scheda alla volta (`navigator.locks`), con l'access nuovo sul
  `BroadcastChannel` `zeroerp-sessione`. `core/api.js` `rinnovaAccess` è l'unica strada verso il
  refresh (la vecchia coda `pendingRequests` è diventata la promise condivisa). Store `auth`:
  niente token in `localStorage` (quelli rimasti si tolgono all'avvio), `ripristinaSessione()` nel
  guard al posto del «refresh proattivo», eventi fra schede LOGOUT (escono tutte) e
  SESSIONE_NUOVA (login o cambio emittente altrove: questa scheda riparte dal boot).
  L'eccezione `window.location` ha ora una sede sola, l'azione `ripartiDalBoot`.
* ⚠️ **CSRF e `SameSite`**: la protezione è doppia (cookie `Strict` + header custom) perché il
  refresh è l'unica rotta autenticata dal solo cookie. Logout e cambio emittente pretendono il
  Bearer, che un altro sito non ha.
* **Test**: `test_auth_views` (`RefreshCookieTests`, 4 nuovi + i test del refresh riscritti sul
  cookie), `test_sessioni_view` (logout legge e cancella il cookie), `test_emittente_attivo_view`,
  `test_change_password_token_veste`; il presidio F-9 di `test_corpo_oggetto` si è spostato dal
  logout (che il corpo non lo legge più) alla PATCH articolo. FE: `sessione.spec.js` (8).
* **Smoke**: `smoke-test-core`, `-audit-logging`, `-jwt-audit-guc` leggono il refresh dal
  `Set-Cookie` col BB `backend/scripts/tests/_smoke_refresh.sh`. ⚠️ Non ancora eseguiti contro il
  backend vero: va riavviato col codice nuovo.
  ⚠️ **Emerso al primo lancio (2026-09-28):** il login di **ogni** smoke rispondeva 500
  `E_AUTH_CHIAMATA_NON_VALIDA` «provenienza assente». Il freno sulla credenziale (dal 2026-09-25)
  pretende `X-Forwarded-For`, che Nginx aggiunge e lo smoke, diretto su Gunicorn, no. Corretto nel
  BB `_smoke_https.sh`, che ora dichiara anche la provenienza `127.0.0.1`; presidio
  `test_il_bb_dichiara_una_provenienza_che_il_login_accetta` (esegue il BB, rosso senza la
  correzione).
* **Doc**: api.md § «Il refresh token viaggia nel cookie», frontend-standards § Sicurezza, i due
  cataloghi BB, le pagine `backend/core/manual/` dei cinque endpoint, `sicurezza-e-qualita-statica.md`.
* ⏳ **Resta il collaudo a video** (sopra, ultima voce): ricarica, due schede oltre i 10 minuti,
  logout da una scheda, cambio emittente con due schede aperte.
  🟡 **Collaudo del 2026-09-28/29, prima parte — superata.** Due dispositivi (Firefox su PC,
  tablet Android), fermi oltre i 10 minuti: alla prima richiesta l'access scaduto dà 401, il
  frontend rinnova da solo (200) e ripete; nessuna uscita (PC 00:18 e 00:28, tablet 00:31). Anche
  la ricarica della pagina rinnova all'avvio.
  ⚠️ **Emerso nel giro:** il tablet usciva con «sessione scaduta» a ogni scadenza, con il rinnovo
  rifiutato 403. Non era il codice nuovo: la scheda era aperta da prima della modifica e girava il
  frontend **vecchio**, che il refresh lo mandava nel corpo e senza l'header anti-CSRF. Il ritorno
  al login non ricarica il codice (è una schermata della stessa app): è bastata una ricarica
  completa. Per distinguere la prossima volta «client vecchio» da «header riscritto lungo la
  strada», `richiedi_header_anti_csrf` scrive nel log `security.refresh_senza_header_anti_csrf`
  col valore ricevuto (troncato) e lo user agent.
  ❓ **Da decidere:** una scheda con il frontend di una versione precedente non si ripara da sola
  (esce a ogni scadenza finché non la si ricarica). In produzione, a ogni rilascio, serve un
  avviso «versione nuova, ricarica» o una ricarica automatica.
  🟡 **Seconda parte**, con due schede **nello stesso browser** (è lì che lavora il
  coordinamento; due dispositivi sono due sessioni, e il logout dal tablet ha lasciato il PC
  collegato, come deve): ✅ logout da una scheda → esce anche l'altra (2026-09-29). Sull'altra
  compareva «sessione scaduta», frase imprecisa: corretta il 2026-09-29 (revisione, ultima voce).
  ✅ cambio emittente con due schede aperte → l'altra riparte col nuovo emittente (2026-09-29).
  ✅ **Collaudo a video del §2 chiuso.**

✅ **Revisione critica del cantiere** (2026-09-28, nello stesso commit `2356ed65c`):

* **E-8 chiuso** (analisi difetti doc API core, ok Tid): la veste del refresh si legge da claim con
  la **firma verificata**. La funzione del logout è diventata il BB `claims_refresh_firmati` di
  `refresh_cookie.py` (regola del 2), copia ritirata. Refresh illeggibile o firmato da altri → 401;
  refresh nostro di un altro canale → 403 come prima. Audit e GUC del refresh nascono dagli stessi
  claim verificati: prima si rileggeva il token tre volte alla cieca.
* **Regola del 2, ok Tid**: `handle_post_json_con_refresh` (cambio password e cambio emittente
  scrivevano il cookie «solo se 200» con lo stesso schema a mano) e `parse_intero_non_negativo` in
  `settings.py` (`DJANGO_TRUSTED_PROXY_COUNT` e HSTS).
* **Fragile**: un rinnovo che risponde senza access ora è un rinnovo fallito (prima le richieste
  ripartivano con `Bearer undefined`); la conversione dei claim interi è una sola.
* **Valori in tre linguaggi**: nome del cookie e header anti-CSRF stanno in Python, in bash e nel
  frontend; `test_nome_cookie_e_header_uguali_nei_tre_linguaggi` li confronta.
* Test aggiunti: `test_auth_views` fino al n. 30 (GUC dai claim verificati, token veri per E-8, il
  BB del POST con refresh), `test_https_header` n. 11, `sessione.spec.js` n. 9.
* ✅ ~~Lasciato, da decidere: dopo un logout fatto in un'altra scheda questa arriva al login con
  la frase «sessione scaduta».~~ **Fatto il 2026-09-29** (frase scelta da Tid): «Ti sei scollegato
  da un'altra scheda». I motivi di ritorno al login sono diventati `MOTIVO_USCITA` in
  `core/sessione.js`, sede unica per interceptor, store, guard del router e `LoginView`: il guard
  che non rimbalza alla home una sessione dichiarata chiusa riconosce ogni motivo, non la sola
  stringa `session_expired`. Test: `sessione.spec.js` n. 10-11, `stores/auth.spec.js` n. 1 (rosso
  senza la correzione).

---

## 3. Secondo fattore di autenticazione (TOTP)

### 3.1 Cosa esiste già

* **DB**: la tabella `config.auth_totp_device` (1:1 con `auth_user`: secret cifrato, flag
  `abilitato`/`confermato`, hash dei codici di recupero, anti-replay con `ultimo_codice_usato`).
  Doc: `docs/it/dbzero/config/manual/auth_totp_device.md`.
* **Backend**: niente. Nessun servizio, nessuna view, nessun riferimento alla tabella in
  `backend/apps`.
* **La credenziale** (`config.credenziali`, dal 2026-09-25) tiene tentativi, blocco e cambio
  password obbligato. Il vecchio `totp_obbligatorio` è stato tolto da `identita_digitali`
  (changeSet `20260925-25`, decisione D-10) con la nota *«quando il TOTP si farà, l'obbligo sarà
  della credenziale»*.

### 3.2 ⚠️ Documentazione DB da allineare

Il manuale `auth_totp_device.md` descrive un **`TotpService`** che non esiste e un campo
**`totp_obbligatorio` su `risorse_umane_auth_user`** che non esiste più. Anche il manuale di
`credenziali.md` dice che `totp_obbligatorio` «esce da `identita_digitali`» verso la credenziale,
ma la colonna non c'è. Una guida che descrive un disegno mai costruito va riscritta sullo stato
attuale (standard delle guide): chiesto al team DB in §3.3.

### 3.3 Richiesta al team DB

➡️ **Scritta il 2026-09-28:** [brief-db-secondo-fattore-totp.md](brief-db-secondo-fattore-totp.md),
con tre decisioni per Tid (D-T1 → D-T3). I punti sotto restano come origine.

1. **Dove sta l'obbligo del secondo fattore.** Proposta: colonna `totp_obbligatorio` su
   `config.credenziali`, come dice la nota di D-10. ✅ **Decisione di Tid (2026-09-28):
   entrambi.** Il flag sulla credenziale lo accende l'amministratore sul singolo utente; in più
   l'obbligo scatta **da solo** per gli account privilegiati (per esempio il super admin, chi
   gestisce utenti e permessi), e cade quando quei permessi si perdono. Obbligo effettivo = flag
   **oppure** regola. Quali permessi rendono «privilegiato» un account, e dove si calcola la
   regola, si definisce nel brief DB.
2. **Funzioni di scrittura** del device (registra, conferma, disabilita, consuma un codice di
   recupero, anti-replay) sul modello di `config.credenziali`: niente RLS (si legge prima del
   login, quando un perimetro non c'è ancora), **all'app solo `SELECT`**, ogni scrittura da una
   funzione di `script`. Da verificare sulla postura attuale di `auth_totp_device`: che GRANT ha
   `zeroerp_app` su una tabella che oggi nessuno usa.
3. **Allineare i due manuali** di §3.2.

### 3.4 Backend e frontend

* **Flusso di login a due passi**: password corretta e device attivo → risposta
  `two_factor_required` con un token di sfida **breve** (pochi minuti, monouso), non un JWT
  d'accesso; secondo passo con il codice → JWT. Il freno sui tentativi e il throttle valgono
  anche per il codice (6 cifre = un milione di combinazioni: senza freno, si indovinano).
* **Setup**: segreto generato dal backend, mostrato come QR code **una volta**, confermato con il
  primo codice; codici di recupero mostrati una volta.
* **Middleware** che obbliga al setup chi ha l'obbligo e non ha un device attivo, sul modello di
  `PasswordChangeRequiredMiddleware`.
* ✅ **Dipendenze — decisione di Tid (2026-09-28): librerie esistenti.** Quali, fra le
  alternative sotto, si sceglie nel lavoro; ogni libreria nuova si nomina a Tid prima di
  aggiungerla. ✅ **Scelte e approvate da Tid (2026-09-28): `pyotp` per il TOTP, `segno` per il
  QR code, generato nel backend come SVG** (il frontend non aggiunge librerie npm). Si
  aggiungono a `requirements` quando parte il lavoro BE, dopo il DB. Le alternative valutate:
  * TOTP: `pyotp`, oppure RFC 6238 scritta sulla libreria standard (`hmac`, `hashlib`,
    `struct`: una trentina di righe, più i test con i vettori della RFC);
  * QR code: generato nel backend (`qrcode`, SVG) o nel frontend (una libreria npm).

#### 3.4-bis Il piano (2026-09-30, DB consegnato il 2026-09-29)

Il DB del secondo fattore è applicato ([brief-db-secondo-fattore-totp.md](brief-db-secondo-fattore-totp.md),
richieste al BE/FE in §9.5). Decisioni di Tid del 2026-09-30: le decisioni 5 → 8 di §6.

⛔ **Il «middleware sul modello di `PasswordChangeRequiredMiddleware`» non si fa**: quel
middleware è **inerte col JWT** (A-8 del [piano accessi](../work-in-progress/piano-be-fe-accessi-credenziale-e-vesti.md):
a `process_view` l'utente del Bearer è ancora anonimo) e scrive a mano un codice che non è a
catalogo. Copiato, anche l'obbligo del secondo fattore sarebbe fatto rispettare dal solo
frontend. L'analisi [2FA](autenticazione-due-fattori-e-provider.md) A.2.11 lo diceva già: **lo
stesso meccanismo, non un secondo**.

| Lotto | Cosa |
| --- | --- |
| **T-0** | Il **cancello degli obblighi** dopo l'autenticazione DRF (chiude A-8; A-7 resta in L-6): cambio password e configurazione del secondo fattore in **una** sede, ciascuno coi suoi percorsi ammessi. Prima un test che provi che oggi non scatta, poi la correzione. Codici a catalogo: [brief-db-codici-cancello-obblighi-e-sfida-totp.md](brief-db-codici-cancello-obblighi-e-sfida-totp.md). ⚠️ **In vigore solo il cambio password** (`OBBLIGHI_IN_VIGORE`, 2026-09-30): un obbligo si fa rispettare solo quando esiste la strada per soddisfarlo. Acceso insieme a T-0, il secondo fattore murava il `SUPER_ADMIN` (obbligo per PROFILO, device assente): ogni API rispondeva 403 e la UI finiva su «avvio non riuscito» |
| **T-1** | `pyotp` e `segno` in `requirements.in`; `genera_error_policies` per i sei `E_TOTP_*`; `totp_service` (verifica che restituisce il **passo** accettato, periodo in una sede sola; codici di recupero; QR SVG); i verbi DB dietro `AuthRepository`; `auth_totp_device.secret_encrypted` in `CAMPI_CIFRATI`. ✅ **Fatto il 2026-10-01**, tranne l'ultima voce: `pyotp==2.10.0` e `segno==1.6.6` nel lock (nessun altro pacchetto mosso); policy e ripieghi dei sei codici presenti; [totp_service.py](../../../../backend/apps/core/services/totp_service.py) (vettori RFC 6238, provato per mutazione); i verbi dietro un repository suo, [secondo_fattore_repository.py](../../../../backend/apps/core/db/secondo_fattore_repository.py), provato sul DB vero col ciclo di vita intero (anti-replay, codici monouso). 🔴 **`CAMPI_CIFRATI` no, ed è un difetto di modello**: `ricifra_campi_cifrati` legge con `SELECT … FOR UPDATE` e riscrive con un `UPDATE` diretto, ma su `auth_totp_device` l'app ha il solo `SELECT` (`20260929-24`; verificato sul DB vivo il 2026-10-01). Iscritta così, la colonna farebbe fallire la rotazione delle chiavi; non iscritta, i segreti resterebbero sulla chiave vecchia e diventerebbero illeggibili quando la si toglie. Serve un verbo DB per la rotazione: decisione 9 di §6, [brief-db-totp-ricifra-segreto.md](brief-db-totp-ricifra-segreto.md). ✅ **Chiuso il 2026-10-01**: verbo consegnato dal DB (`20261001-35`), `CampoCifrato` impara a scrivere col verbo, il segreto è in `CAMPI_CIFRATI`; `test_ricifra_campi_cifrati_db` con i due casi del device (ruota, cambiato nel frattempo), provati per mutazione. T-3 non aspetta più niente |
| **T-2** | Login a due passi sulle **tre** porte: device `ATTIVO` → niente JWT, `two_factor_required` + sfida firmata di 5 minuti (credenziale, veste, porta, provenienza). `POST /api/v1/{porta}/token/secondo-fattore/` con il codice **o** un codice di recupero: blocco ricontrollato, codice sbagliato = `fn_registra_tentativo_login(successo => false)` (D-T2), il successo si registra **solo** qui ✅ **Fatto il 2026-10-01**: il primo passo nelle tre porte (`porta` sulla view), la sfida in [sfida_secondo_fattore.py](../../../../backend/apps/core/services/sfida_secondo_fattore.py), il secondo passo in [secondo_fattore_token_views.py](../../../../backend/apps/core/api/secondo_fattore_token_views.py), la chiusura dell'accesso estratta in `chiudi_accesso_riuscito` (due chiamanti). Il login intero è provato sul DB vero, e lì è emerso un difetto: il rifiuto del DB su un codice ripresentato interrompeva la transazione e il tentativo fallito non veniva contato. Corretto con un savepoint. ⚠️ Dichiarato: al primo passo SimpleJWT emette comunque access e refresh, che non escono dalla view (una riga in più fra gli `OutstandingToken`, nessun token consegnato) |
| **T-3** | Self-service `/api/v1/auth/secondo-fattore/` (stato, registrazione, conferma, codici di recupero, disattivazione); per il `SUPER_ADMIN` l'obbligo sulla credenziale e la disattivazione del device di un altro con motivo, traccia `TOTP_DISABILITATO` (`via: APP`) in `dbops.sessioni_utente` (D-T3); il segno `richiede_secondo_fattore` nell'editor del profilo di reparto — oggi l'unico profilo con una scrittura. **Nello stesso lotto** `SECONDO_FATTORE` entra in `OBBLIGHI_IN_VIGORE` e gli endpoint self-service lo dichiarano in `obblighi_ammessi` (`test_ogni_obbligo_in_vigore_ha_la_sua_strada` lo verifica sugli URL veri) ✅ **BE fatto il 2026-10-01**: [secondo_fattore_service.py](../../../../backend/apps/core/services/secondo_fattore_service.py) (la verifica della prova ci è stata spostata dal secondo passo: tre chiamanti), le view self-service e del SUPER_ADMIN, il segno nel profilo di reparto (assente nel PUT = invariato), `errore_provenienza_assente` estratto (regola del 2). Provati il servizio sul DB vero (configura, rigenera, disattiva con traccia; obbligo e disattivazione del SUPER_ADMIN, il rifiuto senza motivo) e il segno di reparto. ⚠️ **L'obbligo del secondo fattore resta FUORI dal cancello** (`OBBLIGHI_IN_VIGORE`): entra con T-4, quando c'è la pagina e il guard che ci porta — senza, il SUPER_ADMIN avrebbe 403 ovunque |
| **T-4** | FE: il secondo passo in `LoginView`; la pagina «Sicurezza» (QR, conferma, codici di recupero mostrati una volta) con la voce nel menu utente e il guard dell'obbligo — ⚠️ **prima** del caricamento delle misure di pagina nel `beforeEach`, come `mustChangePassword`: dopo, il 403 dell'obbligo diventa «avvio non riuscito» invece del setup; la sezione nel drawer operatore; il toggle nell'editor del reparto; i18n. **Solo il FE admin**: le pagine di login di portale e shop non esistono (Q-3 del piano accessi) — il BE copre le tre porte ✅ **Fatto il 2026-10-02**. BE: l'obbligo del secondo fattore **in vigore** nel cancello, `obblighi_pendenti` su `/core/me/` (la regola del cancello, non una copia), il QR come data URI (un `<img>`, mai `v-html`). FE: `completaSecondoPasso` nello store e il secondo passo in `LoginView`; `SicurezzaView` (`/sicurezza`, fuori dal layout) col guard dopo quello del cambio password e la voce nel menu utente; `OperatoreSecondoFattore.vue` nella scheda dati del drawer operatore; il segno nell'editor del reparto; i18n it/en. Verdi: backend 5737 + 5999 col DB vero, frontend 532 test, lint, guard, build. ⚠️ **Gli smoke bash** entrano come `SMOKE_USER` (default `tid`, SUPER_ADMIN): col secondo fattore attivo il loro login riceve la sfida — decisione 10 di §6 🟡 **Collaudo del 2026-10-02 (Tid), superato**: configurazione dalla pagina Sicurezza, login col codice, smoke `smoke-test-core` col secondo passo automatico. Corretti strada facendo: la pagina era il cerchio del login e tagliava QR e codici (ora un riquadro ad altezza libera, centrato); il BB degli smoke falliva in silenzio dietro `2>/dev/null` (ora un 401 che dice cosa manca, e riconosce un codice di recupero passato come chiave); il secondo passo condivideva il contatore di frequenza del login (429 al secondo login: ora `SecondoFattoreRateThrottle`, un contatore suo) |
| **T-5** | Test (il login a due passi anche col DB vero), smoke, doc (api.md, manuale del token multi-veste, cataloghi BB, runbook del DBA per lo sblocco dal server, §9.5 punto 7 del brief DB), collaudo ✅ **Fatto il 2026-10-02**: manuale `backend/core/manual/api_secondo_fattore.md` (e il secondo passo in `api_multi_veste_token.md`, il contatore in `api_throttling.md`, `obblighi_pendenti` in `api_user_profile.md`); la guida `risorse-umane-e-accessi.md` («Secondo fattore di autenticazione»); la procedura del DBA nel runbook `dev/infra/comandi-utili-run-book.md` §10; l'analisi 2FA aggiornata (Parte A costruita, domande chiuse); i test sul DB vero e il collaudo (T-4). Brief archiviato |

⚠️ **Dichiarati, non decisi:**

* chi ha l'obbligo e non ha ancora un device entra con la sola password e configura al primo
  accesso: chi conosce solo la password può registrare il **proprio** telefono prima del
  titolare. È il limite noto dell'iscrizione al primo accesso;
* i codici di recupero hanno circa 80 bit casuali e si salvano come SHA-256 semplice, senza una
  chiave del backend: ruotare la `SECRET_KEY` non li invalida, e con quell'entropia una chiave
  non aggiunge difesa.

### 3.5 ⛔ Prerequisito: separare la chiave di cifratura dalla `SECRET_KEY`

Oggi `crypto_service` ricava la chiave Fernet dalla `SECRET_KEY`. Con i segreti TOTP cifrati
così, **ruotare la `SECRET_KEY` spegnerebbe il secondo fattore di tutti gli utenti**, oltre a
rendere illeggibili le password SMTP: la rotazione della chiave di Django diventerebbe
un'operazione che nessuno vuole fare, cioè non si farebbe.

Proposta, **prima** del TOTP:

* chiave dedicata `DJANGO_FIELD_ENCRYPTION_KEYS` (obbligatoria), separata dalla `SECRET_KEY`;
* `MultiFernet` con **più chiavi**: si cifra con la prima, si decifra con tutte. Ruotare vuol dire
  aggiungere una chiave in testa e ri-cifrare con calma, senza rompere niente;
* un comando di gestione per la ri-cifratura, e la migrazione dei dati cifrati di oggi (password
  SMTP) dalla chiave derivata alla chiave nuova.

✅ **Fatto il 2026-09-28** (BE, `dev/backend-tid`):

* `settings.py`: `FIELD_ENCRYPTION_KEYS` da `DJANGO_FIELD_ENCRYPTION_KEYS`, obbligatoria, senza
  ripiego; il backend non parte con una chiave non Fernet o ripetuta
  (`parse_chiavi_cifratura`, il messaggio nomina la posizione, mai la chiave);
* `crypto_service`: `MultiFernet` sulle chiavi, `ricifra`, e `CAMPI_CIFRATI`, l'elenco delle
  colonne cifrate che la rotazione percorre (oggi `config.email_account.smtp_password_encrypted`;
  `auth_totp_device.secret_encrypted` entra col TOTP, insieme al codice che la scrive);
* `manage.py ricifra_campi_cifrati [--dry-run] [--anche-chiave-da-secret-key]`: tutto o niente;
  l'opzione è la migrazione una-tantum dalla chiave derivata. La derivazione vive solo lì;
* test: `test_crypto_service` (14), `test_ricifra_campi_cifrati_db` (4, sul DB vero; 6 dal 2026-10-01, col segreto TOTP);
* CI: chiave segnaposto in `ci-validate.yaml` e nello smoke del container di `ci.yaml`;
* doc: `.env.example`, `configurazione-django.md`, `sicurezza-e-qualita-statica.md`
  § «Le chiavi dei dati cifrati» (la procedura di rotazione), catalogo BB, manuali email.

✅ **Migrazione su `backend-dev` fatta il 2026-09-28**: chiave aggiunta ai due file, una password
SMTP ri-cifrata (verificata con la sola chiave nuova), Gunicorn e timer ripartiti, login
provato; `.env.systemd` portato a `600` (era `644`). Nel farlo il comando è stato lanciato da
`backend/` con il percorso dalla radice («File o directory non esistente»), e il riavvio
successivo ha lasciato il backend fermo per qualche minuto: la doc della procedura ora lo dice.

Per **ogni altra macchina con dati** (nell'ordine; la `SECRET_KEY` NON si cambia prima; comandi
dalla radice del repo):

1. `backend/scripts/chiave-cifratura-aggiungi.sh` (genera la chiave e la scrive in
   `backend/env.sh` e `backend/.env.systemd`);
2. `backend/scripts/chiave-cifratura-ricifra.sh --migrazione` (dry-run, conferma, scrittura);
3. riavviare il servizio (`sudo systemctl restart zeroerp-gunicorn`); i timer rileggono
   `.env.systemd` da soli;
4. solo ora, se si vuole, ruotare la `SECRET_KEY` (voce «Rotazione dei segreti» di
   `sicurezza-e-qualita-statica.md`).

⚠️ Per il team DB (§3.3 punto 3): anche `auth_totp_device.md` dice «chiave derivata da
`Django SECRET_KEY`»; da riscrivere con il resto del manuale. `email_account.md` è già allineato.

---

## 4. ruff `B` (bugbear)

Accenderla, con la disciplina di `ruff.toml`: si sana, poi si accende, e il cancello nasce a zero.

Rilievi al 2026-09-26 (`ruff check --select B --statistics .`), come fatto datato:

| Regola | Rilievi | Cosa chiede |
| --- | --- | --- |
| `B905` | 47 | `zip()` senza `strict=`: tronca **in silenzio** alla lista più corta. Una per una: `strict=True` dove le due liste devono essere lunghe uguali (quasi sempre), `strict=False` scritto dove la troncatura è voluta |
| `B007` | 11 | variabile del ciclo non usata: `_` o un nome che inizia con `_` |
| `B904` | 8 | `raise` dentro un `except` senza `from`. `ruff.toml` le ha già guardate e scartate (sono `raise AssertionError("unreachable")`): si mettono in `ignore` con il motivo, non si toccano |
| `B023` | 6 | una funzione definita nel ciclo che usa la variabile del ciclo: legge il valore **dell'ultimo giro**. Da guardare una per una, possono essere difetti veri |

Da fare nello stesso giro: `select` in `ruff.toml` più la voce di commento con le decisioni, e la
riga della tabella «famiglie accese» nel documento tecnico.

✅ **Fatto il 2026-09-28.** Misurati quel giorno **74** rilievi (50 `B905`, 11 `B007`, 7 `B904`,
6 `B023`), sanati tutti, poi `B` accesa: il cancello nasce a zero. Le decisioni, una per famiglia,
sono nel commento di `ruff.toml`; in breve:

* `B905`: tutti `strict=True`, nessuna troncatura voluta. ⚠️ La correzione automatica di ruff
  mette `strict=False`, che conserva il difetto: non va usata;
* `B023`: nessun difetto (lambda invocate subito), variabili legate come argomenti di default;
* `B007`: rinominate `_x`, più due cose vere — codice morto in `test_ui_action_e_canale_campi`
  (il sorgente «senza docstring» calcolato e mai letto) e `check_i18n_keys.py` che non diceva
  dove sta un'intestazione di colonna senza traduzione;
* `B904`: ⚠️ **diverso da quanto proposto sopra**. Sui 7 rilievi di oggi solo 4 sono
  `AssertionError("unreachable")` (marcati `noqa` sul punto); 3 sono traduzioni d'errore vere
  (`views.py` ×2, `payload_validators.py`), ora `from None`. Quindi la regola **resta accesa**
  invece di finire in `ignore`.

Emerse nel giro, rimandate il 2026-09-28 e ✅ **fatte lo stesso giorno** (richiesta di Tid):

1. ✅ **Regola del 2 su `row_to_dict` / `rows_to_list`** (`core/db/_helpers.py`): ritirate le 32
   conversioni riga→dizionario scritte a mano in 12 file (`amm_software`, `ui_admin`, `auth`,
   `portale`, `session_audit`, `parameter`, `lookup`, `config_crud`, `pratiche`,
   `approvazioni_prezzo`, `send_pending_emails`). Le due forme ricorrenti sono diventate le
   chiamate ai BB; le varianti a mano (conteggio `total_count` da togliere, JSONB normalizzato,
   `require` fra lettura e conversione, guardia su `cursor.description`) conservano il loro
   passo in più. ⚠️ Una sola resta fuori, ed è un'altra operazione: `vendite_repository` (fondi
   da decidere) mappa tuple già estratte da `_query_paged_view`, con `strict=False` dichiarato
   per la colonna in coda. Due test avevano un `description` finto fatto di tuple (senza
   `.name`, che psycopg ha): ora `SimpleNamespace(name=...)`. Provato anche sul DB vero
   (`ZEROERP_TEST_DB_E2E=1`, suite intera).
2. ✅ **`ErrorManager.raise_error` dichiarata `-> NoReturn`**, e con lei
   `listini_service._translate_integrity_error` (chiude con `map_integrity_error`, già
   `NoReturn`). Tolte le **21** righe `raise AssertionError("unreachable"/"irraggiungibile")`
   (le 19 contate più una dentro `ErrorManager` stesso e una in `plafond_fattura_service`). Due
   `ErrorManager.require(False, ...)` — un «solleva sempre» mascherato da controllo — sono ora
   `raise_error`, quello nell'`except` con `cause=exc`. Presidio: `test_error_manager` (ogni
   ramo solleva; `NoReturn` dichiarato sulle tre funzioni).
   Stessa operazione sull'altra forma della riga, il `raise` nudo (`raise  # unreachable, per
   type checker`): 66 nel codice applicativo, classificati per la chiamata che li precede.
   ✅ Tolti i **57** che seguono `ErrorManager.raise_error` (`documenti` 53, `parameter_service`
   2, `amm_software_repository` 1, `pipeline_runner` 1): dipendevano solo da `raise_error`, già
   `NoReturn`. ⚠️ Il primo conteggio li aveva mancati perché cercava solo la forma
   `AssertionError(...)`: una ricerca per **testo** vede una forma, quella per **significato**
   («riga dopo una chiamata che solleva sempre») le vede tutte.
   ✅ **Il giro a sé, fatto il 2026-09-28** (richiesta di Tid):
   * 9 `raise` nudi dopo traduttori d'errore **locali**, tolti dichiarando `NoReturn` il
     traduttore dopo averne verificato che solleva su ogni ramo: `_raise_known_db_error`
     (`pratiche_service` ×6, `definizioni_service` ×1; il ramo «non riconosciuto» chiude con
     `raise exc`) e `_translate_nota_integrity_error` (`catalogo_service` ×2);
   * 4 `ErrorManager.require(False, ...)` → `raise_error`: `soggetti_service` ×2,
     `amm_software_service` e `auth_helpers` (questi due dentro un `except`, con `cause=exc`);
   * ⚠️ **una terza forma**, fuori dai conteggi sopra: `raise  # pragma: no cover`, 10 punti.
     Seguono `raise_error` (`lista_preset_admin_service` ×2, `lista_colonna_admin_service` ×1),
     `map_integrity_error` (`partitioned_note_service` ×2) e i due `_traduci` di `vendite`
     (`famiglie_service` ×2, `registri_service` ×2), ora `NoReturn`: chiudono entrambi con
     `map_integrity_error`. Tolta anche la riga dall'esempio d'uso nel commento di
     `map_integrity_error`, che insegnava la forma;
   * presidio: `test_error_manager` n. 5 controlla `NoReturn` anche sui quattro traduttori
     nuovi. Nel codice applicativo non restano né `raise` di comodo né `require(False)`.

   Non c'è un type checker in CI: `NoReturn` oggi lo legge l'editor, e un test come
   `test_error_manager` ne prova la verità.

---

## 5. Ordine consigliato

1. **§3.5 chiave di cifratura separata**: è piccola, sblocca §3, e rende indolore ruotare la
   `SECRET_KEY` (quella rimasta nella storia del repo: non urgente, il repo è privato, ma è il
   momento naturale per farlo).
2. **§4 ruff `B`**: solo backend, nessuna decisione aperta.
3. **§1 header**, prima come `Report-Only`: non rompe niente, e intanto si raccolgono le
   violazioni.
4. **§2 token in cookie**: tocca login, refresh e logout di tre canali, più il FE. Va fatto
   **prima** di rendere applicata la CSP? No, sono indipendenti, ma insieme chiudono lo stesso
   rischio (uno script iniettato): conviene tenerli vicini.
5. **§3 TOTP**, dopo le decisioni del DB (§3.3) e l'ok sulle dipendenze (§3.4).

## 6. Decisioni aperte per Tid

| # | Domanda | § |
| --- | --- | --- |
| 1 | ✅ HSTS a `0` dichiarato sulla macchina di sviluppo (Tid, 2026-09-28) | 1.3 |
| 2 | ✅ Più schede: coordinamento fra schede (strada A), access a 10 minuti (Tid, 2026-09-28) | 2.4 |
| 3 | ✅ Obbligo del secondo fattore: **entrambi** — flag sulla credenziale più regola automatica per gli account privilegiati (Tid, 2026-09-28) | 3.3 |
| 4 | ✅ Dipendenze TOTP e QR: librerie esistenti (Tid, 2026-09-28) | 3.4 |
| 5 | ✅ Il cancello degli obblighi (A-8) si fa **prima** del TOTP, come lotto T-0, con cambio password e secondo fattore nella stessa sede; A-7 resta in L-6 (Tid, 2026-09-30) | 3.4-bis |
| 6 | ✅ I codici mancanti con un mini brief DB, il BE lavora in parallelo e il merge aspetta l'apply (Tid, 2026-09-30) | 3.4-bis |
| 7 | ✅ L'utente che disattiva da sé il proprio device presenta un codice TOTP **o** di recupero: una sessione rubata da sola non spegne il secondo fattore (Tid, 2026-09-30) | 3.4-bis |
| 8 | ✅ Il `SUPER_ADMIN` che disattiva il device di un altro **non** chiude le sue sessioni: sono state aperte col secondo fattore, e il telefono perso non le compromette (Tid, 2026-09-30) | 3.4-bis |
| 9 | ✅ La rotazione delle chiavi per il segreto TOTP: un verbo DB che sostituisce il segreto **solo se è ancora quello letto**, chiamato dal comando di rotazione senza un utente (strada A; scartate la sola sessione del migratore, che porterebbe le sue credenziali sul server del backend, e il rinvio). Brief: [brief-db-totp-ricifra-segreto.md](brief-db-totp-ricifra-segreto.md) (Tid, 2026-10-01) | 3.4-bis |
| 10 | ✅ Gli smoke bash col secondo fattore attivo sull'utente con cui entrano (`SMOKE_USER`, default `tid`, SUPER_ADMIN): il BB `_smoke_secondo_fattore.sh` (`curl_login`) fa il secondo passo col segreto in `SMOKE_TOTP_SECRET` e il codice calcolato col venv, aspettando un passo nuovo fra due login. Scartati: un utente degli smoke senza obbligo (non può essere SUPER_ADMIN, che l'obbligo l'ha sempre, e gli smoke di amministrazione lo vogliono) e togliere l'obbligo al SUPER_ADMIN (contro D-T1, e non risolve: il problema è il device, non l'obbligo) (Tid, 2026-10-02) | 3.4-bis |

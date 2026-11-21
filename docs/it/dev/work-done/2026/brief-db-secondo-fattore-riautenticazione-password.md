# Brief BE → DB — Secondo fattore: la password per registrare il device

> **Chi scrive:** backend (`dev/backend-tid`), 2026-10-02. **A chi:** team DB (`dev/db-tid`).
> **Origine:** revisione del giro BE/FE del secondo fattore (chiuso in
> [brief-be-fe-sicurezza-header-token-mfa.md](brief-be-fe-sicurezza-header-token-mfa.md) §3.4-bis).
> **Decisione di Tid (2026-10-02):** `registra/` chiede la password della credenziale.
> **Stato:** ✅ **CHIUSO il 2026-10-03.** R-1 applicato (DB); BE/FE fatto (§5), col
> cambio password sotto lo stesso freno (§5.1); collaudo a video superato (§5.2); il
> freno che chiude la sessione e la scheda utente (§5.3), collaudati da Tid lo stesso
> giorno. Nessun residuo aperto.

## 1. Il problema

`POST /api/v1/auth/secondo-fattore/registra/` e `conferma/` chiedono la sola sessione.
Chi tiene una sessione rubata di un utente **senza device** (con o senza obbligo) può
legare il **proprio** telefono: al login dopo, il titolare si ferma al secondo passo e
resta fuori.

È la stessa debolezza che la decisione 7 ha chiuso per la disattivazione («una sessione
rubata da sola non spegne il secondo fattore»), dal verso opposto: qui la sessione da sola
lo **accende per conto di un altro**. Il cambio password chiede già la password attuale;
la registrazione del secondo fattore no.

## 2. Cosa farà il backend (dopo R-1)

* `registra/` vuole `{password}`. Prima di tutto il freno della credenziale
  (`check_blocco_login`), poi `check_password`.
* Password sbagliata = **tentativo fallito** (D-T2, `script.fn_registra_tentativo_login`
  con `successo = false`), come un codice sbagliato: chi tiene la sessione non deve poter
  provare password senza freno. Password giusta: non azzera i tentativi (non è un login).
* La regola vale **sempre**, anche al primo accesso con l'obbligo: una sola regola, e la
  pagina «Sicurezza» chiede la password nello stesso modulo che avvia la configurazione.
* `conferma/` resta com'è: chiude una configurazione che `registra/` ha già protetto.

## 3. Richieste al team DB

| # | Cosa | Perché |
| --- | --- | --- |
| **R-1** | Codice nuovo `E_TOTP_PASSWORD_NON_VALIDA`, classe `DATO_ERRATO`, campo `password`, in `codici_errore.csv` e `messaggi_errore.csv` (it, con causa e soluzione). Proposta di frase: «Password non corretta.» — causa «La password non è quella dell'accesso.», soluzione «Inserire la password con cui si accede.». Lo solleva il **backend** (la verifica della password è di Django), come `E_TOTP_CODICE_NON_VALIDO`; conta come tentativo fallito (D-T2) | Nessun codice a catalogo dice «password sbagliata» fuori dal cambio password: `E_CHANGE_PASSWORD` è di un'altra operazione; `E_AUTHENTICATION_FAILED` è un 401, e un 401 sul frontend fa partire il rinnovo della sessione e poi il logout |

**Esito R-1 (DB, 2026-10-03).** Una riga in `80_data/sql/config/codici_errore.csv`
(`DATO_ERRATO`, la nota dice chi lo solleva, perché non è un 401 e `campo = password` nel
contesto) e una in `messaggi_errore.csv` (id **1189**), con la frase, la causa e la
soluzione proposte senza cambi. Nessun changeSet nuovo: i due CSV li ricarica il loader
del seed. Frase chiusa, nessun segnaposto.

Dopo l'apply il BE rigenera `error_policies_generated.py` e aggiunge il ripiego senza
segnaposto in `error_messages_fallback.py`.

## 4. Ordine

1. DB: R-1 (seed dei due CSV), apply e corsa pgTAP di Tid.
2. BE: `registra/` con la password e il freno; test (password giusta, sbagliata che conta,
   assente, credenziale bloccata); manuale `api_secondo_fattore.md`.
3. FE: il campo password nel modulo di avvio della configurazione in `SicurezzaView`.

## 5. Esito BE/FE (2026-10-03)

* **Codici.** `error_policies_generated.py` rigenerato col DB allineato a git: entra
  `E_TOTP_PASSWORD_NON_VALIDA` (`DATO_ERRATO`) e, rimasto indietro dal giro IVA per
  cassa, `E_EMITTENTE_REGIME_CONFERMA_DERIVATA` (`TECNICO`). Il ripiego senza
  segnaposto per **tutti e due** in `error_messages_fallback.py`.
* **BE.** `SecondoFattoreService.avvia_configurazione(user, password, provenienza=…)`:
  `check_blocco_login`, poi `check_password`; sbagliata → `fn_registra_tentativo_login`
  con `successo = false` e 400 `E_TOTP_PASSWORD_NON_VALIDA` (`campo = password`); assente
  → stesso codice, **non** conta (come la prova senza codice); giusta → nessun
  tentativo registrato. `registra/` legge `{password}` e la provenienza col BB
  `provenienza_obbligatoria`. `conferma/` invariato.
* **Test.** View coi mock (`test_secondo_fattore_views`: giusta, sbagliata che conta,
  assente che non conta, credenziale bloccata che ferma prima di `check_password`);
  DB vero (`test_obblighi_e_secondo_fattore_db`:
  `test_la_password_sbagliata_conta_e_frena_la_configurazione` — `max_tentativi`
  password sbagliate da una provenienza, poi la giusta trova `E_UTENTE_BLOCCATO` e il
  device non nasce). 12/12 verdi con `ZEROERP_TEST_DB_E2E=1`.
* **FE.** `SicurezzaView`: l'avvio (e il «ricomincia») è un form con il campo
  `Password` (stesso pezzo di `ChangePasswordView`, `autocomplete=current-password`),
  pulsante spento senza password; l'errore arriva nella card con la frase del
  backend. `registraSecondoFattore(password)`. Chiave i18n
  `auth.secondo_fattore.chiedi_password` (it/en).
* **Manuale.** `api_secondo_fattore.md`: corpo di `registra/`, la regola, i due codici.

### 5.1 Il cambio password senza freno — chiuso (2026-10-03, ok Tid)

`POST /auth/change-password/` verificava la password attuale con il solo
`check_password`: chi teneva una sessione rubata ne provava quante voleva (la view
non ha un throttle suo). Era lo stesso difetto di `registra/`, dal verso del cambio
password — e il più grave dei due, perché alla password giusta il titolare resta fuori.

Chiuso con un BB, regola del 2: `verifica_password_con_freno`
(`apps/core/services/password_con_freno.py`), chiamato dal cambio password
(`E_CHANGE_PASSWORD`, campo `old_password`) e da `registra/`; ritirata la copia in
`SecondoFattoreService`. Nel cambio password la verifica sale **in testa**, prima
delle regole sulla nuova password. Test: `test_change_password_token_veste` n. 6-9
(sbagliata conta, assente no, frenata ferma prima, l'ordine con una nuova debole).
Censiti i punti che verificano una password: login (freno suo), cambio password,
`registra/` — gli altri flussi usano un token monouso.

### 5.2 Collaudo a video (Tid, 2026-10-03) — superato

Con l'utente `pochi`, senza secondo fattore:

1. «Sicurezza dell'accesso», password sbagliata → «Password non corretta.» nella card,
   nessun QR, sessione intatta; password giusta → QR, chiave e codici.
2. Configurazione lasciata a metà → «Ricomincia la configurazione», che chiede di
   nuovo la password.
3. `/change-password` con l'attuale sbagliata → «Password attuale non corretta.»,
   nessun logout.
4. Ripetuto fino al blocco → «Troppi tentativi non riusciti da questa postazione:
   riprovare fra 15 minuti.», nessun logout.
5. Credenziale frenata, «Ricomincia» con la password **giusta** → il messaggio del
   blocco, nessun QR: il freno è uno per login, cambio password e `registra/`.

Smoke: `smoke-test-core.sh` §13 (un tentativo sbagliato per endpoint, mai fino al
blocco: non c'è un'API che azzeri il freno dei tentativi), 37/0 sul server.

### 5.3 Dopo il collaudo — la sessione al freno, la scheda utente (2026-10-03)

**Il freno chiude la sessione (decisione A di Tid).** Al collaudo, a postazione
bloccata, la sessione da cui si erano provate le password restava al lavoro (`/` e
dentro). Il blocco dell'amministratore chiude già tutte le sessioni; quello da
tentativi no, e finché le prove venivano solo dal login non serviva. Da qui le prove
vengono anche da dentro una sessione — il caso della sessione rubata. Ora
`verifica_password_con_freno` riceve la `request` e, quando trova la postazione
frenata (`E_UTENTE_BLOCCATO`) o la fa frenare col tentativo sbagliato, chiude **quella**
sessione (refresh del `sid` in blacklist, riga `LOGOUT` con `motivo = FRENO_PASSWORD`)
e risponde col freno del DB, coi minuti. Non le altre: darebbe a chi ne tiene una
rubata il modo di buttare fuori il titolare. `E_LOGIN_ATTESA` non chiude. Il frontend
(`seSessioneChiusaDalFreno`) azzera la sessione e porta al login con «Sessione chiusa:
troppe password sbagliate…». ⚠️ L'access già emesso a un client che non è il nostro
vive fino alla scadenza (10 minuti), come dopo ogni logout.
Trovato scrivendolo, sul DB vero: il controllo del blocco va in un **savepoint**, o il
rifiuto del DB — sotto una transazione del chiamante — si porta via il tentativo
appena registrato (provato per mutazione). Regola del 2: `sid_corrente` in
`request_context`, ritirato `_get_current_sid` di `sessioni_view`.

**La scheda utente.** Il cambio password non aveva una voce di menu né un link per
uscirne. Ora il badge dell'utente (in alto a sinistra) apre `SchedaUtentePopover`:
nome, utente, ruolo e le due azioni, «Cambia password» e «Sicurezza dell'accesso»
(uscita dal kebab delle preferenze). La conferma con schede modificate è una sola per
le due pagine. `ChangePasswordView` ha «Torna all'applicazione» fuori dall'obbligo.
La guida `risorse-umane-e-accessi.md` diceva «Profilo → Cambia password», una voce che
non esisteva: allineata.

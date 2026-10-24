# API secondo fattore (TOTP) — configurazione e amministrazione

## Scopo

Gestisce il secondo fattore di autenticazione (codice a tempo, RFC 6238) di una credenziale: la configurazione fatta dalla persona stessa (QR, chiave, codici di recupero, conferma), la rigenerazione dei codici di recupero e la disattivazione dietro un codice; per il SUPER_ADMIN l'obbligo sulla credenziale e la disattivazione del device di un altro, con motivo. Il secondo passo del login è in [api_multi_veste_token.md](api_multi_veste_token.md#secondo-passo-del-login-secondo-fattore).

## Contesto

* **La credenziale è una**: device, obbligo e codici valgono per tutte le porte
  (operatore, portale, shop), non per la sola veste.
* **Lo stato e le regole sono del DB** (`config.auth_totp_device`, verbi
  `script.fn_totp_*`, all'app il solo `SELECT`): monouso del passo, consumo dei
  codici di recupero, chi può cosa. Il backend genera il segreto, lo cifra
  (`crypto_service`) e verifica il codice (`totp_service`): il DB non vede mai
  niente in chiaro.
* **L'obbligo** è della credenziale (flag acceso dal SUPER_ADMIN) oppure di un
  profilo (`profili_accesso.richiede_secondo_fattore`; il SUPER_ADMIN lo ha
  sempre). Lo risponde `script.fn_totp_obbligatorio`.
* **Il cancello degli obblighi** (`apps/core/api/cancello_obblighi.py`): con
  l'obbligo pendente e il device non `ATTIVO`, ogni richiesta col Bearer riceve
  403 `E_TOTP_CONFIGURAZIONE_RICHIESTA`, tranne queste view (`obblighi_ammessi`),
  il profilo `/core/me/` e il logout. Il frontend porta alla pagina «Sicurezza
  dell'accesso» leggendo `obblighi_pendenti` di `/core/me/`.

Logica: `apps/core/services/secondo_fattore_service.py`. View:
`apps/core/api/secondo_fattore_views.py` (la propria credenziale) e
`apps/amm_software/api/accessi_views.py` (SUPER_ADMIN).

## Endpoint — la propria credenziale

Autenticazione Bearer; `skip_area_check` (il perimetro è la credenziale del
chiamante, registro `_SU_SE_STESSI` di `test_skip_area_check_registro`).

| Metodo e path | Corpo | Risposta `data` |
| --- | --- | --- |
| `GET /api/v1/auth/secondo-fattore/` | — | `stato` (`ASSENTE` / `DA_CONFERMARE` / `ATTIVO`), `obbligatorio`, `motivo` (`CREDENZIALE` / `PROFILO` / null), `codici_recupero_rimasti` |
| `POST /api/v1/auth/secondo-fattore/registra/` | `{password}` | `qr_data_uri` (data URI di un SVG, per un `<img>`), `segreto` (la chiave, a gruppi di 4), `codici_recupero` (dieci) |
| `POST /api/v1/auth/secondo-fattore/conferma/` | `{codice}` | lo stato, ora `ATTIVO` |
| `POST /api/v1/auth/secondo-fattore/codici-recupero/` | `{codice}` | `codici_recupero` (dieci nuovi: i vecchi non valgono più) |
| `POST /api/v1/auth/secondo-fattore/disattiva/` | `{codice}` o `{codice_recupero}` | lo stato, ora `ASSENTE` |

* `registra/` vuole la **password** della credenziale, sempre — anche al primo
  accesso con l'obbligo: con la sola sessione, chi la tiene rubata legherebbe il
  proprio telefono a un accesso **senza device**, e il titolare resterebbe fuori
  al login dopo. Prima il freno della credenziale (`script.fn_check_blocco_login`), poi la
  password: sbagliata conta come un tentativo fallito (D-T2), assente no; giusta
  **non** azzera i tentativi (non è un login). Quando il freno della postazione
  scatta, la sessione della richiesta si chiude, come nel cambio password
  ([api_token_cambio_password.md](api_token_cambio_password.md)). ⛔ Il rifiuto è 400
  `E_TOTP_PASSWORD_NON_VALIDA` e non un 401, che sul frontend farebbe partire il
  rinnovo della sessione e poi il logout.
* `registra/` mostra segreto, QR e codici **una volta sola**: al DB vanno il
  segreto cifrato e le impronte (SHA-256) dei codici. Su un device `ATTIVO` il DB
  rifiuta (`E_TOTP_DEVICE_GIA_ATTIVO`); su uno `DA_CONFERMARE` la configurazione
  ricomincia.
* `conferma/`: un codice sbagliato **non** conta sul freno (il segreto è appena
  stato dato).
* `codici-recupero/` e `disattiva/` vogliono una prova: una sessione rubata da
  sola non li ottiene. Un codice sbagliato, già usato o di recupero non valido
  conta come un tentativo fallito della credenziale (freno a DB, D-T2).
* `disattiva/` scrive `TOTP_DISABILITATO` in `dbops.sessioni_utente`
  (`dettaglio: {via: APP, chi_agisce, motivo}`) **nella stessa transazione**: se
  la traccia non si scrive, la disattivazione si annulla. Con l'obbligo, il
  cancello riporta subito alla configurazione.

## Endpoint — amministratore (SUPER_ADMIN)

`AdminAPIView`; i verbi del DB ricontrollano il SUPER_ADMIN. La credenziale deve
esistere (`E_CREDENZIALE_NON_TROVATA`, 404), prima di ogni lettura.
⭐ Dal 2026-10-02 la sede e' la **credenziale** (`credenziali/<id>/…`,
brief-db-be-fe-area-accessi): il secondo fattore vale per tutte le sue vesti, e
il tab «Altri accessi» lo gestisce per un cliente del portale come il drawer
operatore per un operatore. Prima stava sotto `operatori/<id>/`: ritirato.

| Metodo e path | Corpo | Risposta `data` |
| --- | --- | --- |
| `GET /api/v1/amm-software/credenziali/<auth_user_id>/secondo-fattore/` | — | lo stato, più `obbligo_sulla_credenziale` |
| `POST …/secondo-fattore/obbligo/` | `{valore: bool}` | lo stato |
| `POST …/secondo-fattore/disattiva/` | `{motivo}` (obbligatorio) | lo stato |

* `obbligo/` accende o spegne il solo flag della **credenziale**: un obbligo che
  viene da un profilo resta (`motivo = PROFILO`). `valore` deve essere un booleano
  JSON: assente, `null` o di altro tipo → 400 `E_AMM_VALIDAZIONE`, verificato
  **prima** dell'esistenza della credenziale.
* `disattiva/` (telefono perso) cancella il device; senza motivo il DB rifiuta
  (`E_TOTP_MOTIVO_OBBLIGATORIO`). Le sessioni aperte **restano** (decisione 8 del
  brief). Traccia come sopra, con `chi_agisce` = il SUPER_ADMIN.
  ⛔ **Mai sulla propria credenziale** (`E_PERMESSO_NEGATO`, 403): per il DB «la
  credenziale stessa» disattiva senza motivo e senza prova, quindi da qui una
  sessione rubata spegnerebbe il secondo fattore del SUPER_ADMIN. Il proprio si
  disattiva da `auth/secondo-fattore/disattiva/`, con un codice.
* Il segno del profilo di reparto si scrive con `PUT reparti/<uo_id>/profilo/`,
  campo `richiede_secondo_fattore` (assente = invariato).

## Output

Envelope standard. Errori principali:

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_TOTP_CODICE_NON_VALIDO` | 400 | codice sbagliato o assente |
| `E_TOTP_PASSWORD_NON_VALIDA` | 400 | `registra/` con la password sbagliata o assente (`campo = password`) |
| `E_UTENTE_BLOCCATO`, `E_CREDENZIALE_BLOCCATA` | 403 | `registra/` o una prova con la credenziale frenata dai tentativi, o bloccata dall'amministratore |
| `E_TOTP_PASSO_GIA_USATO` | 400 | codice già usato (anti-replay sul passo di 30 secondi) |
| `E_TOTP_RECOVERY_NON_VALIDO` | 400 | codice di recupero sbagliato o già usato |
| `E_TOTP_DEVICE_ASSENTE` | 409 | conferma senza configurazione avviata, prova senza device attivo |
| `E_TOTP_DEVICE_GIA_ATTIVO` | 409 | `registra/` o `conferma/` su un device attivo |
| `E_TOTP_MOTIVO_OBBLIGATORIO` | 400 | disattivazione da amministratore senza motivo |
| `E_AMM_VALIDAZIONE` | 400 | `obbligo/` senza un `valore` booleano JSON |
| `E_PERMESSO_NEGATO` | 403 | disattivazione da amministratore sulla propria credenziale |
| `E_TOTP_CONFIGURAZIONE_RICHIESTA` | 403 | (il cancello) ogni altra API con l'obbligo pendente |

## Regole

* Il periodo (30 s) e le cifre (6) stanno **solo** in `totp_service`: il DB
  riceve il passo già calcolato. Si accettano il passo di adesso, il precedente
  e il successivo (orologio del telefono), non oltre.
* Il segreto ruota con le chiavi di cifratura (`ricifra_campi_cifrati`) attraverso
  il verbo `script.fn_totp_ricifra_segreto`: la tabella è chiusa all'app.
* Lo sblocco del caso senza via d'uscita (l'unico SUPER_ADMIN senza telefono né
  codici) è del DBA, dal server: [runbook](../../../dev/infra/comandi-utili-run-book.md),
  «Sblocco del secondo fattore».

## Dipendenze DB

`config.auth_totp_device`, `config.credenziali.totp_obbligatorio`,
`config.profili_accesso.richiede_secondo_fattore`; `script.fn_get_totp_device`,
`script.fn_totp_obbligatorio`, `script.fn_totp_registra_device`,
`script.fn_totp_conferma_device`, `script.fn_totp_registra_uso`,
`script.fn_totp_consuma_recovery`, `script.fn_totp_rigenera_recovery`,
`script.fn_totp_disabilita_device`, `script.fn_imposta_totp_obbligatorio`;
`dbops.sessioni_utente` (evento `TOTP_DISABILITATO`).

## Test

`apps/core/tests/api/test_secondo_fattore_views.py` (view e servizio, coi
repository finti), `apps/core/tests/db/test_obblighi_e_secondo_fattore_db.py`
(servizio sui verbi veri, traccia compresa),
`apps/amm_software/tests/db/test_profilo_reparto_secondo_fattore_db.py`.

# Piano — Autenticazione tramite provider esterni (OAuth/OIDC)

> **Tipo documento**: piano di lavoro (DB + backend + frontend).
>
> **Data**: 2026-10-02 · **Stato**: 📋 **PIANIFICATO — non in sviluppo.** Prima di partire si
> decidono le domande aperte di §F.
>
> **Da dove viene**: è la Parte B di
> [autenticazione-due-fattori-e-provider.md](../work-done/autenticazione-due-fattori-e-provider.md),
> estratta il 2026-10-02 quando la Parte A (il secondo fattore TOTP) è stata costruita e quel
> documento archiviato (decisione di Tid). Il modello di partenza — una persona, una credenziale,
> più vesti; tre porte di login — sta nel §0 di quel documento e nella guida
> `guide/risorse-umane-e-accessi.md`; qui non si ripete.
>
> **Cosa c'è già, e OAuth riusa** (2026-10-02):
>
> * il **secondo passo del login**: dopo la prova giusta il login risponde con una **sfida
>   firmata** (porta, provenienza, scadenza) e il JWT nasce solo dopo il codice
>   (`apps/core/api/secondo_fattore_token_views.py`, manuale
>   `backend/core/manual/api_multi_veste_token.md`). Il flusso OAuth arriva allo stesso punto:
>   credenziale trovata → blocco → veste della porta → secondo fattore se richiesto → JWT (§E);
> * il **cancello degli obblighi** (`apps/core/api/cancello_obblighi.py`): cambio password e
>   secondo fattore da configurare fermano ogni richiesta finché non si chiudono;
> * il **freno della credenziale** sulla coppia credenziale + provenienza, e i log di sicurezza
>   di ogni accesso sbagliato (`security.login_fallito`, `security.secondo_fattore_fallito`) e
>   di ogni limite di frequenza (`security.limite_frequenza`).
>
> **Prerequisito**: il piano accessi
> ([piano-be-fe-accessi-credenziale-e-vesti.md](piano-be-fe-accessi-credenziale-e-vesti.md)),
> per i lotti che toccano il ciclo di vita della credenziale.
>
> ⚠️ Il testo di §B è quello del 2026-09-25: i riferimenti al «2FA» e al «passo 2» che lì sono
> futuri oggi sono costruiti (sopra). Dove dissente dal codice, vale il codice.

---

# Parte B — Autenticazione tramite provider esterni (OAuth/OIDC)

## B.1 Obiettivo e scope

Entrare da una o più porte (admin, portale, shop) con un provider OAuth/OIDC
esterno: **Google**, **Microsoft**, **Apple**, estendibile (GitHub, LinkedIn,
IdP aziendali come Okta o un tenant Azure AD).

**Invariante**: il login esterno produce **lo stesso JWT interno** del login
con password (`identita_id`, `ruolo_applicativo`, `sid`). Permessi, GUC e guard
di rotta **non cambiano**.

⭐ **Cosa cambia col modello a credenziale.** Il provider autentica la
**persona**, cioè fa lo stesso lavoro della password: sostituisce la *prova di
possesso della credenziale*, non la scelta della veste, che resta della porta
come oggi. Da qui la domanda di fondo della parte B: il collegamento col
provider sta sulla **credenziale** o sulla **veste**? È **Q-4**. Lo schema qui
sotto è scritto nella forma «sulla credenziale», coerente con D-6 e D-10, ma
**non è deciso**.

## B.2 Schema DB proposto (da confermare dopo Q-4)

### B.2.1 Tabella del collegamento col provider

* [ ] **B.2.1** — Brief al team DB. Forma «sulla credenziale»:

```sql
CREATE TABLE config.credenziali_provider (
    id               BIGSERIAL PRIMARY KEY,
    auth_user_id     INTEGER NOT NULL,        -- FK → django.auth_user in 90_end (forma di casa)
    provider         VARCHAR(50)  NOT NULL,   -- 'google', 'microsoft', 'apple'
    provider_sub     VARCHAR(500) NOT NULL,   -- subject dell'IdP, stabile per provider
    provider_email   VARCHAR(254),            -- email al momento del collegamento (audit/UI)
    provider_name    VARCHAR(255),            -- nome visualizzato (audit/UI)
    attivo           BOOLEAN NOT NULL DEFAULT true,
    linked_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    ultimo_login_at  TIMESTAMPTZ,
    meta             JSONB NOT NULL DEFAULT '{}',
    -- audit standard; storicizzazione: vedi sotto
);

-- Un subject di un provider appartiene a una sola credenziale
ALTER TABLE config.credenziali_provider
  ADD CONSTRAINT uq_credenziali_provider_provider_sub UNIQUE (provider, provider_sub);
```

Nella forma alternativa «sulla veste», la FK punterebbe a
`identita_digitali.id`: la stessa persona dovrebbe collegare Google una volta
per porta.

**Perché così**:

* **UNIQUE `(provider, provider_sub)`**: un account Google porta a una sola
  credenziale; evita il collegamento ombra.
* **FK verso `django.auth_user` in `90_end`**, con `preCondition tableExists` e
  `MARK_RAN`, come `auth_totp_device` e `credenziali`: in CI la FK non c'è.
* **Storico**: a differenza di `credenziali` (che cambia a ogni password
  sbagliata), collegare e scollegare è un atto raro e da tracciare. ❓ Serve lo
  storico sulla riga oppure un registro di eventi? Lo decide il team DB, e
  `ultimo_login_at` non deve generare uno snapshot a ogni accesso.

### B.2.2 I metodi di accesso della credenziale

La versione di aprile aggiungeva `identita_digitali.login_methods TEXT[]`,
tenuto allineato da un trigger. Nel modello attuale i metodi sono della
**credenziale**, e un array derivato da un'altra tabella è una copia che può
divergere.

* [ ] **B.2.2** — ❓ **Q-5**: servono un campo derivato, o bastano la presenza
  di una password utilizzabile più le righe attive di `credenziali_provider`,
  letti da una funzione? Questa pagina propone la **funzione** (nessuna copia),
  ma la decisione è aperta.

### B.2.3 Guard: la credenziale non resta senza modo di entrare

* [ ] **B.2.3** — Brief DB: un guard che rifiuti lo scollegamento dell'ultimo
  provider quando la credenziale non ha una password utilizzabile. Errore
  `E_CREDENZIALE_SENZA_METODO_LOGIN`. Il guard va sulla **credenziale** (è lei
  che resta chiusa fuori), non sulla veste.

## B.3 Backend

### B.3.1 Dipendenze

* [ ] **B.3.1** — Da aggiungere a `backend/requirements.in` (⛔ ok esplicito di Tid):

| Pacchetto                        | Versione | Scopo                              |
| -------------------------------- | -------- | ---------------------------------- |
| `django-allauth[socialaccount]`  | >= 0.57  | Framework OAuth multi-provider     |
| `requests-oauthlib`              | >= 1.3   | Client OAuth per i flussi custom   |

`django-allauth` è preferito a `social-auth-app-django`: è mantenuto, supporta
PKCE nativamente, ha hook espliciti (`pre_social_login`) per agganciarsi alla
nostra risoluzione di credenziale e veste, e supporta OIDC discovery.

### B.3.2 Configurazione

* [ ] **B.3.2** — `settings.py`: `INSTALLED_APPS` (`allauth`,
  `allauth.account`, `allauth.socialaccount` + provider),
  `SOCIALACCOUNT_PROVIDERS` con client id e secret da variabili d'ambiente
  (`OAUTH_PKCE_ENABLED: True`), `SOCIALACCOUNT_ADAPTER =
  'apps.core.api.oauth_adapter.ZeroErpSocialAdapter'`,
  `SOCIALACCOUNT_AUTO_SIGNUP = False`. I segreti stanno in `.env` in sviluppo e
  in un secret manager in produzione; **mai** committati.

### B.3.3 Adapter: dal provider alla credenziale, poi alla veste

* [ ] **B.3.3** — `apps/core/api/oauth_adapter.py`, `pre_social_login`:
  1. ricava la porta dal path;
  2. cerca `(provider, sub)` in `credenziali_provider`;
  3. se lo trova ed è attivo, controlla il **blocco dell'admin** sulla
     credenziale (`fn_check_blocco_login`: il blocco vale da **ogni** porta e
     con **ogni** metodo, Q-7), poi risolve la veste della porta con la stessa
     logica di `MultiVesteTokenSerializer` (senza veste attiva:
     `VesteNonAttivaError`, come oggi);
  4. se non lo trova:
     * porta **admin** → rifiuto `E_OAUTH_OPERATORE_NON_INVITATO` (gli
       operatori si invitano; il primo accesso OAuth collega la credenziale
       creata dall'invito);
     * porte **portale/shop** → ❓ nuova registrazione, oppure collegamento a
       una credenziale esistente per email? Con l'email unica (D-9) il rischio
       di presa di possesso è concreto (§B.5.2): **Q-8**;
  5. aggiorna `ultimo_login_at` ed emette il JWT (B.3.5).

| Porta del callback           | Veste                                   | Registrazione autonoma? |
| ---------------------------- | --------------------------------------- | ----------------------- |
| `/api/v1/admin/oauth/`       | `OPERATORE`                             | ❌ solo invito          |
| `/api/v1/portale/oauth/`     | `CLIENTE_PORTALE`, `FORNITORE_PORTALE`  | ❓ Q-8                  |
| `/api/v1/shop/oauth/`        | `SHOP_CUSTOMER`                         | ❓ Q-8                  |

### B.3.4 Endpoint OAuth per porta

* [ ] **B.3.4**:
  * `GET /api/v1/{porta}/oauth/<provider>/authorize/`: redirect al provider;
    `state` e PKCE generati lato server e salvati in Redis (TTL 10 minuti,
    chiave `oauth_state:<uuid>`);
  * `GET /api/v1/{porta}/oauth/<provider>/callback/`: scambio del code,
    risoluzione (B.3.3), JWT. Se serve il secondo fattore (Q-9) risponde con la
    **sfida firmata** del secondo passo, come il login con password
    (`two_factor_required` + `sfida`, poi `/{porta}/token/secondo-fattore/`: esiste dal
    2026-10-02, `secondo_fattore_token_views.py`);
  * `POST /api/v1/auth/oauth/<provider>/link/`: collegamento da un utente già
    entrato (§B.5.2);
  * `POST /api/v1/auth/oauth/<id>/unlink/`: scollegamento (dall'utente stesso
    o dall'admin), soggetto al guard di §B.2.3.

### B.3.5 Emissione del JWT dopo OAuth

* [ ] **B.3.5** — Un metodo di `MultiVesteTokenSerializer` (o un helper
  condiviso con il login a password) che emetta la coppia di token per una
  credenziale e una porta **senza** verificare la password. Resta **una sola**
  risoluzione della veste e **un solo** punto di emissione, con metadati di
  sessione `metodo_login = 'oauth_<provider>'`.

### B.3.6 Codici errore

* [ ] **B.3.6** — In `codici_errore.csv` (con la rigenerazione di policy e ripiego):
  `E_OAUTH_STATE_INVALIDO`, `E_OAUTH_CODE_SCAMBIO_FALLITO`,
  `E_OAUTH_PROVIDER_SUB_MANCANTE`, `E_OAUTH_EMAIL_NON_VERIFICATA`,
  `E_OAUTH_OPERATORE_NON_INVITATO`, `E_OAUTH_MAPPING_GIA_LINKATO`,
  `E_OAUTH_PROVIDER_DISABILITATO`, `E_CREDENZIALE_SENZA_METODO_LOGIN`.

## B.4 Frontend

* [ ] **B.4.1** — `LoginView.vue`: la sezione «Oppure accedi con» mostra i
  provider configurati **per quella porta** (`/api/v1/{porta}/oauth/providers/`).
  Il clic avvia un redirect vero del browser (non una chiamata XHR). Al ritorno
  il backend consegna il JWT al frontend. ❓ Come consegnarlo (frammento
  dell'URL o cookie di breve durata) è da decidere insieme al trasporto dei
  token di oggi.
* [ ] **B.4.2** — «Account collegati» nella sezione Sicurezza del profilo:
  elenco dei provider (provider, email, collegato il, ultimo accesso),
  «Collega…» e «Scollega», con avviso se lo scollegamento lascerebbe la
  credenziale senza modo di entrare.
* [ ] **B.4.3** — Pannello operatore (admin): i metodi di accesso **della
  credenziale** (password, provider, 2FA) e «Scollega provider» d'emergenza.

## B.5 Sicurezza — punti critici

### B.5.1 State CSRF e PKCE

`state` casuale di 32 byte URL-safe, in Redis con TTL 10 minuti, legato alla
sessione. PKCE su tutti i provider che lo supportano; con Apple è obbligatorio.

### B.5.2 Collegamento sicuro

**Lo scenario**: Mario ha la password su `mario@example.com`; qualcuno crea
`mario@example.com` presso un provider e prova a collegarlo. Collegare **per
email** significa consegnargli l'account. Con portale e shop che entrano per
email (D-9), l'email è una chiave: il rischio è maggiore, non minore.

**Decisione di aprile, confermata**: **mai** collegare automaticamente per
email. Il collegamento richiede sempre una di queste due cose:

* un utente già entrato con la password, più una conferma tramite OTP via email;
* per gli operatori, un collegamento preparato dall'admin al momento
  dell'invito.

### B.5.3 Revoca lato provider

Se il provider disabilita l'account, il JWT resta valido fino alla scadenza.
Si può ricontrollare presso il provider a ogni refresh (+1 chiamata), oppure
usare i webhook di revoca (fuori MVP). Il **blocco dell'admin** della
credenziale resta il modo immediato per chiudere, da ogni porta e con ogni
metodo.

### B.5.4 Email non verificata

Se il provider non dichiara `email_verified`, il login è rifiutato con
`E_OAUTH_EMAIL_NON_VERIFICATA`, su tutte le porte.

### B.5.5 GDPR (documentazione, non codice)

* [ ] **B.5.5** — Informativa privacy (quali dati del provider si conservano),
  DPA con i provider, prova del consenso (`linked_at` +
  `meta.consent_text_version`), diritto all'oblio (cancellazione del
  collegamento, e dello storico se c'è).

## B.6 Test

* [ ] **B.T.1** — Callback simulato: credenziale trovata, veste della porta
  risolta, JWT con i claim giusti.
* [ ] **B.T.2** — Porta admin senza invito → `E_OAUTH_OPERATORE_NON_INVITATO`.
* [ ] **B.T.3** — `state` scaduto → `E_OAUTH_STATE_INVALIDO`.
* [ ] **B.T.4** — Email non verificata → `E_OAUTH_EMAIL_NON_VERIFICATA`.
* [ ] **B.T.5** — Collegamento da utente entrato: OTP chiesto, verificato,
  collegamento creato.
* [ ] **B.T.6** — Scollegamento dell'ultimo metodo → `E_CREDENZIALE_SENZA_METODO_LOGIN`.
* [ ] **B.T.7** — 2FA dopo OAuth (Q-9): il callback emette il `two_factor_token`, non il JWT.
* [ ] **B.T.8** — Lo stesso `provider_sub` non si collega a due credenziali (UNIQUE).
* [ ] **B.T.9** — Credenziale bloccata dall'admin → il login OAuth è rifiutato.
* [ ] **B.T.10** — Credenziale collegata senza la veste della porta →
  `VesteNonAttivaError`, come con la password.

## B.7 Infrastruttura

* **Variabili d'ambiente**: `OAUTH_GOOGLE_CLIENT_ID/SECRET`,
  `OAUTH_MICROSOFT_CLIENT_ID/SECRET/TENANT`,
  `OAUTH_APPLE_TEAM_ID/KEY_ID/PRIVATE_KEY_PATH`,
  `OAUTH_REDIRECT_URI_{ADMIN,PORTALE,SHOP}`.
* **Console dei provider**: redirect URI in whitelist per ogni ambiente.
* **Redis**: quello che c'è (`django_redis`, `REDIS_URL`); in CI si usa
  `LocMemCache`, e per lo `state` basta.

---


# C. Stima e ordine consigliato

| Fase                                                          | Sprint | Complessità |
| ------------------------------------------------------------- | :----: | ----------- |
| **B.1 MVP OAuth** — Google sulla porta admin                  |   1    | Bassa-Media |
| **B.2** — Microsoft + porta portale                           |   1    | Bassa       |
| **B.3** — Collega/scollega + conferma OTP                     |  ~1    | Media       |
| **B.4** — Shop con registrazione autonoma + Apple (se Q-8 la ammette) |   1    | Media       |
| **B.5** — Rafforzamento: validazione al refresh, revoca, WebAuthn |   2+   | Alta        |

**Ordine**: si decide §F, poi il brief DB di §D, poi le fasi in ordine. Il secondo passo del
login e il cancello, che servono anche all'OAuth, esistono già.

---

# D. Brief DB (da passare al team DB, dopo §F)

* [ ] **D.2.a** — La tabella del collegamento col provider (§B.2.1), nella sede
  decisa da Q-4, con UNIQUE `(provider, provider_sub)` e FK in `90_end`.
* [ ] **D.2.b** — I metodi di accesso della credenziale (§B.2.2, Q-5).
* [ ] **D.2.c** — Il guard contro la credenziale senza metodo di accesso (§B.2.3).
* [ ] **D.2.d** — Storico o registro di eventi per collegamenti e scollegamenti.
* [ ] **D.2.e** — I codici errore (§B.3.6) in `codici_errore.csv`.

I changeSet seguono le convenzioni di
[linee-guida-sql.md](../../linee-guida-sql.md) e, per i guard,
[linee-guida-trigger.md](../../linee-guida-trigger.md).

---

# E. 2FA e OAuth insieme

* **Tutti e due sono della credenziale**: il 2FA protegge la persona, OAuth è
  un altro modo per dimostrare di essere lei. Il flusso composto è: OAuth →
  credenziale trovata → controllo del blocco → veste della porta → TOTP (se
  richiesto) → JWT.
* Chi ha password e Google collegato continua a entrare con l'una se l'altra
  viene tolta; il guard di §B.2.3 impedisce di toglierle tutte.
* I codici di recupero valgono qualunque sia il metodo di accesso.
* **Il blocco dell'admin vale per tutti i metodi e per tutte le porte.**

---


# F. Domande aperte (da decidere con Tid prima dello sviluppo)

Le domande del secondo fattore (Q-1, Q-2, Q-3, Q-6) sono chiuse e stanno nel documento
d'origine. Restano queste; la Q-10 è di fatto decisa (il reset della password non tocca il
dispositivo) e va solo confermata.

| # | Domanda | Possibili risposte | Dove pesa |
| --- | --- | --- | --- |
| **Q-4** | **Il collegamento col provider sta sulla credenziale o sulla veste?** | credenziale (un collegamento per persona, coerente con D-6 e D-10), oppure veste (un collegamento per porta) | B.2.1, B.3.3, D.2.a |
| **Q-5** | **I metodi di accesso sono un campo o una lettura?** | un campo derivato mantenuto da trigger, oppure una funzione che li calcola | B.2.2, D.2.b |
| **Q-7** | **Blocco dell'admin e OAuth**: la credenziale bloccata resta chiusa anche via provider? (Proposta: sì.) E il cambio password obbligatorio vale per chi entra solo via provider? | sì / no; per il cambio password: si ignora, oppure si chiede lo stesso | B.3.3, B.T.9 |
| **Q-8** | **Registrazione autonoma via provider su portale e shop**: si ammette? Se l'email esiste già come credenziale, cosa succede? | nessuna registrazione autonoma; oppure registrazione solo con email nuova; mai il collegamento automatico per email (§B.5.2) | B.3.3, B.4, §C fase B.4 |
| **Q-9** | **Il 2FA dopo OAuth**: richiesto sempre, oppure ci si fida dell'MFA dichiarato dal provider (claim `amr`)? | sempre (proposta di aprile, la più sicura); oppure fiducia verso una whitelist di provider | B.3.4, B.T.7 |
| **Q-10** | **Il reset della password tocca il 2FA?** Il reset dimostra solo il possesso dell'email; come il blocco dell'admin, il 2FA dovrebbe restare. | il dispositivo resta (proposta); oppure il reset lo disattiva | A.2.1, `password-reset-confirm` |

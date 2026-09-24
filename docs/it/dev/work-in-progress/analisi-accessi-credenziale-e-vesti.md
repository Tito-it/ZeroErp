# Analisi — Accessi: una credenziale, più vesti, un ciclo di vita solo

> **Origine:** difetto M-4 di
> [analisi-be-difetti-emersi-verifica-doc-api-core.md](analisi-be-difetti-emersi-verifica-doc-api-core.md)
> («il blocco login vale solo per la veste OPERATORE»), 2026-09-24. Alla
> domanda «per veste o per credenziale?» Tid ha risposto:
> *«non dovrebbe essere per veste ma per credenziali e dovrebbe essere tutto
> uniformato: uno user "operatore" o uno user "shop" ecc. deve avere la stessa
> logica per accessi/attivazioni/disattivazioni»*.
>
> **Cosa contiene:** l'inventario di come funziona **oggi** il ciclo di vita di
> un accesso per ogni veste (§2), i difetti che ne escono (§3), il modello
> proposto (§4) e le domande che decide Tid (§5). Non contiene codice: dalle
> decisioni nasceranno un brief DB e un piano BE/FE (§6).
>
> **Stato:** ⏳ analisi — decise da Tid il 2026-09-24 **tutte e dieci**
> (§5). Brief DB scritto:
> [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md).
>
> **Come leggere «Verificato»:** ✅ = riletto sul codice o sulla doc
> auto-generata da chi scrive (2026-09-24); 🔎 = dall'inventario per lotti, con
> prova `file:riga`, da rileggere prima di correggere.

---

## 1. Il principio deciso

Due oggetti, e ciascuno ha le sue regole:

| Oggetto | Cos'è | Tabella |
| --- | --- | --- |
| **Credenziale** | chi sei: username + password | `django.auth_user` |
| **Veste** | da quale porta entri: operatore, portale cliente/fornitore, shop | `anagrafiche.identita_digitali` (`ruolo_applicativo`) |

⭐ **Decisione di Tid, 2026-09-24:**

1. il **blocco per password errate è della credenziale**, non della veste. La
   password è una sola e vale per tutte le porte: chi prova password la sta
   provando per tutte;
2. **accessi, attivazioni e disattivazioni seguono la stessa logica per ogni
   veste**. Cambia la porta, non il ciclo di vita.

⚠️ La guida [architettura-multi-face-auth §3.1](../../guide/architettura-multi-face-auth.md)
e il manual `anagrafiche/manual/identita_digitali.md` dicono il contrario
(*«lo stato di lockout è per-identità: un lockout sul portale non blocca lo
shop»*). Vanno riscritti con la decisione, nello stesso giro del codice.

---

## 2. Inventario — com'è oggi

I percorsi sono relativi a `backend/apps/` e a `docs/it/dbzero/`.

### 2.1 Invito

| | OPERATORE | PORTALE (cliente/fornitore) · SHOP | |
| --- | --- | --- | --- |
| Service | `anagrafiche/services/invito_operatore_service.py:46` | `portale/services/invito_portale_service.py` `_invia_invito_common` | 🔎 |
| Chi può invitare | `AdminAPIView` (solo SUPER_ADMIN) | `DomainAPIView`, area `anagrafiche` | 🔎 |
| Crea la credenziale? | no: esiste già, la crea `create_operatore` con la password scelta dall'admin; email duplicata rifiutata | sì se manca, cercandola per email; nasce col segnaposto `!` (password non utilizzabile) | ✅ portale · 🔎 operatore |
| Identità all'invito | **già attiva** (la crea `fn_crea_risorsa_umana_v2` con `attivo=true`) | **non attiva** fino al consumo del token (dal 2026-09-24, M-3) | ✅ portale · 🔎 operatore |
| Password | **sovrascritta** con una casuale mai comunicata (`invito_operatore_service.py:77-82`) | non toccata; il flusso lo decide «ha una password vera?» | 🔎 · ✅ |
| `deve_cambiare_password` | `true` sulla veste | `false` | 🔎 |
| Reinvio | invalidazione dei token **fuori** dalla transazione (`:150-152`), password ri-sovrascritta | invalidazione dentro la stessa transazione | 🔎 |
| Guard «ha già accesso» | `auth_user.last_login IS NULL` in `script.fn_check_operatore_invitabile` — ma **nessuno scrive `last_login`** (grep vuoto nel backend; `UPDATE_LAST_LOGIN` di SimpleJWT a default `False`) | «identità della veste già attiva → rifiuto» | ✅ `last_login` · 🔎 guard |

### 2.2 Attivazione (consumo del token)

| | OPERATORE (`core/api/attivazione_view.py`) | PORTALE · SHOP | |
| --- | --- | --- | --- |
| Attiva l'identità? | no — è già attiva | sì, nella stessa transazione, in entrambi i flussi | ✅ portale/shop · 🔎 operatore |
| `identita_id` nel token | facoltativo: se manca il flag si azzera su **tutte** le vesti attive | obbligatorio | 🔎 |
| Esiste anche senza token | — | lo shop, da un cliente portale loggato (`ProfileActivateShopView`): nasce attiva, e **riattiva** anche una veste revocata dall'admin | 🔎 |

### 2.3 Login e richieste

| Regola | Com'è oggi | |
| --- | --- | --- |
| Blocco per password errate | `script.fn_check_blocco_login` / `fn_registra_tentativo_login` ricevono il solo `auth_user_id` e leggono/scrivono **la riga `ruolo_applicativo = 'OPERATORE'`**. Chi non ha quella riga non viene mai contato né bloccato; chi ce l'ha viene bloccato anche sbagliando sul portale | ✅ |
| Perché è così | residuo: le funzioni sono nate su `risorse_umane_auth_user`, operatori per natura; l'hotfix del 19-04 (`20260419-93/-94`, dopo il passaggio al modello multi-veste) ha spostato le scritture su `identita_digitali` filtrando `OPERATORE` per non cambiare perimetro in urgenza | ✅ |
| Parametri | `login_max_tentativi_falliti` (5) e `login_blocco_minuti` (15): **globali**, letti da `config.parameters.default_value` senza la cascata degli override | ✅ |
| Throttle | `LoginRateThrottle` 5/5 min **per IP**, condiviso dai tre namespace | 🔎 |
| Periodo di validità della veste | `valido_dal`/`valido_al` **non** letti al login né a ogni richiesta: contano solo nell'OR che calcola `auth_user.is_active` | 🔎 |
| Cambio password obbligatorio | `PasswordChangeRequiredMiddleware.process_view` guarda `request.user` di Django, che per il JWT a quel punto è ancora anonimo (stesso schema di S-2): **probabilmente non scatta mai**. Oggi lo fa rispettare solo il frontend | ✅ il meccanismo · 🔎 l'effetto (serve una prova reale) |
| `totp_obbligatorio` | colonna per veste che nessuno legge; il dispositivo TOTP (`config.auth_totp_device`) è 1:1 con la credenziale | 🔎 |

### 2.4 Disattivazione e riattivazione

| | OPERATORE (`amm_software`) | PORTALE · SHOP (`InvitoPortaleService.disattiva_veste_*`) | |
| --- | --- | --- | --- |
| Righe toccate | **tutte le identità della credenziale**, senza filtro sul ruolo, che diventano `attivo=false, ruolo_applicativo='DISABILITATO'` (`amm_software/db/amm_software_repository.py:487-493`) | solo la veste | ✅ |
| Riattivazione | diretta, senza token: **tutte** le identità tornano `attivo=true, ruolo_applicativo='OPERATORE'` (`:528-534`) | solo con un nuovo invito (token) | ✅ |
| Token di sessione (JWT) | blacklist di tutte le sessioni (di tutte le vesti) | nessuna blacklist: l'accesso cade alla richiesta dopo, il refresh riesce ancora | 🔎 |
| Token d'invito pendenti | non invalidati | invalidati | 🔎 |
| Cache permessi | invalidata | **non** invalidata | 🔎 |

### 2.5 Reset e cambio password

Entrambi agiscono sulla **credenziale** (la password è di `auth_user`) e
chiudono tutte le sessioni. Il reset si chiede per **username**, che per portale
e shop è generato dall'email e non compare nelle email d'invito (🔎); il reset
**non** sblocca un utente bloccato (🔎).

---

## 3. Difetti

### 3.1 Del modello — priorità massima

| # | Difetto | |
| --- | --- | --- |
| M-5 | **Disattivare un operatore spegne tutte le vesti della credenziale** e le rinomina `DISABILITATO`: l'operatore che è anche cliente perde il portale, e il ruolo originale di ogni veste va perso | ✅ |
| M-6 | **Riattivare un operatore porta a `OPERATORE` tutte le sue identità.** Una veste cliente o fornitore non può diventare OPERATORE (`trgfn_identita_digitali_guard_coerenza` vuole un soggetto_ruolo RIS_UMANA) e due righe attive con lo stesso ruolo violano l'unique `(auth_user_id, ruolo_applicativo) WHERE attivo`: la riattivazione di un operatore multi-veste **fallisce**, o, se passasse, corromperebbe le vesti. *Deduzione dai vincoli, da provare con un caso costruito* | ✅ il codice · 🔎 l'esito |
| M-4 | Blocco per password errate solo per chi ha la veste OPERATORE (vedi §2.3) | ✅ |

### 3.2 Asimmetrie fra le vesti

| # | Asimmetria | Cosa comporta | |
| --- | --- | --- | --- |
| A-1 | L'invito operatore **sovrascrive la password** della credenziale | se la credenziale ha anche una veste portale o shop attiva, quella perde l'accesso finché l'invito operatore non si attiva | 🔎 |
| A-2 | Il guard «ha già accesso» dell'operatore si basa su `last_login`, che nessuno scrive | un operatore già operativo può essere reinvitato, e si vede sostituire la password | ✅ `last_login` |
| A-3 | Identità operatore **attiva prima** che l'invito sia accettato | l'accesso esiste prima del consenso (con una password ignota, ma esiste) | 🔎 |
| A-4 | Reinvio operatore con invalidazione fuori transazione | lo stesso difetto già chiuso sul portale col fix #17 | 🔎 |
| A-5 | Revoca: blacklist, invalidazione dei token d'invito e della cache presenti in un flusso e assenti nell'altro | una veste revocata resta usabile fino alla scadenza dell'access token, e i permessi in cache restano | 🔎 |
| A-6 | Lo shop si riattiva da solo (`ProfileActivateShopView`) anche dopo una revoca dell'admin | la revoca dell'admin non è definitiva | 🔎 |
| A-7 | Periodo di validità della veste non applicato al login | una veste scaduta resta usabile se la credenziale ha un'altra veste valida | 🔎 |
| A-8 | `PasswordChangeRequiredMiddleware` inerte col JWT | il cambio obbligatorio è affidato al solo frontend | ✅ meccanismo |
| A-9 | La creazione dell'operatore esige una credenziale nuova (email duplicata rifiutata, confronto case-sensitive), il portale la riusa per email (case-insensitive) | la stessa persona non può essere operatore e cliente con una credenziale sola, se diventa operatore per seconda | 🔎 |

---

## 4. Il modello proposto

### 4.1 Cosa è della credenziale, cosa è della veste

| Della **credenziale** (`auth_user`) | Della **veste** (`identita_digitali`) |
| --- | --- |
| la password | `attivo` — la porta è aperta? |
| **il blocco per password errate**: contatore e scadenza | `valido_dal` / `valido_al` — applicati al login **e** a ogni richiesta |
| le sessioni (blacklist) | |
| il cambio password obbligatorio (D-7) | |
| `is_active` = almeno una veste utilizzabile (come oggi) | |

⛔ Il blocco **non** sta su una riga di veste scelta (oggi `OPERATORE`), né su
tutte le vesti copiato: ha una sede della credenziale. Con i parametri globali
di oggi.

### 4.2 Un solo ciclo di vita, per ogni veste

| Passo | Regola unica |
| --- | --- |
| **Invito** | crea la veste **non attiva**; crea la credenziale se manca (col segnaposto non utilizzabile) o riusa quella della stessa persona; **non tocca mai una password esistente**; flusso scelto sulla credenziale («ha una password vera?») — cioè la regola già applicata al portale con M-3 |
| **Reinvio** | invalida i token precedenti **nella stessa transazione** del nuovo; rifiutato se la veste è già attiva |
| **Attivazione** | consuma il token e **attiva la veste**, nella stessa transazione; sceglie la password solo se la credenziale non ne ha una vera |
| **Disattivazione** | tocca **solo quella veste**: `attivo=false`, `ruolo_applicativo` invariato; invalida i token d'invito pendenti, chiude le sessioni **di quella veste**, invalida la cache permessi; se era l'ultima veste utilizzabile, la credenziale si spegne (lo fa già il trigger su `is_active`) |
| **Riattivazione** | **nuovo invito**, per ogni veste (D-3): chi ha già una password attiva con un clic |
| **Blocco** | per credenziale, qualunque porta si stia provando |

Le differenze che **restano** fra le vesti sono solo di **porta**: quale
namespace di login la accetta, quale template email, chi ha il permesso di
invitare. ⭐ Il *permesso* di invitare un operatore può legittimamente essere
diverso da quello di invitare un cliente: è un diritto, non un ciclo di vita.

---

## 5. Decisioni aperte (Tid)

| # | Domanda | Proposta |
| --- | --- | --- |
| D-1 | **Sede del blocco della credenziale**: una tabella 1:1 con `auth_user` in uno schema nostro (le colonne su `django.auth_user` sarebbero dentro una tabella di Django) | ✅ **DECISA (Tid, 2026-09-24): come proposto** — tabella nostra, forma a scelta del team DB; `tentativi_falliti`/`bloccato_fino_a` via da `identita_digitali` nello stesso giro |
| D-2 | Il **reset password riuscito sblocca** la credenziale? | ✅ **DECISA (Tid, 2026-09-24): sì** — chi dimostra di possedere l'email ha già superato la prova che il blocco protegge |
| D-3 | **Riattivazione**: sempre con un nuovo invito (token), come portale e shop, oppure diretta dall'admin per tutte le vesti? | ✅ **DECISA (Tid, 2026-09-24): nuovo invito, per tutte le vesti** (*«ho un dubbio, però credo che sia meglio nuovo invito»*). ⭐ Ciò che scioglie il dubbio: col flusso deciso sulla credenziale, chi ha già una password riattiva con **un clic** (token CROSS, nessuna password nuova) — il costo è un giro di email, e in cambio nessuna veste torna attiva senza che la persona lo sappia. ⇒ la riattivazione diretta di `amm_software` si ritira; la risorsa umana (il rapporto di lavoro) e l'accesso restano due cose: riattivare la persona in HR non riapre la porta |
| D-4 | La **revoca dell'admin** blocca la riattivazione self-service dello shop (A-6)? | ✅ **DECISA (Tid, 2026-09-24): sì** — la veste ricorda di essere stata **revocata dall'amministratore**; da revocata l'attivazione self-service dello shop è rifiutata e si torna solo con un nuovo invito (D-3). «Mai attivata» resta attivabile dal pulsante come oggi |
| D-5 | **Disattivazione**: chiude le sessioni della sola veste o tutte? | ✅ **DECISA (Tid, 2026-09-24): della sola veste** — le sessioni si riconoscono dal claim `identita_id`, che c'è già; le altre vesti della stessa persona restano aperte. Vale per **tutte** le vesti (oggi l'operatore chiude tutto, portale/shop niente) |
| D-6 | L'operatore può **riusare una credenziale esistente** (A-9), come il portale? | ✅ **DECISA (Tid, 2026-09-24): una persona, una credenziale** — la creazione dell'operatore riusa la credenziale esistente per email (stessa regola dell'invito: veste aggiunta, attivazione con un clic e la password che la persona ha già); l'email si confronta **sempre senza distinguere maiuscole e minuscole**, in tutte le strade. ⚠️ Tocca anche il DB: `anagrafiche.fn_crea_auth_user` oggi rifiuta l'email duplicata (`E_ADMIN_EMAIL_DUPLICATA`, confronto case-sensitive) |
| D-7 | Il **cambio password obbligatorio** (`deve_cambiare_password`) è della veste o della credenziale? | ✅ **DECISA (Tid, 2026-09-24): della credenziale** — la password è una sola. Oggi è per veste e il reset lo azzera su tutte, che è già di fatto la lettura per credenziale. Sta nella stessa sede di D-1 |
| D-8 | `last_login`: lo si scrive, o il guard dell'invito operatore passa a «veste già attiva → rifiuto» come il portale? | ✅ **DECISA (Tid, 2026-09-24): tutte e due le cose.** Il guard diventa «**veste già attiva → rifiuto**», uguale per ogni veste (regola unica di §4.2); ⛔ `last_login` non decide più chi si può invitare. **E l'ultimo accesso si registra**: oggi nessuno lo scrive (SimpleJWT ha `UPDATE_LAST_LOGIN` a `False` e il login non lo aggiorna) — va scritto a ogni login riuscito, come informazione («ultimo accesso il…»). Nota per il piano: `last_login` è della credenziale. L'ultimo accesso **per veste** oggi non c'è da nessuna parte: `dbops.sessioni_utente` registra l'evento LOGIN per `auth_user_id`, senza la veste (nessuna colonna, `dettaglio` vuoto) — se servirà, l'evento dovrà portare l'`identita_id` del token (verificato sulla doc auto-generata, 2026-09-24) |
| D-9 | Login e reset per **username**, che per portale/shop è generato: si accede per email? | ✅ **DECISA (Tid, 2026-09-24): la chiave d'ingresso è della PORTA.** Portale e shop: si entra (e si chiede il reset) con l'**email**. Operatore: con il **nome utente**, che si **mostra nell'invito**. ⭐ È una differenza di porta, non di ciclo di vita (§4.2): la credenziale resta una, e la stessa persona entra nel portale con l'email e nel gestionale col nome utente. ⚠️ Condizione: l'email diventa una chiave, quindi **unica senza distinguere maiuscole e minuscole** su `django.auth_user` — oggi il DB non lo garantisce (vincolo da chiedere al team DB, va col D-6) |
| D-10 | `totp_obbligatorio` (per veste, mai letto) | ✅ **DECISA (Tid, 2026-09-24):** il TOTP non si costruisce ora (è una funzione nuova, non un difetto). `identita_digitali.totp_obbligatorio`, che nessuno legge, **esce ora** con le altre colonne; quando il TOTP si farà, l'**obbligo sarà della credenziale** come il dispositivo (`config.auth_totp_device`) — il secondo fattore protegge la password, e la password è una. L'eventuale «questa porta chiede il TOTP in più» si decide allora |

---

## 6. Da qui in avanti

1. Decisioni di §5 — ✅ tutte e dieci prese da Tid il 2026-09-24.
2. **Prova di M-6** con un caso costruito (credenziale con veste operatore +
   cliente portale → disabilita → riattiva), prima di correggere.
3. **Brief DB** — ✅ scritto il 2026-09-24:
   [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md).
   Sede del blocco (D-1), `fn_check_blocco_login` /
   `fn_registra_tentativo_login` per credenziale, sblocco al reset (D-2),
   funzioni o guard che servano alla disattivazione per veste; riscrittura
   del manual `identita_digitali.md` e dei manual delle due funzioni (che
   citano ancora `risorse_umane_auth_user`).
4. **Piano BE/FE**: invito e attivazione operatore sulla regola unica
   (A-1…A-4), disattivazione/riattivazione per veste (M-5, M-6, A-5),
   validità al login (A-7), cambio password obbligatorio che funzioni col JWT
   (A-8), guida `architettura-multi-face-auth` §3.1 riscritta.

---
{% include-markdown "signature-core.md" %}

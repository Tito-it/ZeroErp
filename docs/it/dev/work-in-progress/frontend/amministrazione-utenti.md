# Amministrazione Utenti — WIP

> Documento di lavoro per pianificazione e avanzamento del modulo Amministrazione.
> Dipende da: `docs/it/dev/work-in-progress/permessi-e-autorizzazioni.md` (completato)
> Dipende da: `docs/it/dev/work-in-progress/sviluppi-risorse-umane.md` (completato)
> Guida di riferimento permessi: `docs/it/guide/architettura-permessi-e-autorizzazioni.md`

---

## Posizionamento nello Sviluppo Concentrico

Il modulo Amministrazione appartiene all'**Anello 1 — Infrastruttura Applicativa**.

```
    Anello 1 (Infrastruttura Applicativa)
    ┌────────────────────────────────────────────────────────────┐
    │  Amministrazione (NUOVO — solo ADMIN)                      │
    │                                                            │
    │  + API orchestratore creazione utente                      │
    │  + API gestione permessi utente                            │
    │  + API configurazione profili reparto                      │
    │  + Frontend: area Amministrazione (sidebar dedicata)       │
    └────────────────────────────────────────────────────────────┘
           ↑ usa
    Anello 0 (Nucleo — già esistente)
    ┌────────────────────────────────────────────────────────────┐
    │  config.*            — aree, override, profili reparto     │
    │  anagrafiche.*       — soggetti, risorse_umane, bridge     │
    │  PermissionResolver  — già implementato                    │
    │  ZeroERPPermission   — già implementato                    │
    │  permissions_cache   — già implementato                    │
    │  dbops.sessioni_utente, request_log — già implementati     │
    └────────────────────────────────────────────────────────────┘
```

### Perché Anello 1

1. **Consuma infrastruttura Anello 0** — usa `PermissionResolver`, le tabelle `config.*`,
   `anagrafiche.*`, il sistema di audit già operativo. Non aggiunge logica al nucleo.
2. **Accesso esclusivamente ADMIN** — non passa dal sistema di profili reparto (sarebbe
   ricorsivo); il check è diretto su `ruolo_sistema = ADMIN` tramite decorator/permission
   dedicata `IsAdminZeroERP`.
3. **Nessuna dipendenza inversa** — nessun modulo esterno dipende da questo. È un consumer
   puro delle strutture esistenti.

### Cosa aggiunge al sistema

| Capacità                                    | Prima                                | Dopo                                                                     |
| ------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------ |
| Creazione utente completo da frontend       | Operazione manuale multi-step sul DB | Form unico: soggetto + risorsa_umana + auth_user in un'unica transazione |
| Visualizzazione lista operatori con stato   | Non disponibile                      | Lista con filtri per reparto, ruolo, stato attivo                        |
| Configurazione override permessi per utente | Solo via SQL                         | UI dedicata nel pannello utente                                          |
| Configurazione profilo di un reparto        | Solo via SQL                         | Pagina dedicata per area con toggle TUTTO/LETTURA/BLOCCATO               |
| Consultazione permessi effettivi            | Endpoint già esiste                  | Visualizzato nel pannello utente frontend                                |

---

## Prerequisiti già esistenti

- [x] `auth_user` — autenticazione Django con JWT
- [x] `anagrafiche.soggetti` — anagrafica soggetti (PF e PG)
- [x] `anagrafiche.soggetti_ruoli` — ruoli soggetto (incluso `RIS_UMANA`)
- [x] `anagrafiche.risorse_umane` — con `attivo`, `valido_dal`, `valido_al`, `unita_organizzativa_id`
- [x] `anagrafiche.risorse_umane_auth_user` — bridge 1:1 con `ruolo_sistema`
- [x] `config.ruolo_sistema` — ENUM (ADMIN, OPERATIVO, DISABILITATO)
- [x] `config.livello_accesso` — ENUM (TUTTO, LETTURA, BLOCCATO)
- [x] `config.aree_funzionali` — 10 aree funzionali con seed
- [x] `config.azioni_processo` — azioni con `permission_codename`
- [x] `config.profili_reparto_aree` — profilo aree per unità organizzativa
- [x] `config.profili_reparto_azioni` — profilo azioni per unità organizzativa
- [x] `config.user_override_aree` — override area per singolo utente
- [x] `config.user_override_oggetti` — override oggetto Django per singolo utente
- [x] `config.user_override_azioni` — override azione per singolo utente
- [x] `config.user_emittenti_fiscali` — scope emittenti per singolo utente
- [x] `config.unita_organizzative` — reparti con gerarchia `parent_id`
- [x] `anagrafiche.emittenti_fiscali` — emittenti con `soggetto_ruolo_id`
- [x] `script.fn_get_ruolo_sistema` — lookup ruolo
- [x] `script.fn_resolve_livello_area` — risoluzione livello area
- [x] `script.fn_check_azione_processo` — verifica azione
- [x] `script.fn_get_emittenti_scope_sr_ids` — scope emittenti
- [x] `PermissionResolver` + `ZeroERPPermission` — enforcement backend
- [x] `permissions_cache.py` — cache L1/L2 con `invalidate_user()`
- [x] `anagrafiche.fn_sync_auth_user_is_active` — sync `auth_user.is_active`
- [x] `GET /api/v1/core/users/{id}/permessi-effettivi/` — già esposto

---

## 1. Backend: Permission class e struttura area

### Backend

- [ ] 1.1 — Permission class `IsAdminZeroERP` in `apps/core/api/permissions.py`
  - Logica: legge `ruolo_sistema` dal bridge tramite `PermissionResolver.get_ruolo_sistema()`
  - Restituisce `True` solo se `ADMIN`; altrimenti `403`
  - Riutilizza la cache L1/L2 già esistente
  - Non passa dal sistema profili/override (check diretto)
  - **Prerequisiti**: nessuno (estende ciò che esiste)

- [ ] 1.2 — App Django `apps/amministrazione/` con struttura base
  - `apps/amministrazione/__init__.py`
  - `apps/amministrazione/apps.py`
  - `apps/amministrazione/api/__init__.py`
  - `apps/amministrazione/api/views.py` (vuoto, da popolare)
  - `apps/amministrazione/api/serializers.py` (vuoto, da popolare)
  - `apps/amministrazione/db/__init__.py`
  - `apps/amministrazione/db/amministrazione_repository.py`
  - Aggiungere a `INSTALLED_APPS` in `settings.py`
  - Aggiungere prefix `/api/v1/amministrazione/` a `urls.py`
  - **Prerequisiti**: 1.1

### Test

- [ ] 1.3 — Test unitari `IsAdminZeroERP`
  - Caso: ADMIN → 200 su view protetta
  - Caso: OPERATIVO → 403
  - Caso: DISABILITATO → 403
  - Caso: utente senza bridge → 403
  - File: `apps/core/tests/api/test_admin_permission.py`
  - **Prerequisiti**: 1.1

---

## 2. Backend: API Lista e Dettaglio Utenti

### DB

- [ ] 2.1 — Query SQL `fn_list_utenti` (inline nel repository, non funzione DB separata)
  - JOIN: `auth_user` + `risorse_umane_auth_user` + `risorse_umane` + `unita_organizzative`
  - Campi ritornati: `auth_user_id`, `username`, `email`, `first_name`, `last_name`,
    `ruolo_sistema`, `is_active`, `unita_organizzativa_id`, `unita_organizzativa_nome`,
    `risorsa_umana_id`, `attivo`, `valido_al`, `data_insert`
  - Filtri supportati: `ruolo_sistema`, `unita_organizzativa_id`, `is_active`, `search` (username/nome)
  - Ordinamento: `last_name`, `username`
  - **Prerequisiti**: nessuno (tabelle esistenti)

### Backend

- [ ] 2.2 — `GET /api/v1/amministrazione/utenti/`
  - Paginazione standard DRF (page/page_size)
  - Filtri query string: `ruolo_sistema`, `unita_organizzativa_id`, `is_active`, `search`
  - Permission: `IsAdminZeroERP`
  - **Prerequisiti**: DB 2.1, BE 1.2

- [ ] 2.3 — `GET /api/v1/amministrazione/utenti/{auth_user_id}/`
  - Dettaglio completo: dati auth_user + risorsa_umana + override permessi correnti
  - Include lista `user_override_aree`, `user_override_azioni`, `user_emittenti_fiscali`
  - Riusa l'output di `GET /api/v1/core/users/{id}/permessi-effettivi/` come sotto-sezione
  - **Prerequisiti**: 2.2

- [ ] 2.4 — `PATCH /api/v1/amministrazione/utenti/{auth_user_id}/`
  - Campi modificabili: `email`, `first_name`, `last_name`, `ruolo_sistema`,
    `unita_organizzativa_id`, `attivo` (risorsa_umana), `valido_al`
  - Modifiche a `ruolo_sistema` e `attivo` devono chiamare `fn_sync_auth_user_is_active`
    via repository (la funzione DB gestisce già la sync di `auth_user.is_active`)
  - Dopo modifica: invalida cache permessi con `permissions_cache.invalidate_user(auth_user_id)`
  - **Prerequisiti**: 2.3

- [ ] 2.5 — `POST /api/v1/amministrazione/utenti/{auth_user_id}/disabilita/`
  - Shortcut: imposta `ruolo_sistema = DISABILITATO` + `risorse_umane.attivo = false`
  - Chiama `fn_sync_auth_user_is_active` (sync `auth_user.is_active = false`)
  - Invalida token via blacklist SimpleJWT se configurato (`BLACKLIST_AFTER_ROTATION`)
  - Invalida cache permessi
  - **Prerequisiti**: 2.4

### Test

- [ ] 2.6 — Test lista utenti: filtri, paginazione, permission check (4 test)
- [ ] 2.7 — Test dettaglio: campi ritornati, utente non esistente (3 test)
- [ ] 2.8 — Test PATCH: modifica ruolo, sync is_active, invalidazione cache (5 test)
- [ ] 2.9 — Test disabilita: stato finale, blacklist token, cache (3 test)
- [ ] File: `apps/amministrazione/tests/api/test_utenti_views.py`
- **Prerequisiti**: 2.2–2.5

---

## 3. Backend: Orchestratore Creazione Utente

### Contesto

Creare un operatore richiede una catena di operazioni transazionali:

```
soggetti (PF)
  └── soggetti_ruoli (tipo RIS_UMANA)
        └── risorse_umane (operativa)
              ├── risorse_umane_auth_user (bridge + ruolo_sistema)
              └── auth_user (credenziali Django)
```

Tutto deve avvenire in un'unica transazione DB. Se uno step fallisce, rollback completo.

### DB

- [ ] 3.1 — Funzione `anagrafiche.fn_crea_operatore(...)` — orchestratore transazionale lato DB
  - Parametri:
    - `p_cognome text`, `p_nome text`, `p_codice_fiscale text` (opzionale)
    - `p_data_nascita date` (opzionale), `p_sesso char(1)` (opzionale)
    - `p_username text`, `p_email text`, `p_password_hash text`
    - `p_ruolo_sistema config.ruolo_sistema` (default `OPERATIVO`)
    - `p_unita_organizzativa_id integer`
    - `p_valido_dal date` (default TODAY), `p_valido_al date` (opzionale)
  - Step interni:
    1. Verifica unicità `username` e `email` in `auth_user`
    2. Verifica che non esista già un soggetto PF con stesso CF (se fornito)
    3. INSERT `auth_user` (con `is_active = true`, password Django hash)
    4. INSERT `anagrafiche.soggetti` (tipo PF)
    5. INSERT `anagrafiche.soggetti_ruoli` (tipo `RIS_UMANA`)
    6. INSERT `anagrafiche.risorse_umane`
    7. INSERT `anagrafiche.risorse_umane_auth_user` (trigger 1.4 già esistente
       chiama `fn_sync_auth_user_is_active` automaticamente)
  - Ritorno: `auth_user_id bigint`
  - Errori: via `script.fn_log_and_raise_error()` con codici dedicati
    - `E_ADMIN_USERNAME_DUPLICATO`
    - `E_ADMIN_EMAIL_DUPLICATA`
    - `E_ADMIN_CF_DUPLICATO`
    - `E_ADMIN_UO_NON_TROVATA`
  - **Prerequisiti**: nessuno (tutte le tabelle esistono)

### Backend

- [ ] 3.2 — `POST /api/v1/amministrazione/utenti/`
  - Serializer con validazione: username univoco, email valida, password strength
  - Chiama `fn_crea_operatore` via `cursor.execute()` in transaction
  - Password: ricevuta in chiaro dal frontend, hashata con `make_password()` prima di
    passarla alla funzione DB (mai in chiaro sul DB)
  - Risposta: `201 Created` con `auth_user_id` + dati completi utente creato
  - Permission: `IsAdminZeroERP`
  - **Prerequisiti**: DB 3.1, BE 1.2

- [ ] 3.3 — Test per orchestratore creazione
  - Mock DB: verifica che la funzione SQL venga chiamata con parametri corretti
  - Caso: creazione completa → 201 con tutti i campi
  - Caso: username duplicato → 400 con codice errore
  - Caso: email duplicata → 400
  - Caso: CF duplicato → 400
  - Caso: UO non trovata → 400
  - Caso: errore DB generico → 500 con rollback
  - 6 test — File: `apps/amministrazione/tests/api/test_crea_utente.py`
  - **Prerequisiti**: 3.2

### Test DB

- [ ] 3.4 — Test pgTAP per `fn_crea_operatore`
  - Caso: creazione completa → tutti i record esistono nelle 5 tabelle
  - Caso: username duplicato → RAISE con codice corretto
  - Caso: email duplicata → RAISE
  - Caso: CF duplicato → RAISE
  - Caso: rollback su errore → nessun record parziale
  - 5 test — **Prerequisiti**: DB 3.1

---

## 4. Backend: API Override Permessi Utente

### Contesto

Le 4 tabelle override esistono ma non hanno API di scrittura. L'endpoint
`GET /api/v1/core/users/{id}/permessi-effettivi/` mostra il risultato risolto
ma non permette modifica. Queste API colmano il gap.

### Backend

- [ ] 4.1 — `GET/PUT /api/v1/amministrazione/utenti/{id}/override-aree/`
  - GET: lista override aree attivi per l'utente (include `valido_dal`, `valido_al`)
  - PUT: sostituisce la lista completa degli override aree (replace semantics)
  - Ogni item: `area_id`, `livello` (TUTTO/LETTURA/BLOCCATO), `valido_dal`, `valido_al`
  - Dopo scrittura: `invalidate_user(auth_user_id)`
  - **Prerequisiti**: BE 1.2

- [ ] 4.2 — `GET/PUT /api/v1/amministrazione/utenti/{id}/override-azioni/`
  - Come 4.1 ma per `config.user_override_azioni`
  - Ogni item: `azione_id`, `abilitata` (boolean), `valido_dal`, `valido_al`
  - **Prerequisiti**: BE 1.2

- [ ] 4.3 — `GET/PUT /api/v1/amministrazione/utenti/{id}/emittenti-scope/`
  - GET: lista emittenti autorizzati per l'utente
  - PUT: sostituisce la lista (lista vuota = nessuna restrizione per ADMIN/OPERATIVO senza whitelist)
  - Ogni item: `emittente_fiscale_id`
  - **Prerequisiti**: BE 1.2

- [ ] 4.4 — Test override aree: GET, PUT, invalidazione cache (4 test per API)
- [ ] 4.5 — Test override azioni: GET, PUT (3 test)
- [ ] 4.6 — Test scope emittenti: GET, PUT, lista vuota (3 test)
- [ ] File: `apps/amministrazione/tests/api/test_override_permessi.py`
- **Prerequisiti**: 4.1–4.3

---

## 5. Backend: API Profili Reparto

### Backend

- [ ] 5.1 — `GET /api/v1/amministrazione/reparti/`
  - Lista `config.unita_organizzative` con flag `ha_profilo_configurato`
    (true se esiste almeno una riga in `profili_reparto_aree`)
  - Include conteggio operatori nel reparto
  - **Prerequisiti**: BE 1.2

- [ ] 5.2 — `GET /api/v1/amministrazione/reparti/{uo_id}/profilo/`
  - Ritorna struttura completa del profilo:
    - Lista tutte le `aree_funzionali` (10) con `livello` configurato o `BLOCCATO` default
    - Lista tutte le `azioni_processo` con `abilitata` configurato o `false` default
  - **Prerequisiti**: 5.1

- [ ] 5.3 — `PUT /api/v1/amministrazione/reparti/{uo_id}/profilo/`
  - Riceve struttura completa (aree + azioni)
  - Replace semantics: elimina profilo esistente e riscrive
  - Dopo scrittura: `invalidate_department(uo_id)` per invalidare cache
    di tutti gli utenti del reparto
  - **Prerequisiti**: 5.2

- [ ] 5.4 — Test lista reparti: flag ha_profilo, conteggio operatori (3 test)
- [ ] 5.5 — Test GET profilo: aree complete, default BLOCCATO (3 test)
- [ ] 5.6 — Test PUT profilo: replace, invalidazione cache reparto (4 test)
- [ ] File: `apps/amministrazione/tests/api/test_profili_reparto.py`
- **Prerequisiti**: 5.1–5.3

---

## 6. Frontend: Area Amministrazione

### Contesto

L'area Amministrazione è una nuova voce nella sidebar, visibile **solo** agli utenti
con `ruolo_sistema = ADMIN`. Il frontend legge il ruolo dal JWT o da un endpoint
`/api/v1/core/me/` (da verificare se già esiste o da aggiungere come prerequisito).

### Struttura frontend

```
src/
  views/
    amministrazione/
      UtentiListView.vue          ← pagina lista operatori
      RepartiProfiloView.vue      ← pagina configurazione profili reparto
  components/
    amministrazione/
      UtenteDrawer.vue            ← drawer creazione/modifica (drawer pattern standard)
      UtentePermessiTab.vue       ← tab permessi effettivi + override
      RepartoProfiloEditor.vue    ← editor profilo reparto (aree + azioni)
  stores/
    amministrazione/
      utenti.js                   ← Pinia store per lista/dettaglio utenti
      reparti.js                  ← Pinia store per profili reparto
  api/
    amministrazione.js            ← axios calls verso /api/v1/amministrazione/
```

### 6.1 Prerequisiti frontend

- [ ] 6.1 — Endpoint `GET /api/v1/core/me/`
  - Risposta: `auth_user_id`, `username`, `ruolo_sistema`, `unita_organizzativa_id`
  - Usato dal frontend al boot per determinare la visibilità dell'area Amministrazione
  - Aggiunto all'app `core` (non `amministrazione`)
  - **Prerequisiti**: nessuno

- [ ] 6.2 — Guard sidebar: mostra voce "Amministrazione" solo se `ruolo_sistema === 'ADMIN'`
  - Usare composable `useCurrentUser()` già nel progetto (o creare se mancante)
  - Nessuna route guard server-side necessaria (le API già bloccano con 403)
  - **Prerequisiti**: 6.1

### 6.2 Lista Utenti

- [ ] 6.3 — `UtentiListView.vue` — pagina principale
  - DataTable PrimeVue con colonne: nome/cognome, username, reparto, ruolo_sistema, stato (badge)
  - Filtri toolbar: search (text), reparto (dropdown), ruolo_sistema (dropdown), attivo (toggle)
  - Pulsante "+ Nuovo operatore" → apre `UtenteDrawer.vue` in modalità creazione
  - Click su riga → apre `UtenteDrawer.vue` in modalità modifica
  - **Prerequisiti**: BE 2.2, FE 6.2

- [ ] 6.4 — `UtenteDrawer.vue` — drawer universale creazione/modifica
  - **Modalità CREA**: form completo con tutti i campi di `fn_crea_operatore`
    - Sezione "Persona": nome, cognome, codice fiscale (opzionale), data nascita, sesso
    - Sezione "Accesso": username, email, password (con conferma), ruolo_sistema
    - Sezione "Collocazione": unità organizzativa (treeselect/dropdown gerarchico),
      valido_dal, valido_al
  - **Modalità MODIFICA**: stessi campi ma no password (sezione cambio password separata)
  - Pulsante "Disabilita operatore" (rosso, solo in modalità modifica) → conferma dialog
  - Tabs in modalità modifica: "Dati" | "Permessi" | "Sessioni recenti"
  - **Prerequisiti**: BE 3.2 (crea), BE 2.4 (modifica)

- [ ] 6.5 — `UtentePermessiTab.vue` — tab permessi nel drawer modifica
  - Sezione "Permessi effettivi" (read-only): tabella aree + livello risolto
    (verde TUTTO, giallo LETTURA, rosso BLOCCATO) — chiama permessi-effettivi esistente
  - Sezione "Override aree": lista override attivi con edit inline
  - Sezione "Override azioni": toggle per ogni azione di processo
  - Sezione "Emittenti autorizzati": multiselect (visibile solo se OPERATIVO)
  - Nota informativa se l'utente è ADMIN: "Gli amministratori hanno accesso totale
    — gli override non vengono applicati"
  - **Prerequisiti**: BE 4.1–4.3

### 6.3 Configurazione Profili Reparto

- [ ] 6.6 — `RepartiProfiloView.vue` — pagina lista reparti
  - Tabella reparti con colonna "Profilo configurato" (check verde / warning giallo)
  - Click su riga → apre `RepartoProfiloEditor.vue` come drawer o navigazione interna
  - **Prerequisiti**: BE 5.1

- [ ] 6.7 — `RepartoProfiloEditor.vue` — editor profilo
  - Due sezioni in accordion/tab: "Aree funzionali" | "Azioni di processo"
  - **Aree funzionali**: griglia con tutte le 10 aree, per ognuna un SelectButton
    con opzioni TUTTO / LETTURA / BLOCCATO (colori coerenti con tab permessi)
  - **Azioni processo**: lista azioni con toggle on/off per abilitazione
  - Pulsante "Salva profilo" con conferma (le modifiche impattano tutti gli utenti del reparto)
  - Nota informativa: "Le modifiche si applicano a tutti gli operatori del reparto
    senza override individuali"
  - **Prerequisiti**: BE 5.2, BE 5.3

---

## 7. Navigazione sidebar e routing

### Backend

- [ ] 7.1 — Route Vue: `/amministrazione/utenti` → `UtentiListView`
- [ ] 7.2 — Route Vue: `/amministrazione/reparti` → `RepartiProfiloView`
- [ ] 7.3 — Voce sidebar "Amministrazione" con icona `UsersRound` (o equivalente PrimeVue)
  - Sotto-voci: "Operatori" e "Profili Reparto"
  - Visibile solo se `ruolo_sistema === 'ADMIN'` (letto da store `useCurrentUser`)
  - **Prerequisiti**: FE 6.2

---

## Tabella riassuntiva

| #       | Area      | Tipo | Descrizione                                           | Prerequisiti | Stato |
| ------- | --------- | ---- | ----------------------------------------------------- | ------------ | ----- |
| 1.1     | Infra     | BE   | `IsAdminZeroERP` permission class                     | —            | TODO  |
| 1.2     | Infra     | BE   | App `apps/amministrazione/` struttura base            | 1.1          | TODO  |
| 1.3     | Infra     | Test | Test `IsAdminZeroERP` (4 test)                        | 1.1          | TODO  |
| 2.1     | Utenti    | DB   | Query lista utenti (repository)                       | —            | TODO  |
| 2.2     | Utenti    | BE   | `GET /amministrazione/utenti/`                        | 2.1, 1.2     | TODO  |
| 2.3     | Utenti    | BE   | `GET /amministrazione/utenti/{id}/`                   | 2.2          | TODO  |
| 2.4     | Utenti    | BE   | `PATCH /amministrazione/utenti/{id}/`                 | 2.3          | TODO  |
| 2.5     | Utenti    | BE   | `POST .../disabilita/`                                | 2.4          | TODO  |
| 2.6–2.9 | Utenti    | Test | Test lista, dettaglio, modifica, disabilita (15 test) | 2.2–2.5      | TODO  |
| 3.1     | Creazione | DB   | `anagrafiche.fn_crea_operatore`                       | —            | TODO  |
| 3.2     | Creazione | BE   | `POST /amministrazione/utenti/`                       | 3.1, 1.2     | TODO  |
| 3.3     | Creazione | Test | Test orchestratore BE (6 test)                        | 3.2          | TODO  |
| 3.4     | Creazione | Test | Test pgTAP `fn_crea_operatore` (5 test)               | 3.1          | TODO  |
| 4.1     | Override  | BE   | API override aree (GET/PUT)                           | 1.2          | TODO  |
| 4.2     | Override  | BE   | API override azioni (GET/PUT)                         | 1.2          | TODO  |
| 4.3     | Override  | BE   | API scope emittenti (GET/PUT)                         | 1.2          | TODO  |
| 4.4–4.6 | Override  | Test | Test override (10 test)                               | 4.1–4.3      | TODO  |
| 5.1     | Reparti   | BE   | `GET /amministrazione/reparti/`                       | 1.2          | TODO  |
| 5.2     | Reparti   | BE   | `GET .../reparti/{id}/profilo/`                       | 5.1          | TODO  |
| 5.3     | Reparti   | BE   | `PUT .../reparti/{id}/profilo/`                       | 5.2          | TODO  |
| 5.4–5.6 | Reparti   | Test | Test profili reparto (10 test)                        | 5.1–5.3      | TODO  |
| 6.1     | Frontend  | BE   | `GET /core/me/`                                       | —            | TODO  |
| 6.2     | Frontend  | FE   | Guard sidebar ADMIN                                   | 6.1          | TODO  |
| 6.3     | Frontend  | FE   | `UtentiListView.vue`                                  | 2.2, 6.2     | TODO  |
| 6.4     | Frontend  | FE   | `UtenteDrawer.vue` (crea + modifica)                  | 3.2, 2.4     | TODO  |
| 6.5     | Frontend  | FE   | `UtentePermessiTab.vue`                               | 4.1–4.3      | TODO  |
| 6.6     | Frontend  | FE   | `RepartiProfiloView.vue`                              | 5.1          | TODO  |
| 6.7     | Frontend  | FE   | `RepartoProfiloEditor.vue`                            | 5.2, 5.3     | TODO  |
| 7.1–7.3 | Routing   | FE   | Routes + sidebar voce Amministrazione                 | 6.2          | TODO  |

---

## Ordine di sviluppo raccomandato

```
SPRINT 1 — Fondamenta backend
  DB:  3.1 fn_crea_operatore (Liquibase changeset)
  BE:  1.1 IsAdminZeroERP
  BE:  1.2 struttura app amministrazione
  BE:  2.1 query lista utenti
  BE:  2.2–2.5 CRUD utenti
  BE:  3.2 POST crea utente
  Test: 1.3, 2.6–2.9, 3.3, 3.4

SPRINT 2 — Override e profili backend
  BE:  4.1–4.3 override permessi
  BE:  5.1–5.3 profili reparto
  BE:  6.1 GET /core/me/
  Test: 4.4–4.6, 5.4–5.6

SPRINT 3 — Frontend lista e creazione utenti
  FE:  6.2 guard sidebar
  FE:  6.3 UtentiListView
  FE:  6.4 UtenteDrawer (modalità crea)
  FE:  routing 7.1–7.3

SPRINT 4 — Frontend permessi e profili reparto
  FE:  6.4 UtenteDrawer (modalità modifica)
  FE:  6.5 UtentePermessiTab
  FE:  6.6–6.7 Reparti + RepartoProfiloEditor
```

---

## Decisioni di progetto

| #   | Decisione                           | Scelta                                                          | Motivazione                                                                   |
| --- | ----------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| D1  | Collocazione sidebar                | Area dedicata "Amministrazione" (solo ADMIN)                    | Separazione netta da config di dominio; visibilità controllata da ruolo       |
| D2  | Creazione utente                    | Form unico via `fn_crea_operatore` (transazionale)              | Garantisce coerenza; no stato intermedio su DB                                |
| D3  | Check ADMIN                         | `IsAdminZeroERP` diretto (non via profili reparto)              | Evita ricorsività; l'admin non può "lockoutarsi" per errore di configurazione |
| D4  | Override semantics                  | Replace completo (PUT)                                          | Più semplice da gestire nel frontend; evita PATCH parziali complessi          |
| D5  | Password al momento della creazione | Hashata lato Django con `make_password()`, mai in chiaro sul DB | Sicurezza; la funzione DB riceve solo l'hash                                  |
| D6  | Cambio password                     | Fuori dallo scope di questo WIP (endpoint dedicato separato)    | Complessità ridotta; gestibile come evolution                                 |

---

## Note

- Il modulo non gestisce `config.user_override_oggetti` nella prima versione (override a livello
  model Django). È un caso d'uso avanzato e raro; rimandato a evoluzione futura.
- Le sessioni recenti nel drawer utente (tab "Sessioni recenti") attingono a
  `dbops.sessioni_utente` già implementato — semplice query con filtro `auth_user_id`.
- La gestione degli emittenti fiscali autorizzati nel form di creazione è opzionale:
  se non compilata, l'utente non ha restrizioni (whitelist vuota = nessun filtro per OPERATIVO).
- `unita_organizzative` ha struttura gerarchica (`parent_id`) — il componente dropdown
  nel form deve gestire l'indentazione o usare TreeSelect di PrimeVue.
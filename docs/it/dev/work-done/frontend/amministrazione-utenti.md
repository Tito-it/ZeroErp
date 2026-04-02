# Amministrazione Utenti — WIP

> Documento di lavoro per pianificazione e avanzamento del modulo Amministrazione.
>
> **Stato**: Sprint 2 completato (2026-03-12). Evoluzione in corso (sezione 8 — SoggettoResolver).
>
> Evoluzione: l'architettura building block e' documentata in
> [Architettura Building Block](../../work-done/frontend/componenti-riutilizzabili.md) (documento master, completato)
> e [Building Block Repository](../../work-done/backend/building-block-repository.md) (backend, completato).
>
> Dipende da: `docs/it/dev/work-in-progress/permessi-e-autorizzazioni.md` (completato)
> Dipende da: `docs/it/dev/work-done/sviluppi-risorse-umane.md` (completato)
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

- [x] 1.1 — Permission class `IsAdminZeroERP` in `apps/core/api/permissions.py`
  - Logica: legge `ruolo_sistema` dal bridge tramite `PermissionResolver.get_ruolo_sistema()`
  - Restituisce `True` solo se `ADMIN`; altrimenti `403`
  - Riutilizza la cache L1/L2 già esistente
  - Non passa dal sistema profili/override (check diretto)
  - **Prerequisiti**: nessuno (estende ciò che esiste)

- [x] 1.2 — App Django `apps/amm_software/` con struttura base
  - Implementata come `apps/amm_software/` (non `apps/amministrazione/`)
  - Registrata in `INSTALLED_APPS`, prefix `/api/v1/amm-software/`
  - Contiene: `api/views.py`, `api/urls_v1.py`, `api/serializers.py`,
    `services/amm_software_service.py`, `db/amm_software_repository.py`
  - **Prerequisiti**: 1.1

### Test

- [x] 1.3 — Test unitari `IsAdminZeroERP`
  - Caso: ADMIN → 200 su view protetta
  - Caso: OPERATIVO → 403
  - Caso: DISABILITATO → 403
  - Caso: utente senza bridge → 403
  - File: `apps/core/tests/api/test_admin_permission.py`
  - **Prerequisiti**: 1.1

---

## 2. Backend: API Lista e Dettaglio Utenti

### DB

- [x] 2.1 — Query SQL lista utenti (inline nel repository `amm_software_repository.py`)
  - JOIN: `auth_user` + `risorse_umane_auth_user` + `risorse_umane` + `unita_organizzative`
  - Campi ritornati: `auth_user_id`, `username`, `email`, `first_name`, `last_name`,
    `ruolo_sistema`, `is_active`, `unita_organizzativa_id`, `unita_organizzativa_nome`,
    `risorsa_umana_id`, `attivo`, `valido_al`, `data_insert`
  - Filtri supportati: `ruolo_sistema`, `unita_organizzativa_id`, `is_active`, `search` (username/nome)
  - Ordinamento: `last_name`, `username`
  - **Prerequisiti**: nessuno (tabelle esistenti)

### Backend

- [x] 2.2 — `GET /api/v1/amm-software/operatori/`
  - Paginazione standard DRF (page/page_size)
  - Filtri query string: `ruolo_sistema`, `unita_organizzativa_id`, `is_active`, `search`
  - Permission: `IsAdminZeroERP`
  - **Prerequisiti**: DB 2.1, BE 1.2

- [x] 2.3 — `GET /api/v1/amm-software/operatori/{auth_user_id}/`
  - Dettaglio completo: dati auth_user + risorsa_umana + override permessi correnti
  - Include lista `user_override_aree`, `user_override_azioni`, `user_emittenti_fiscali`
  - Riusa l'output di `GET /api/v1/core/users/{id}/permessi-effettivi/` come sotto-sezione
  - **Prerequisiti**: 2.2

- [x] 2.4 — `PATCH /api/v1/amm-software/operatori/{auth_user_id}/`
  - Campi modificabili: `email`, `first_name`, `last_name`, `ruolo_sistema`,
    `unita_organizzativa_id`, `attivo` (risorsa_umana), `valido_al`
  - Modifiche a `ruolo_sistema` e `attivo` devono chiamare `fn_sync_auth_user_is_active`
    via repository (la funzione DB gestisce già la sync di `auth_user.is_active`)
  - Dopo modifica: invalida cache permessi con `permissions_cache.invalidate_user(auth_user_id)`
  - **Prerequisiti**: 2.3

- [x] 2.5 — `POST /api/v1/amm-software/operatori/{auth_user_id}/disabilita/`
  - Shortcut: imposta `ruolo_sistema = DISABILITATO` + `risorse_umane.attivo = false`
  - Chiama `fn_sync_auth_user_is_active` (sync `auth_user.is_active = false`)
  - Invalida token via blacklist SimpleJWT se configurato (`BLACKLIST_AFTER_ROTATION`)
  - Invalida cache permessi
  - **Prerequisiti**: 2.4

### Test

- [x] 2.6 — Test lista utenti: filtri, paginazione, permission check (4 test)
- [x] 2.7 — Test dettaglio: campi ritornati, utente non esistente (3 test)
- [x] 2.8 — Test PATCH: modifica ruolo, sync is_active, invalidazione cache (5 test)
- [x] 2.9 — Test disabilita: stato finale, blacklist token, cache (3 test)
- [x] File: `apps/amm_software/tests/api/test_utenti_views.py` (15 test)
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

- [x] 3.1 — Funzione `anagrafiche.fn_crea_operatore(...)` — orchestratore transazionale lato DB
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

- [x] 3.2 — `POST /api/v1/amm-software/operatori/`
  - Serializer con validazione: username univoco, email valida, password strength
  - Chiama `fn_crea_operatore` via `cursor.execute()` in transaction
  - Password: ricevuta in chiaro dal frontend, hashata con `make_password()` prima di
    passarla alla funzione DB (mai in chiaro sul DB)
  - Risposta: `201 Created` con `auth_user_id` + dati completi utente creato
  - Permission: `IsAdminZeroERP`
  - **Prerequisiti**: DB 3.1, BE 1.2

- [x] 3.3 — Test per orchestratore creazione
  - Mock DB: verifica che la funzione SQL venga chiamata con parametri corretti
  - Caso: creazione completa → 201 con tutti i campi
  - Caso: username duplicato → 400 con codice errore
  - Caso: email duplicata → 400
  - Caso: CF duplicato → 400
  - Caso: UO non trovata → 400
  - Caso: errore DB generico → 500 con rollback
  - 7 test — File: `apps/amm_software/tests/api/test_crea_utente.py`
  - **Prerequisiti**: 3.2

### Test DB

- [x] 3.4 — Test pgTAP per `fn_crea_operatore`
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

- [x] 4.1 — `GET/PUT /api/v1/amm-software/operatori/{id}/override-aree/`
  - GET: lista override aree attivi per l'utente (include `valido_dal`, `valido_al`)
  - PUT: sostituisce la lista completa degli override aree (replace semantics)
  - Ogni item: `area_id`, `livello` (TUTTO/LETTURA/BLOCCATO), `valido_dal`, `valido_al`
  - Dopo scrittura: `invalidate_user(auth_user_id)`
  - **Prerequisiti**: BE 1.2

- [x] 4.2 — `GET/PUT /api/v1/amm-software/operatori/{id}/override-azioni/`
  - Come 4.1 ma per `config.user_override_azioni`
  - Ogni item: `azione_id`, `abilitata` (boolean), `valido_dal`, `valido_al`
  - **Prerequisiti**: BE 1.2

- [x] 4.3 — `GET/PUT /api/v1/amm-software/operatori/{id}/emittenti-scope/`
  - GET: lista emittenti autorizzati per l'utente
  - PUT: sostituisce la lista (lista vuota = nessuna restrizione per ADMIN/OPERATIVO senza whitelist)
  - Ogni item: `emittente_fiscale_id`
  - **Prerequisiti**: BE 1.2

- [x] 4.4 — Test override aree: GET, PUT, invalidazione cache (4 test per API)
- [x] 4.5 — Test override azioni: GET, PUT (3 test)
- [x] 4.6 — Test scope emittenti: GET, PUT, lista vuota (3 test)
- [x] File: `apps/amm_software/tests/api/test_override_permessi.py` (10 test)
- **Prerequisiti**: 4.1–4.3

---

## 5. Backend: API Profili Reparto

### Backend

- [x] 5.1 — `GET /api/v1/amm-software/reparti/`
  - Lista `config.unita_organizzative` con flag `ha_profilo_configurato`
    (true se esiste almeno una riga in `profili_reparto_aree`)
  - Include conteggio operatori nel reparto
  - **Prerequisiti**: BE 1.2

- [x] 5.2 — `GET /api/v1/amm-software/reparti/{uo_id}/profilo/`
  - Ritorna struttura completa del profilo:
    - Lista tutte le `aree_funzionali` (10) con `livello` configurato o `BLOCCATO` default
    - Lista tutte le `azioni_processo` con `abilitata` configurato o `false` default
  - **Prerequisiti**: 5.1

- [x] 5.3 — `PUT /api/v1/amm-software/reparti/{uo_id}/profilo/`
  - Riceve struttura completa (aree + azioni)
  - Replace semantics: elimina profilo esistente e riscrive
  - Dopo scrittura: `invalidate_department(uo_id)` per invalidare cache
    di tutti gli utenti del reparto
  - **Prerequisiti**: 5.2

- [x] 5.4 — Test lista reparti: flag ha_profilo, conteggio operatori (3 test)
- [x] 5.5 — Test GET profilo: aree complete, default BLOCCATO (3 test)
- [x] 5.6 — Test PUT profilo: replace, invalidazione cache reparto (4 test)
- [x] File: `apps/amm_software/tests/api/test_profili_reparto.py` (10 test)
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
      OperatoriListView.vue          ← pagina lista operatori
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

- [x] 6.1 — Endpoint `GET /api/v1/core/me/`
  - Implementato in `apps/core/api/me_view.py` (`UserProfileView`)
  - Chiama `script.fn_get_user_profile(auth_user_id)` — ritorna JSONB completo
  - Include: utente, ruolo_sistema, risorse_umane, soggetto, emittente, permessi_area
  - Guard DB aggiunti (2026-03-18): `E_UTENTE_DISABILITATO`, `E_UTENTE_NON_ATTIVO`, `E_UTENTE_SCADUTO`

- [x] 6.2 — Guard sidebar: mostra voce "Amm. Software" solo se `ruolo_sistema === 'ADMIN'`
  - Implementato in `auth.js`: `isAdmin` computed + `visibleDomains` filtra `adminOnly`
  - `navigation.js`: dominio `amm-software` con flag `adminOnly: true`
  - Router guard in `router/index.js`: redirect a `/forbidden` se non admin
  - Badge admin nella topbar (`AppTopbar.vue`) — chip arancione visibile solo per ADMIN

### 6.2 Lista Utenti

- [x] 6.3 — `OperatoriListView.vue` — pagina principale
  - DataTable PrimeVue con colonne: nome/cognome, username, reparto, ruolo_sistema, stato (badge)
  - Filtri toolbar: search (text), reparto (dropdown), ruolo_sistema (dropdown), attivo (toggle)
  - Pulsante "+ Nuovo operatore" → apre `UtenteDrawer.vue` in modalità creazione
  - Click su riga → apre `UtenteDrawer.vue` in modalità modifica
  - **Prerequisiti**: BE 2.2, FE 6.2

- [x] 6.4 — `UtenteDrawer.vue` — drawer universale creazione/modifica (V1)
  - V1 implementata con form inline per dati persona (senza SoggettoResolver)
  - **Modalità CREA**: form completo con tutti i campi di `fn_crea_operatore`
  - **Modalità MODIFICA**: stessi campi, tabs "Dati" | "Permessi" | "Sessioni recenti"
  - **Evoluzione prevista (V2)**: integrazione SoggettoResolver — vedi sezione 8
  - **Prerequisiti**: BE 3.2 (crea), BE 2.4 (modifica)

- [x] 6.5 — `UtentePermessiTab.vue` — tab permessi nel drawer modifica
  - Sezione "Permessi effettivi" (read-only): tabella aree + livello risolto
    (verde TUTTO, giallo LETTURA, rosso BLOCCATO) — chiama permessi-effettivi esistente
  - Sezione "Override aree": lista override attivi con edit inline
  - Sezione "Override azioni": toggle per ogni azione di processo
  - Sezione "Emittenti autorizzati": multiselect (visibile solo se OPERATIVO)
  - Nota informativa se l'utente è ADMIN: "Gli amministratori hanno accesso totale
    — gli override non vengono applicati"
  - **Prerequisiti**: BE 4.1–4.3

### 6.3 Configurazione Profili Reparto

- [x] 6.6 — `RepartiProfiloView.vue` — pagina lista reparti
  - Tabella reparti con colonna "Profilo configurato" (check verde / warning giallo)
  - Click su riga → apre `RepartoProfiloEditor.vue` come drawer o navigazione interna
  - **Prerequisiti**: BE 5.1

- [x] 6.7 — `RepartoProfiloEditor.vue` — editor profilo
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

- [x] 7.1 — Route Vue: `/amm-software/operatori` → `OperatoriListView`
- [x] 7.2 — Route Vue: `/amm-software/profili-reparto` → `RepartiProfiloView`
- [x] 7.3 — Voce sidebar "Amm. Software" con icona `pi pi-lock`
  - 4 sotto-voci: Operatori, Profili Reparto, Permessi (placeholder), Audit Log (placeholder)
  - Visibile solo se `isAdmin` — filtrata da `visibleDomains` in `auth.js`

---

## Tabella riassuntiva

| #       | Area      | Tipo | Descrizione                                           | Prerequisiti | Stato |
| ------- | --------- | ---- | ----------------------------------------------------- | ------------ | ----- |
| 1.1     | Infra     | BE   | `IsAdminZeroERP` permission class                     | —            | DONE  |
| 1.2     | Infra     | BE   | App `apps/amm_software/` struttura base               | 1.1          | DONE  |
| 1.3     | Infra     | Test | Test `IsAdminZeroERP` (6 test)                        | 1.1          | DONE  |
| 2.1     | Utenti    | DB   | Query lista utenti (repository)                       | —            | DONE  |
| 2.2     | Utenti    | BE   | `GET /amm-software/operatori/`                           | 2.1, 1.2     | DONE  |
| 2.3     | Utenti    | BE   | `GET /amm-software/operatori/{id}/`                      | 2.2          | DONE  |
| 2.4     | Utenti    | BE   | `PATCH /amm-software/operatori/{id}/`                    | 2.3          | DONE  |
| 2.5     | Utenti    | BE   | `POST .../disabilita/`                                | 2.4          | DONE  |
| 2.6–2.9 | Utenti    | Test | Test lista, dettaglio, modifica, disabilita (15 test) | 2.2–2.5      | DONE  |
| 3.1     | Creazione | DB   | `anagrafiche.fn_crea_operatore`                       | —            | DONE  |
| 3.2     | Creazione | BE   | `POST /amm-software/operatori/`                          | 3.1, 1.2     | DONE  |
| 3.3     | Creazione | Test | Test orchestratore BE (7 test)                        | 3.2          | DONE  |
| 3.4     | Creazione | Test | Test pgTAP `fn_crea_operatore` (5 test)               | 3.1          | DONE  |
| 4.1     | Override  | BE   | API override aree (GET/PUT)                           | 1.2          | DONE  |
| 4.2     | Override  | BE   | API override azioni (GET/PUT)                         | 1.2          | DONE  |
| 4.3     | Override  | BE   | API scope emittenti (GET/PUT)                         | 1.2          | DONE  |
| 4.4–4.6 | Override  | Test | Test override (10 test)                               | 4.1–4.3      | DONE  |
| 5.1     | Reparti   | BE   | `GET /amm-software/reparti/`                          | 1.2          | DONE  |
| 5.2     | Reparti   | BE   | `GET .../reparti/{id}/profilo/`                       | 5.1          | DONE  |
| 5.3     | Reparti   | BE   | `PUT .../reparti/{id}/profilo/`                       | 5.2          | DONE  |
| 5.4–5.6 | Reparti   | Test | Test profili reparto (10 test)                        | 5.1–5.3      | DONE  |
| 6.1     | Frontend  | BE   | `GET /core/me/` + guard DB utente                     | —            | DONE  |
| 6.2     | Frontend  | FE   | Guard sidebar ADMIN + badge topbar                    | 6.1          | DONE  |
| 6.3     | Frontend  | FE   | `OperatoriListView.vue`                                  | 2.2, 6.2     | DONE  |
| 6.4     | Frontend  | FE   | `UtenteDrawer.vue` V1 (crea + modifica)               | 3.2, 2.4     | DONE  |
| 6.5     | Frontend  | FE   | `UtentePermessiTab.vue`                               | 4.1–4.3      | DONE  |
| 6.6     | Frontend  | FE   | `RepartiProfiloView.vue`                              | 5.1          | DONE  |
| 6.7     | Frontend  | FE   | `RepartoProfiloEditor.vue`                            | 5.2, 5.3     | DONE  |
| 7.1–7.3 | Routing   | FE   | Routes + sidebar + 2 placeholder                      | 6.2          | DONE  |
| **8.1** | Resolver  | DB   | Endpoint config-resolver per tipo ruolo               | —            | TODO  |
| **8.2** | Resolver  | DB   | Evoluzione `fn_crea_operatore` (soggetto esistente)   | 8.1          | TODO  |
| **8.3** | Resolver  | BE   | `GET /anagrafiche/ruoli/{tipo_ruolo}/config-resolver/` | 8.1         | TODO  |
| **8.4** | Resolver  | BE   | Evoluzione `POST /amm-software/operatori/` (due flussi)  | 8.2, 8.3    | TODO  |
| **8.5** | Resolver  | FE   | Componente `SoggettoResolver.vue` (sotto-drawer)      | 8.3          | TODO  |
| **8.6** | Resolver  | FE   | `UtenteDrawer.vue` V2 (integra SoggettoResolver)      | 8.4, 8.5    | TODO  |
| **8.7** | Resolver  | Test | Test config-resolver + evoluzione creazione            | 8.3, 8.4    | TODO  |

---

## Ordine di sviluppo — storico e prossimi

```
SPRINT 1 — Fondamenta backend                                        COMPLETATO (2026-03-12)
  1.1–1.3, 2.1–2.9, 3.1–3.4

SPRINT 2 — Override, profili, frontend completo                       COMPLETATO (2026-03-12)
  4.1–4.6, 5.1–5.6, 6.1–6.7, 7.1–7.3

SPRINT 3 (sessione 2026-03-18) — Hardening login e UX admin          COMPLETATO
  - Guard DB su fn_get_user_profile (E_UTENTE_DISABILITATO/NON_ATTIVO/SCADUTO)
  - Propagazione codici errore DB → frontend (ErrorTranslator regex E_*)
  - Messaggi login specifici per stato utente (LoginView.vue)
  - Pulizia token su errore profilo (auth.js)
  - Badge admin nella topbar (AppTopbar.vue)

SPRINT 4 — SoggettoResolver (building block universale)              DA FARE
  DB:   8.1 config-resolver + 8.2 evoluzione fn_crea_operatore
  BE:   8.3 endpoint config-resolver + 8.4 evoluzione POST utenti
  FE:   8.5 SoggettoResolver.vue + 8.6 UtenteDrawer V2
  Test: 8.7
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

---

## 8. SoggettoResolver — Building Block Universale "Cerca o Crea Soggetto"

> Aggiunto: 2026-03-18
> Stato: **analisi completata, sviluppo da avviare**

### Contesto

La V1 di `UtenteDrawer` crea sempre un soggetto nuovo inline. Ma nella realta'
un operatore potrebbe gia' esistere in anagrafica come fornitore, cliente, o altro ruolo.
Serve un pattern universale per **cercare un soggetto esistente o crearne uno nuovo**
prima di assegnare un ruolo.

Questo pattern si ripete identico per ogni ruolo futuro:

| Contesto            | Ruolo assegnato | Tipi ammessi |
| ------------------- | --------------- | ------------ |
| Creazione operatore | RIS_UMANA       | PF           |
| Creazione cliente   | CL              | PF, PG, ENC  |
| Creazione fornitore | FO              | PF, PG, ENC  |
| Creazione referente | RE              | PF, PG       |
| Creazione gestore   | GE              | PG           |

### Principio: tutto data-driven dal DB

Il frontend **non deve hardcodare** i tipi ammessi o i requisiti CF/PIVA.
La configurazione esiste gia' nel DB:

1. `config.tipi_ruoli_nature_ammesse` — quali nature (PF/PG/ENC) sono ammesse per ogni ruolo
2. `config.tipi_soggetto_dettaglio` — per ogni tipo dettaglio, `cf_obbligatorio` e `piva_obbligatoria`

La catena e':

```text
tipo_ruolo → nature ammesse → tipi_soggetto_dettaglio → cf/piva obbligatori
```

Un singolo endpoint backend aggrega tutto e il frontend si adatta automaticamente.

### Flusso UX

```text
1. Amministratore apre drawer "Nuovo Operatore"
2. Clicca "Cerca o crea soggetto"
3. Si apre SoggettoResolver (sotto-drawer dedicato)
   ├── campo ricerca per nome / CF / P.IVA
   ├── risultati filtrati per nature ammesse dal ruolo
   ├── soggetti con ruolo gia' assegnato → visibili con warning, non selezionabili
   └── se non trovato → "Crea nuovo soggetto" → form completo (SoggettoForm esistente)
4. Soggetto selezionato/creato → sotto-drawer si chiude
5. Drawer operatore riprende con soggetto agganciato e dati pre-compilati
6. Amministratore completa i campi specifici del ruolo (username, ruolo_sistema, UO)
7. Submit → backend assegna ruolo + crea auth_user
```

### Decisioni architetturali

| #   | Decisione                     | Scelta                                                   | Motivazione                                                        |
| --- | ----------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------ |
| D7  | Inline o sotto-drawer         | Sotto-drawer dedicato                                    | Autonomo, riusabile da qualsiasi contesto senza rifarlo            |
| D8  | Form creazione                | Form completo (SoggettoForm + contatti + indirizzi)      | Gia' costruito e testato; evita anagrafiche incomplete             |
| D9  | Configurazione tipi/CF/PIVA   | Data-driven dal DB, non props hardcoded                  | Aggiungere un ruolo = solo config DB, zero modifiche frontend      |
| D10 | Soggetto con ruolo esistente  | Visibile con warning, non selezionabile                  | Nasconderlo rischia duplicazione; il warning chiarisce la situazione|

---

### 8.1 — DB: Nessuna nuova tabella necessaria

Le tabelle di configurazione esistono gia':

- `config.tipi_ruoli` — elenco ruoli (CL, FO, GE, RIS_UMANA, ...)
- `config.tipi_ruoli_nature_ammesse` — matrice ruolo → nature ammesse (19 righe seed)
- `config.tipi_soggetto_dettaglio` — tipo dettaglio con `cf_obbligatorio`, `piva_obbligatoria`

Serve solo una **query** che aggreghi queste informazioni per un dato tipo_ruolo.
Puo' essere inline nel repository backend o una funzione DB — a scelta.

---

### 8.2 — DB: Evoluzione `fn_crea_operatore` (due flussi)

La funzione attuale crea sempre un soggetto nuovo. Va estesa per accettare
un soggetto esistente:

```text
Flusso A: p_soggetto_id = NULL → crea soggetto PF + ruolo RIS_UMANA + risorsa_umana + auth_user
Flusso B: p_soggetto_id = X    → verifica esistenza soggetto, natura ammessa,
                                  assegna ruolo RIS_UMANA + crea risorsa_umana + auth_user
```

Nuovo parametro: `p_soggetto_id integer DEFAULT NULL`.

Guard aggiuntivi per flusso B:
- Soggetto deve esistere
- Natura soggetto deve essere ammessa per RIS_UMANA (PF)
- Soggetto non deve gia' avere ruolo RIS_UMANA

Questo stesso pattern si applica a future `fn_crea_cliente`, `fn_crea_fornitore`, ecc.

---

### 8.3 — Backend: Endpoint config-resolver

```text
GET /api/v1/anagrafiche/ruoli/{tipo_ruolo_codice}/config-resolver/
```

Risposta:

```json
{
  "tipo_ruolo": "RIS_UMANA",
  "tipo_ruolo_descrizione": "Risorsa Umana",
  "nature_ammesse": ["PF"],
  "tipi_soggetto_dettaglio": [
    {
      "id": 1,
      "codice_interno": "PR",
      "descrizione": "Privato",
      "natura": "PF",
      "cf_obbligatorio": true,
      "piva_obbligatoria": false
    }
  ]
}
```

Per il fornitore:

```json
{
  "tipo_ruolo": "FO",
  "nature_ammesse": ["PF", "PG", "ENC"],
  "tipi_soggetto_dettaglio": [
    { "codice_interno": "PR",  "natura": "PF",   "cf_obbligatorio": true,  "piva_obbligatoria": false },
    { "codice_interno": "DI",  "natura": "PF",   "cf_obbligatorio": true,  "piva_obbligatoria": true  },
    { "codice_interno": "SC",  "natura": "PG",   "cf_obbligatorio": true,  "piva_obbligatoria": true  },
    { "codice_interno": "SP",  "natura": "PG",   "cf_obbligatorio": true,  "piva_obbligatoria": true  },
    { "codice_interno": "ENC", "natura": "ENTE", "cf_obbligatorio": true,  "piva_obbligatoria": true  }
  ]
}
```

Implementazione: `apps/anagrafiche/db/soggetti_repository.py` (query inline)
+ `apps/anagrafiche/api/views_soggetti.py` (nuova view).

---

### 8.4 — Backend: Evoluzione POST creazione operatore

`POST /api/v1/amm-software/operatori/` accetta due payload:

**Flusso A — soggetto nuovo** (come oggi):

```json
{
  "cognome": "Rossi", "nome": "Mario", "codice_fiscale": "...",
  "username": "mrossi", "email": "...", "password": "...",
  "unita_organizzativa_id": 1, "ruolo_sistema": "OPERATIVO"
}
```

**Flusso B — soggetto esistente** (nuovo):

```json
{
  "soggetto_id": 42,
  "username": "mrossi", "email": "...", "password": "...",
  "unita_organizzativa_id": 1, "ruolo_sistema": "OPERATIVO"
}
```

Discriminante: presenza di `soggetto_id`. Se presente, i campi persona
(cognome, nome, CF, ecc.) non sono necessari.

---

### 8.5 — Frontend: Componente `SoggettoResolver.vue`

Sotto-drawer riusabile. Non conosce il contesto chiamante.

**Props**:

| Prop             | Tipo     | Descrizione                                            |
| ---------------- | -------- | ------------------------------------------------------ |
| `visible`        | Boolean  | Visibilita' del sotto-drawer (v-model)                 |
| `tipoRuoloCodice`| String   | Codice ruolo — usato per chiamare config-resolver      |

**Emits**:

| Evento                | Payload                              | Descrizione                          |
| --------------------- | ------------------------------------ | ------------------------------------ |
| `soggetto-selezionato`| `{ id, ragione_sociale, cf, piva }`  | Soggetto confermato                  |
| `soggetto-creato`     | `{ id, ragione_sociale, cf, piva }`  | Soggetto appena creato               |
| `annullato`           | —                                    | Chiusura senza selezione             |

**Componenti riusati (esistenti)**:

- `useServerAutocomplete` — ricerca soggetti con debounce
- `SoggettoForm` + `useSoggettoForm` — form creazione con validazione
- `ContattoForm` + `useContattoForm` — contatto obbligatorio
- `IndirizzoSoggettoForm` — indirizzi se richiesti dal tipo
- `DrawerTitle` + `DrawerFooter` — layout standard drawer
- `useLookup` — caricamento lookup tipi soggetto

**Logica interna**:

1. Al mount chiama `GET /anagrafiche/ruoli/{tipo}/config-resolver/`
2. Filtra i `tipiSoggetto` nel form di creazione in base a `nature_ammesse`
3. Nella ricerca, mostra warning "gia' [ruolo]" se soggetto ha gia' il ruolo target
4. Errori di conflitto ruolo → inline nel drawer, non in toast

---

### 8.6 — Frontend: UtenteDrawer V2

Evoluzione del drawer operatore per integrare il SoggettoResolver:

**Modalita' CREA (V2)**:

```text
┌─────────────────────────────────────────────┐
│  Nuovo Operatore                            │
│                                             │
│  Soggetto: [non selezionato]                │
│  [ Cerca o crea soggetto ]  ← apre resolver │
│                                             │
│  --- dopo selezione ---                     │
│                                             │
│  Soggetto: Mario Rossi (CF: RSSMR...)       │
│  [ Cambia ]                                 │
│                                             │
│  Sezione "Accesso"                          │
│    Username: [______]                       │
│    Email:    [______]                       │
│    Password: [______]                       │
│    Ruolo:    [OPERATIVO v]                  │
│                                             │
│  Sezione "Collocazione"                     │
│    Unita' organizzativa: [______]           │
│    Valido dal/al: [______]                  │
│                                             │
│  [Salva]                                    │
└─────────────────────────────────────────────┘
```

La sezione "Persona" del V1 viene sostituita dal SoggettoResolver.
Se il soggetto e' esistente, i dati persona sono mostrati in sola lettura.
Se il soggetto e' nuovo, viene creato dal resolver prima del submit.

---

### 8.7 — Test

| Area     | File                                               | Test previsti                                        |
| -------- | -------------------------------------------------- | ---------------------------------------------------- |
| BE       | `apps/anagrafiche/tests/api/test_config_resolver.py` | Config resolver per RIS_UMANA, CL, FO, ruolo senza matrice |
| BE       | `apps/amm_software/tests/api/test_crea_utente.py`  | Flusso B: soggetto esistente, natura errata, ruolo duplicato |
| DB       | `db/pgtap/anagrafiche/test_fn_crea_operatore_v2.sql`| Flusso B: soggetto esistente OK, guard natura, guard duplicato |

---

### Priorita' sviluppo — Sprint 4

```text
Fase 1 — Backend (puo' partire subito)
  DB:  8.1  query config-resolver (inline repository)
  BE:  8.3  endpoint GET config-resolver
  Test: parte di 8.7

Fase 2 — Evoluzione creazione (richiede fase 1)
  DB:  8.2  fn_crea_operatore V2 (parametro p_soggetto_id)
  BE:  8.4  POST utenti con due flussi
  Test: parte di 8.7

Fase 3 — Frontend (richiede fase 1 + fase 2)
  FE:  8.5  SoggettoResolver.vue
  FE:  8.6  UtenteDrawer V2
```
# Permessi e Autorizzazioni — WIP

> Documento di lavoro per pianificazione e avanzamento.
> La guida architetturale di riferimento è `docs/it/guide/architettura-permessi-e-autorizzazioni.md`.

---

## Prerequisiti già esistenti

- [x] `django.auth_user` — schema Django con autenticazione JWT
- [x] `config.unita_organizzative` — reparti con gerarchia `parent_id`
- [x] `config.qualifiche` — qualifiche professionali
- [x] `anagrafiche.risorse_umane` — con FK a `unita_organizzativa_id`
- [x] `anagrafiche.risorse_umane_auth_user` — ponte 1:1 user↔risorsa umana
- [x] `anagrafiche.emittenti_fiscali` — emittenti con utilities e billing account
- [x] `jwt_audit_middleware.py` — propaga `app.jwt_user` in sessione PG

---

## 1. Strutture base e classificazione utente

### DB

- [x] 1.1 — ENUM `config.ruolo_sistema` (`ADMIN`, `OPERATIVO`, `DISABILITATO`)
- [x] 1.2 — ALTER `anagrafiche.risorse_umane_auth_user` ADD `ruolo_sistema` (default `OPERATIVO`)
- [x] 1.3 — ENUM `config.livello_accesso` (`TUTTO`, `LETTURA`, `BLOCCATO`)
- [x] 1.4 — Tabella `config.aree_funzionali` + seed 10 aree
- [x] 1.5 — Tabella `config.azioni_processo` + seed iniziale
- [x] 1.6 — Tabella `config.area_model_overrides`

### Backend

- [x] 1.7 — Model ORM `AreaFunzionale` (`managed=False`) — `apps/config/models.py`
- [x] 1.8 — Model ORM `AzioneProcesso` (`managed=False`) — `apps/config/models.py`
- [x] 1.9 — Model ORM `AreaModelOverride` (`managed=False`) — `apps/config/models.py`
- [x] 1.10 — Model ORM `RisorseUmaneAuthUser` aggiornato con campo `ruolo_sistema` — `apps/anagrafiche/models.py`

---

## 2. Profili reparto (ereditarietà)

### DB

- [x] 2.1 — Tabella `config.profili_reparto_aree` — atteso DB 1.3, 1.4
- [x] 2.2 — Tabella `config.profili_reparto_azioni` — atteso DB 1.5

### Backend

- [x] 2.3 — Model ORM `ProfiloRepartoArea` (`managed=False`) — `apps/config/models.py`
- [x] 2.4 — Model ORM `ProfiloRepartoAzione` (`managed=False`) — `apps/config/models.py`

---

## 3. Override utente

### DB

- [x] 3.1 — Tabella `config.user_override_aree` — atteso DB 1.3, 1.4
- [x] 3.2 — Tabella `config.user_override_oggetti` — atteso DB 1.3
- [x] 3.3 — Tabella `config.user_override_azioni` — atteso DB 1.5
- [x] 3.4 — Tabella `config.user_emittenti_fiscali` — atteso DB prerequisito emittenti_fiscali

### Backend

- [x] 3.5 — Model ORM `UserOverrideArea` (`managed=False`) — `apps/config/models.py`
- [x] 3.6 — Model ORM `UserOverrideOggetto` (`managed=False`) — `apps/config/models.py`
- [x] 3.7 — Model ORM `UserOverrideAzione` (`managed=False`) — `apps/config/models.py`
- [x] 3.8 — Model ORM `UserEmittenteFiscale` (`managed=False`) — `apps/config/models.py`

---

## 4. Enforcement backend

### Backend

- [x] 4.1 — `PermissionResolver` in `apps/core/services/permissions_resolver.py`
- [x] 4.2 — `ZeroERPPermission` (DRF permission class) in `apps/core/api/permissions.py`
- [x] 4.3 — `EmittenteFiscaleScopeMixin` in `apps/core/mixins.py`
- [x] 4.4 — Middleware PG session: `app.current_user_id` + check DISABILITATO in `jwt_audit_middleware.py`

---

## 5. Defense-in-depth DB

### DB

- [x] 5.1 — Funzione `config.fn_check_user_emittente_scope()` — `20_code/config/20260228-24`
- [x] 5.2 — Trigger guard su `vendite.fatture` (scope emittente) — `trgfn_guard_emittente_scope` + trigger `20260228-25/-26`
- [x] 5.3 — Trigger guard su `pagamenti.vendite_movimenti` (scope emittente via fattura) — `20260228-27`. NB: ordini (vendite/acquisti) non hanno colonna emittente

### Backend

- [x] 5.4 — Test Django enforcement permessi (unit test `PermissionResolver`) — `apps/core/tests/services/test_permissions_resolver.py`
- [x] 5.5 — Test Django scope emittente (unit test mixin) — `apps/core/tests/mixins/test_emittente_fiscale_scope.py`

### Test DB

- [x] 5.6 — Test pgTAP per `fn_check_user_emittente_scope` — atteso DB 5.1
- [x] 5.7 — Test pgTAP per trigger guard fatture — atteso DB 5.2

---

## 6. Diagnostica e integrazione

### Backend

- [x] 6.1 — Endpoint diagnostico `/api/v1/core/users/{id}/permessi-effettivi/` — `apps/core/api/views.py`
- [x] 6.2 — Messaggio chiaro quando reparto senza profilo configurato — `ZeroERPPermission._set_deny_message` + `PermissionResolver.has_profilo_reparto_area`
- [x] 6.3 — `ZeroERPPermission` come default DRF in `settings.py` — core views aggiornate
- [x] 6.4 — `EmittenteFiscaleScopeMixin` non applicabile alle view attuali (SQL diretto); pronto per ViewSet ORM futuri

---

## 7. Caching e performance

### Backend

- [x] 7.1 — Cache L1 (per-request dict) + L2 (Redis) per `PermissionResolver` — `apps/core/services/permissions_cache.py` + integrazione in `ZeroERPPermission`
- [x] 7.2 — Invalidazione cache Redis: `invalidate_user()`, `invalidate_department()`, `invalidate_all()` — `apps/core/services/permissions_cache.py`

---

## 8. Gestione scadenze e audit

### DB

- [x] 8.1 — Funzione `config.fn_get_override_scaduti(p_giorni_tolleranza)` — `20_code/config/20260228-28`

### Backend

- [ ] 8.2 — Log storico modifiche profili e override (audit trail permessi) — atteso DB sezione 2, 3

---

## Fasi di rilascio

> Promemoria operativo: in quale ordine le sezioni sopra diventano utilizzabili
> e cosa integrare sulle API/funzioni già esistenti.

### Fase 1 — DB: strutture base

Completare sezioni **1**, **2**, **3** (tutti i punti DB).
Al termine il database ha tutte le tabelle, gli ENUM e i seed necessari.

### Fase 2 — Django: model + enforcement → API vendite protette subito

Completare sezioni **1**, **2**, **3** (punti backend: model `managed=False`)
poi sezione **4** (`PermissionResolver`, `ZeroERPPermission`, middleware).

**Integrazione API esistenti (vendite):**

- [x] F2.1 — Aggiungere `ZeroERPPermission` a tutte le 11 view V1 vendite (`apps/vendite/api/views.py`)
- [x] F2.2 — Scope emittente applicato via SQL DB-first (`config.fn_get_emittenti_scope_sr_ids`) in `VenditeRepository` — atteso DB funzione
- [x] F2.3 — `ApiRunLottoPipelineV1` ha `post_permission = "genera_fatture_lotti"` per check azione
- [x] F2.4 — N/A: nessuna view API esposta su anagrafiche, catalogo, pagamenti (file `views.py` vuoti)

A questo punto tutte le API esistenti sono protette dal sistema permessi.

### Fase 3 — Funzioni SQL, scope emittente e azioni di processo

#### Sviluppi DB

- [ ] D3.1 — Creare funzioni SQL di risoluzione permessi (spec. B.1–B.5)
  - `config.fn_get_ruolo_sistema` (B.1)
  - `config.fn_resolve_livello_area` (B.2)
  - `config.fn_resolve_livello_oggetto` (B.3)
  - `config.fn_check_azione_processo` (B.4)
  - `config.fn_get_emittenti_scope` (B.5)
  - **Prerequisiti**: sezioni DB 1–3 completate ✅
  - **Specifiche**: sezione "Analisi refactoring", B.1–B.5
- [ ] D3.2 — Creare funzione SQL `config.fn_get_emittenti_scope_sr_ids` (spec. B.7)
  - Mappa `emittente_fiscale_id` → `soggetto_ruolo_id` per le query vendite
  - **Prerequisiti**: D3.1 (usa `fn_get_ruolo_sistema`), tabella `config.user_emittenti_fiscali` ✅
  - **Specifiche**: sezione "Analisi refactoring", B.7
- [ ] D3.3 — Seed `config.azioni_processo` con nuovi codename
  - `reset_lotto_draft` — reset lotto a stato DRAFT
  - `reset_lotto_fattura_draft` — reset singola fattura lotto a DRAFT
  - `run_commesse_push` — invio commesse a sistema esterno
  - **Prerequisiti**: tabella `config.azioni_processo` ✅ (sez. 1.5)

#### Sviluppi Backend

- [ ] B3.1 — Aggiungere `post_permission` alle 3 view write vendite rimanenti
  - `ApiResetLottoDraftV1` → `post_permission = "reset_lotto_draft"`
  - `ApiResetLottoFatturaDraftV1` → `post_permission = "reset_lotto_fattura_draft"`
  - `ApiRunCommessePushV1` → `post_permission = "run_commesse_push"`
  - **Prerequisiti**: D3.3 (codenames presenti nel DB)
- [ ] B3.2 — Test unitari per i nuovi `post_permission`
  - Verificare che `ZeroERPPermission.has_permission` instradi correttamente
  - **Prerequisiti**: B3.1

#### Note Fase 3

- `genera_fatture_lotti` e' gia' attivo su `ApiRunLottoPipelineV1` (F2.3 ✅).
- F2.2 (scope emittente `VenditeRepository`): codice backend completato ✅ — attende D3.2 per funzionare in produzione.
- F3.1/F3.2 (`Meta.permissions`): non necessarie — il sistema usa `config.azioni_processo` direttamente.
- Pagamenti: nessuna view API esposta — azioni processo pagamenti rimandate.

### Fase 4 — Defense-in-depth, diagnostica, caching, audit

- [x] Sezioni 5, 6, 7 completate
- [ ] 8.2 — Log storico modifiche profili e override (audit trail permessi)
  - **Prerequisiti**: D3.1 (funzioni SQL attive), sezioni DB 2–3 ✅

---

## Note

- Il documento architetturale (sez. 13) definisce il campo `ruolo_sistema` e la catena di risoluzione aggiornata.
- L'ordine delle sezioni rispecchia le dipendenze: ogni punto backend indica i prerequisiti DB.
- I punti sono sequenziali per sezione: all'interno di una sezione, i numeri DB vengono prima dei backend.
- Le **Fasi di rilascio** indicano quando le API già esistenti (vendite, pipeline) vengono integrate nel sistema permessi.

---

## Analisi refactoring — logica duplicata e funzioni SQL

> Analisi effettuata sul codice backend permessi completato fino a sez. 7.
> Obiettivo: eliminare duplicazioni Python e spostare logica di risoluzione nel DB (filosofia DB-first).

### A. Duplicazioni Python individuate

#### A.1 — `get_ruolo_sistema` duplicato tra middleware e resolver

Il middleware `JwtAuditMiddleware._get_ruolo_sistema_cached()` esegue la stessa identica query
di `PermissionResolver.get_ruolo_sistema()`: legge `ruolo_sistema` da `risorse_umane_auth_user`.
Le due implementazioni hanno cache separate (`request._zeroerp_ruolo_sistema` vs `cache["ruolo_sistema"]`),
quindi il risultato del middleware non viene riutilizzato dal resolver.

**Fix**: il middleware deve usare `PermissionResolver.get_ruolo_sistema()` oppure seminare
il risultato nella cache per-request che il resolver trova gia' popolata.

#### A.2 — Pattern ruolo_sistema ripetuto 3 volte nel resolver

Lo stesso blocco di check `DISABILITATO → bloccato / ADMIN → tutto / else → resolve_fn()`
appare identico in `get_livello_area`, `get_livello_oggetto`, `check_azione`.

**Fix**: estrarre un metodo helper interno, oppure (preferibile) spostare la catena
in una funzione SQL unica che fa tutto in un roundtrip.

#### A.3 — Pattern cache read/write ripetuto 7 volte

Il boilerplate `if cache and key in cache: return / ... / cache[key] = result`
appare in 7 metodi del resolver.

**Fix**: estrarre un helper `_cached(cache, key, compute_fn)` oppure un decoratore.
Se le funzioni SQL sostituiscono le query ORM, il resolver si semplifica drasticamente
e il pattern diventa meno ripetitivo.

#### A.4 — `_save_cache_to_redis` chiamato 8 volte in `has_permission`

Ogni exit path di `ZeroERPPermission.has_permission()` chiama `_save_cache_to_redis()` separatamente.

**Fix**: ristrutturare con un blocco `try/finally` per chiamarlo una sola volta.

### B. Funzioni SQL proposte — specifiche per team DB

Le funzioni seguono le convenzioni del progetto: schema `config`, prefisso `fn_`, parametri `p_`,
variabili locali `v_`, errori via `script.fn_log_and_raise_error()`, COMMENT ON FUNCTION obbligatorio.

#### B.1 — `config.fn_get_ruolo_sistema`

**Scopo**: Restituisce il `ruolo_sistema` di un utente dalla tabella ponte.
Blocco base riusato da tutte le altre funzioni.

| Elemento    | Valore                                                              |
| ----------- | ------------------------------------------------------------------- |
| Schema      | `config`                                                            |
| Nome        | `fn_get_ruolo_sistema`                                              |
| Parametri   | `p_auth_user_id integer` (auth_user.id)                             |
| Ritorno     | `config.ruolo_sistema` (ENUM). NULL se l'utente non ha record ponte |
| Volatilita' | STABLE                                                              |

**Logica**:

```sql
SELECT ruolo_sistema
  FROM anagrafiche.risorse_umane_auth_user
 WHERE auth_user_id = p_auth_user_id;
```

**Dipendenze**: `anagrafiche.risorse_umane_auth_user`

---

#### B.2 — `config.fn_resolve_livello_area`

**Scopo**: Risolve il livello di accesso effettivo di un utente per un'area funzionale.
Catena completa: `ruolo_sistema → override utente area → profilo reparto → BLOCCATO`.

| Elemento    | Valore                                                    |
| ----------- | --------------------------------------------------------- |
| Schema      | `config`                                                  |
| Nome        | `fn_resolve_livello_area`                                 |
| Parametri   | `p_auth_user_id integer`, `p_area_schema_db varchar(50)`  |
| Ritorno     | `config.livello_accesso` (ENUM: TUTTO, LETTURA, BLOCCATO) |
| Volatilita' | STABLE                                                    |

**Logica (catena di risoluzione)**:

```sql
-- 1. v_ruolo := fn_get_ruolo_sistema(p_auth_user_id)
--    NULL (nessun record ponte) → return 'BLOCCATO'
--    'DISABILITATO'             → return 'BLOCCATO'
--    'ADMIN'                    → return 'TUTTO'

-- 2. (OPERATIVO) Cerca override utente area:
SELECT livello
  FROM config.user_override_aree uoa
  JOIN config.aree_funzionali af ON af.id = uoa.area_id
 WHERE uoa.auth_user_id = p_auth_user_id
   AND af.schema_db = p_area_schema_db
   AND (uoa.valido_dal IS NULL OR uoa.valido_dal <= CURRENT_DATE)
   AND (uoa.valido_al  IS NULL OR uoa.valido_al  >= CURRENT_DATE);
-- se trovato, return livello

-- 3. Cerca profilo reparto:
SELECT pra.livello
  FROM config.profili_reparto_aree pra
  JOIN config.aree_funzionali af ON af.id = pra.area_id
  JOIN anagrafiche.risorse_umane_auth_user rau
    ON rau.auth_user_id = p_auth_user_id
  JOIN anagrafiche.risorse_umane ru
    ON ru.id = rau.risorsa_umana_id
 WHERE ru.unita_organizzativa_id = pra.unita_organizzativa_id
   AND af.schema_db = p_area_schema_db;
-- se trovato, return livello

-- 4. Default → return 'BLOCCATO'
```

**Dipendenze**: `anagrafiche.risorse_umane_auth_user`, `anagrafiche.risorse_umane`,
`config.aree_funzionali`, `config.user_override_aree`, `config.profili_reparto_aree`

---

#### B.3 — `config.fn_resolve_livello_oggetto`

**Scopo**: Risolve il livello di accesso per un singolo model Django (app_label + model_name).
Se esiste un override oggetto lo usa, altrimenti risale alla catena area.

| Elemento    | Valore                                                                                                            |
| ----------- | ----------------------------------------------------------------------------------------------------------------- |
| Schema      | `config`                                                                                                          |
| Nome        | `fn_resolve_livello_oggetto`                                                                                      |
| Parametri   | `p_auth_user_id integer`, `p_app_label varchar(100)`, `p_model_name varchar(100)`, `p_area_schema_db varchar(50)` |
| Ritorno     | `config.livello_accesso` (ENUM)                                                                                   |
| Volatilita' | STABLE                                                                                                            |

**Logica**:

```sql
-- 1. v_ruolo := fn_get_ruolo_sistema(p_auth_user_id)
--    NULL/'DISABILITATO' → return 'BLOCCATO'
--    'ADMIN'             → return 'TUTTO'

-- 2. (OPERATIVO) Cerca override utente oggetto:
SELECT livello
  FROM config.user_override_oggetti
 WHERE auth_user_id = p_auth_user_id
   AND app_label    = p_app_label
   AND model_name   = p_model_name
   AND (valido_dal IS NULL OR valido_dal <= CURRENT_DATE)
   AND (valido_al  IS NULL OR valido_al  >= CURRENT_DATE);
-- se trovato, return livello

-- 3. Fallback → return fn_resolve_livello_area(p_auth_user_id, p_area_schema_db)
```

**Dipendenze**: `config.user_override_oggetti` + dipendenze di `fn_resolve_livello_area`

---

#### B.4 — `config.fn_check_azione_processo`

**Scopo**: Verifica se un'azione di processo e' abilitata per un utente.
Catena: `ruolo_sistema → override utente → profilo reparto → negata`.

| Elemento    | Valore                                                         |
| ----------- | -------------------------------------------------------------- |
| Schema      | `config`                                                       |
| Nome        | `fn_check_azione_processo`                                     |
| Parametri   | `p_auth_user_id integer`, `p_permission_codename varchar(100)` |
| Ritorno     | `boolean`                                                      |
| Volatilita' | STABLE                                                         |

**Logica**:

```sql
-- 1. v_ruolo := fn_get_ruolo_sistema(p_auth_user_id)
--    NULL/'DISABILITATO' → return false
--    'ADMIN'             → return true

-- 2. (OPERATIVO) Cerca override utente azione:
SELECT uoa.abilitata
  FROM config.user_override_azioni uoa
  JOIN config.azioni_processo ap ON ap.id = uoa.azione_id
 WHERE uoa.auth_user_id = p_auth_user_id
   AND ap.permission_codename = p_permission_codename
   AND (uoa.valido_dal IS NULL OR uoa.valido_dal <= CURRENT_DATE)
   AND (uoa.valido_al  IS NULL OR uoa.valido_al  >= CURRENT_DATE);
-- se trovato, return abilitata

-- 3. Cerca profilo reparto azione:
SELECT pra.abilitata
  FROM config.profili_reparto_azioni pra
  JOIN config.azioni_processo ap ON ap.id = pra.azione_id
  JOIN anagrafiche.risorse_umane_auth_user rau
    ON rau.auth_user_id = p_auth_user_id
  JOIN anagrafiche.risorse_umane ru
    ON ru.id = rau.risorsa_umana_id
 WHERE ru.unita_organizzativa_id = pra.unita_organizzativa_id
   AND ap.permission_codename = p_permission_codename;
-- se trovato, return abilitata

-- 4. Default → return false
```

**Dipendenze**: `anagrafiche.risorse_umane_auth_user`, `anagrafiche.risorse_umane`,
`config.azioni_processo`, `config.user_override_azioni`, `config.profili_reparto_azioni`

---

#### B.5 — `config.fn_get_emittenti_scope`

**Scopo**: Restituisce gli ID emittenti fiscali autorizzati per un utente.
NULL = nessuna restrizione (whitelist vuota, vede tutto).

| Elemento    | Valore                                         |
| ----------- | ---------------------------------------------- |
| Schema      | `config`                                       |
| Nome        | `fn_get_emittenti_scope`                       |
| Parametri   | `p_auth_user_id integer`                       |
| Ritorno     | `bigint[]` (array). NULL = nessuna restrizione |
| Volatilita' | STABLE                                         |

**Logica**:

```sql
SELECT array_agg(emittente_fiscale_id)
  FROM config.user_emittenti_fiscali
 WHERE auth_user_id = p_auth_user_id;
-- Nessuna riga → return NULL (nessuna restrizione)
-- Almeno una riga → return array di ID
```

**Dipendenze**: `config.user_emittenti_fiscali`

---

#### B.6 — `config.fn_check_user_emittente_scope`

**Scopo**: Verifica se un utente ha accesso a uno specifico emittente fiscale.
Pensata per i trigger defense-in-depth (task WIP 5.1-5.3).

| Elemento    | Valore                                                                           |
| ----------- | -------------------------------------------------------------------------------- |
| Schema      | `config`                                                                         |
| Nome        | `fn_check_user_emittente_scope`                                                  |
| Parametri   | `p_auth_user_id integer` (o NULL per job batch), `p_emittente_fiscale_id bigint` |
| Ritorno     | `boolean`                                                                        |
| Volatilita' | STABLE                                                                           |

**Logica**:

```sql
-- 1. Se p_auth_user_id IS NULL → return true (nessun utente = job batch, nessun filtro)

-- 2. v_ruolo := fn_get_ruolo_sistema(p_auth_user_id)
--    'ADMIN' → return true (admin vede tutto)

-- 3. Conta righe whitelist:
SELECT count(*) FROM config.user_emittenti_fiscali
 WHERE auth_user_id = p_auth_user_id;
-- Se 0 righe → return true (nessuna restrizione)

-- 4. Cerca match specifico:
RETURN EXISTS(
  SELECT 1 FROM config.user_emittenti_fiscali
   WHERE auth_user_id = p_auth_user_id
     AND emittente_fiscale_id = p_emittente_fiscale_id
);
```

**Dipendenze**: `anagrafiche.risorse_umane_auth_user`, `config.user_emittenti_fiscali`

---

#### B.7 — `config.fn_get_emittenti_scope_sr_ids`

**Scopo**: Restituisce i `soggetto_ruolo_id` degli emittenti autorizzati per un utente.
Le tabelle vendite usano `emittente_soggetto_ruolo_id` (FK a `anagrafiche.soggetti_ruoli`),
non `emittente_fiscale_id`, quindi serve questa mappatura aggiuntiva rispetto a `fn_get_emittenti_scope`.

| Elemento    | Valore                                                               |
| ----------- | -------------------------------------------------------------------- |
| Schema      | `config`                                                             |
| Nome        | `fn_get_emittenti_scope_sr_ids`                                      |
| Parametri   | `p_auth_user_id integer`                                             |
| Ritorno     | `bigint[]`. NULL = nessuna restrizione. Array vuoto = nessun accesso |
| Volatilita' | STABLE                                                               |

**Logica**:

```sql
-- 1. v_ruolo := config.fn_get_ruolo_sistema(p_auth_user_id)
--    NULL / 'DISABILITATO' → return '{}'::bigint[]  (nessun accesso)
--    'ADMIN'               → return NULL             (nessuna restrizione)

-- 2. (OPERATIVO) Cerca whitelist e mappa a soggetto_ruolo_id:
SELECT array_agg(ef.soggetto_ruolo_id)
  INTO v_ids
  FROM config.user_emittenti_fiscali uef
  JOIN anagrafiche.emittenti_fiscali ef ON ef.id = uef.emittente_fiscale_id
 WHERE uef.auth_user_id = p_auth_user_id;

-- v_ids IS NULL (nessuna riga whitelist) → return NULL (nessuna restrizione)
-- v_ids array                            → return array di soggetto_ruolo_id
```

**Tabella semantica** (allineata con `fn_get_emittenti_scope`):

| Caso                           | Ritorno          | Effetto sul WHERE       |
| ------------------------------ | ---------------- | ----------------------- |
| ADMIN                          | NULL             | Nessun filtro           |
| OPERATIVO senza whitelist      | NULL             | Nessun filtro           |
| OPERATIVO con whitelist [A, B] | `{srA, srB}`     | `= ANY(array)`          |
| DISABILITATO / senza bridge    | `'{}'::bigint[]` | Nessun match → 0 righe |

**Dipendenze**: `config.fn_get_ruolo_sistema`, `config.user_emittenti_fiscali`,
`anagrafiche.emittenti_fiscali`

---

### C. Dipendenze tra funzioni SQL

```text
fn_get_ruolo_sistema                (standalone, blocco base)
  ├── fn_resolve_livello_area       (usa fn_get_ruolo_sistema)
  │     └── fn_resolve_livello_oggetto  (fallback a fn_resolve_livello_area)
  ├── fn_check_azione_processo      (usa fn_get_ruolo_sistema)
  ├── fn_check_user_emittente_scope (usa fn_get_ruolo_sistema)
  └── fn_get_emittenti_scope_sr_ids (usa fn_get_ruolo_sistema + mapping soggetto_ruolo)

fn_get_emittenti_scope              (standalone, query semplice)
```

**Ordine di creazione**: `fn_get_ruolo_sistema` per primo, poi le altre in qualsiasi ordine.

### D. Impatto sul backend dopo le funzioni SQL

Una volta disponibili le funzioni SQL, il `PermissionResolver` Python passera' da 4-5 query ORM
a 1 sola chiamata `cursor.execute()` per risoluzione. Il refactoring Python (sezione A)
diventa in gran parte automatico: la maggior parte dei metodi del resolver si ridurra'
a una chiamata SQL + gestione cache L1/L2.

I trigger defense-in-depth (task 5.1-5.3) potranno usare direttamente `fn_check_user_emittente_scope`
e `fn_resolve_livello_area` senza logica duplicata.

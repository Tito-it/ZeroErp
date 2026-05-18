# fn_change_user_emittenti_scope

### Scopo

Orchestrazione **atomica** del cambio di scope emittenti per un
`auth_user`, dietro al pulsante "Cambia scope" del drawer Operatore
(Fase 2 P1 2026-04-29).

È **l'unico writer applicativo** ammesso su
`config.user_emittenti_fiscali` per i flussi di drawer: l'enforcement dei
guard (ultimo SA, validità EF, immutabilità della colonna) avviene al suo
interno; il BE traduce gli errori SQL nelle policy HTTP standard
(`error_policies.py`).

> **Vedi anche**
>
> - [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> - [refactor operatore-emittenti — Fase 1](/dev/work-done/refactor-operatore-emittenti) — vincolo `UNIQUE(auth_user_id)` su `user_emittenti_fiscali`
> - [fn_get_user_emittenti_scope](/dbzero/script/funzioni/fn_get_user_emittenti_scope) — vista dichiarativa dello stato corrente
> - [fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo) — guard ultimo SA
> - [trgfn_user_emittenti_fiscali_guard_delete](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete) — guard DELETE bypassato qui via GUC

## Schema

`script` (cross-dominio: scrive `config.user_emittenti_fiscali`,
chiama `script.fn_check_ultimo_super_admin_attivo` e
`script.fn_log_and_raise_error`).

## Firma

```sql
script.fn_change_user_emittenti_scope(
    p_auth_user_id   INTEGER,
    p_emittente_ids  BIGINT[]   -- elementi: anagrafiche.emittenti_fiscali.id
) RETURNS jsonb
```

> Nota tecnica: PostgreSQL **non** supporta la sintassi
> `colonna%TYPE[]` nei parametri di funzione (errore di sintassi al
> CREATE FUNCTION). Il parametro è quindi `BIGINT[]` esplicito; la
> coerenza semantica con `anagrafiche.emittenti_fiscali.id` è garantita
> dalla FK in `INSERT` interno.

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_auth_user_id` | `INTEGER` | Sì | ID utente Django target del cambio scope. |
| `p_emittente_ids` | `BIGINT[]` | Sì (può essere `NULL` o `[]`) | Array degli `emittente_fiscale_id` da assegnare. **Contratto array future-proof** anche se oggi solo `0` o `1` elemento sono ammessi. |

### Mappatura `p_emittente_ids` → scope target

| `array_length(p_emittente_ids, 1)` | Scope target | Effetto |
|:---:|:---:|---|
| `NULL` o `0` | `GLOBAL` | DELETE riga corrente (se esiste). |
| `1` | `SINGLE` | INSERT (o DELETE+INSERT se cambia `emittente_fiscale_id`). |
| `>1` | — | Raise `E_OPERATORE_SCOPE_MULTI_NON_AMMESSO` (id 405). |

## Output

`jsonb` a 3 chiavi:

| Chiave | Tipo | Significato |
|---|---|---|
| `changed` | `boolean` | `true` sse è stata applicata almeno una scrittura (INSERT, DELETE o entrambi). `false` su no-op. |
| `scope_mode` | `text` | Scope **finale** (`GLOBAL` o `SINGLE`). |
| `emittente_id` | `bigint` o `null` | EF finale (`null` se `GLOBAL`). |

Esempio:

```json
{ "changed": true, "scope_mode": "SINGLE", "emittente_id": 17 }
```

## Algoritmo

1. **Guard parametri** (tutti via `script.fn_log_and_raise_error`):
   `auth_user_id` `NULL/<=0` → `E_OPERATORE_SCOPE_PARAM_NON_VALIDO`.
   Lunghezza `p_emittente_ids > 1` → `E_OPERATORE_SCOPE_MULTI_NON_AMMESSO`.
   Singolo elemento `NULL/<=0` → `E_OPERATORE_SCOPE_PARAM_NON_VALIDO`.
2. **Stato corrente**: `SELECT ... FOR UPDATE` su
   `user_emittenti_fiscali` per evitare race con altre sessioni che
   modificano la stessa riga in parallelo.
3. **No-op**: se `current = target` (anche entrambi `NULL`), ritorna
   `changed=false` senza scrittura né guard SA.
4. **Guard ultimo SA**: se `fn_check_ultimo_super_admin_attivo(au) = true`
   AND il cambio è reale, raise `E_PROFILO_ULTIMO_SUPER_ADMIN`
   (id 384, condivisa con i trigger guard di Fase 1).
5. **Apply**:
   * `current IS NOT NULL` → `SET LOCAL zeroerp.allow_user_emittente_delete_override='on'`
     + `DELETE` + `SET LOCAL ... = ''` (reset difensivo).
   * `target IS NOT NULL` → `INSERT` (FK e
     `dbops.trgfn_child_requires_active_parent` validano EF esistente
     e attivo: nessun pre-check locale necessario).
6. Ritorna `jsonb` con `changed=true` e nuovo stato.

## Casi pratici

| Scenario | Operazione interna |
|---|---|
| `GLOBAL → SINGLE` (assegna emittente) | INSERT |
| `SINGLE → GLOBAL` (rimuovi assegnazione) | DELETE (con override) |
| `SINGLE → SINGLE'` (cambia EF) | DELETE + INSERT (`emittente_fiscale_id` è bloccato da `lock_columns`, `UPDATE` non praticabile) |
| `GLOBAL → GLOBAL` o `SINGLE → SINGLE` stesso EF | no-op |

## Override `guard_delete`: motivazione

[`trgfn_user_emittenti_fiscali_guard_delete`](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete)
blocca normalmente la `DELETE` su `user_emittenti_fiscali` se l'utente
Django è ancora attivo, per evitare cancellazioni "selvagge" durante
l'attività dell'operatore.

`fn_change_user_emittenti_scope` rappresenta un **flusso amministrativo
controllato**: la modifica passa per i suoi guard interni (ultimo SA,
validazione EF, FOR UPDATE). Il bypass del trigger non ha quindi senso
"libero": serve solo per consentire il `DELETE+INSERT` orchestrato. La
GUC viene resettata immediatamente dopo, così se la transazione
contiene altre operazioni dopo la fn esse non beneficiano del bypass.

```sql
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = ...;
SET LOCAL zeroerp.allow_user_emittente_delete_override = '';
```

## Codici errore

| Codice | id | Quando | HTTP suggerito |
|---|---|---|---|
| `E_OPERATORE_SCOPE_PARAM_NON_VALIDO` | 409 | `p_auth_user_id` o singolo `emittente_id` `NULL/<=0` | 400 |
| `E_OPERATORE_SCOPE_MULTI_NON_AMMESSO` | 405 | `p_emittente_ids` ha > 1 elemento | 400 |
| `E_PROFILO_ULTIMO_SUPER_ADMIN` | 384 | Cambio reale richiesto su utente che è ultimo SA attivo | 409 (conflict) o 400 |

> Tutti gli errori passano per `script.fn_log_and_raise_error` →
> audit log su `dbops.audit_log` + messaggio i18n da
> `config.messaggi_errore` + codice stabile per il mapping
> `error_policies.py`. **Update 2026-04-29 (Fase 5)**: il guard
> parametri prima usava `RAISE EXCEPTION` diretto con SQLSTATE 22023
> (mappato a `E_DATABASE` generico). Refactor in migration
> `20260429-09-update-fn-change-user-emittenti-scope-use-log-and-raise.yaml`.

## Caratteristiche

* `LANGUAGE plpgsql VOLATILE` — esegue DML, control flow,
  `SET LOCAL`, `RAISE`. **Non** `STABLE`.
* `FOR UPDATE` sulla riga corrente: protegge da race tra sessioni
  parallele che modificano lo stesso `auth_user_id`.
* La fn è l'unico writer programmatico ammesso. Eventuali script di
  manutenzione manuale possono comunque settare la GUC override e
  agire direttamente — pattern documentato in
  [`trgfn_user_emittenti_fiscali_guard_delete`](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete).

## Dipendenze

### Tabelle

* `config.user_emittenti_fiscali` (RW)
* `anagrafiche.emittenti_fiscali` (FK validation via `dbops.trgfn_child_requires_active_parent`)
* `django.auth_user` (FK validation, lettura indiretta via guard_delete)

### Funzioni / GUC

* `script.fn_check_ultimo_super_admin_attivo(integer)` — guard ultimo SA
* `script.fn_log_and_raise_error(...)` — raise standardizzato
* GUC `zeroerp.allow_user_emittente_delete_override` — override locale guard_delete

## Trigger interagenti

| Trigger | Tabella | Comportamento durante la fn |
|---|---|---|
| `trgfn_user_emittenti_fiscali_guard_delete` | `user_emittenti_fiscali` | Bypassato via GUC `'on'` per il solo passaggio DELETE |
| `trgfn_lock_columns` (`emittente_fiscale_id`) | `user_emittenti_fiscali` | Non scatta (la fn evita UPDATE) |
| `dbops.trgfn_child_requires_active_parent` | `user_emittenti_fiscali` | Scatta su INSERT — rifiuta EF inattivi/inesistenti |
| `script.trgfn_audit_data_user_generic` | `user_emittenti_fiscali` | Audit standard `data_*` `user_*` |

## Chi la chiama

* Backend: nuovo endpoint `POST /api/v1/amm-software/operatori/<auth_user_id>/scope/`
  (proposta Fase 2 BE), service che mappa errore SQL → HTTP.
* Test pgTAP: `db/pgtap/script/test-fn-change-user-emittenti-scope.sql`.

## Riferimenti

* WIP: [refactor operatore-emittenti — Fase 2 capability scope](/dev/work-done/refactor-operatore-emittenti)
* Migration: `db/changelog/migrations_v2/20_code/script/20260429-04-create-fn-change-user-emittenti-scope-mctit.yaml`
* Migration update Fase 5: `db/changelog/migrations_v2/20_code/script/20260429-09-update-fn-change-user-emittenti-scope-use-log-and-raise-mctit.yaml` (refactor guard parametri → `fn_log_and_raise_error`)
* Codici errore: `E_OPERATORE_SCOPE_MULTI_NON_AMMESSO` id 405, `E_OPERATORE_SCOPE_PARAM_NON_VALIDO` id 409

## Esempio

```sql
-- Promuovi un operatore GLOBAL a SINGLE su EF id=17
SELECT script.fn_change_user_emittenti_scope(42, ARRAY[17]::bigint[]);
-- {"changed": true, "scope_mode": "SINGLE", "emittente_id": 17}

-- No-op (stesso scope)
SELECT script.fn_change_user_emittenti_scope(42, ARRAY[17]::bigint[]);
-- {"changed": false, "scope_mode": "SINGLE", "emittente_id": 17}

-- Demote a GLOBAL
SELECT script.fn_change_user_emittenti_scope(42, NULL::bigint[]);
-- {"changed": true, "scope_mode": "GLOBAL", "emittente_id": null}

-- Cambio EF (DELETE + INSERT)
SELECT script.fn_change_user_emittenti_scope(42, ARRAY[18]::bigint[]);
-- {"changed": true, "scope_mode": "SINGLE", "emittente_id": 18}

-- MULTI rifiutato applicativamente
SELECT script.fn_change_user_emittenti_scope(42, ARRAY[17, 18]::bigint[]);
-- ERROR: E_OPERATORE_SCOPE_MULTI_NON_AMMESSO

-- Ultimo SA: cambio reale bloccato
SELECT script.fn_change_user_emittenti_scope(7, ARRAY[17]::bigint[]);
-- ERROR: E_PROFILO_ULTIMO_SUPER_ADMIN
```

## Note di migrazione / integrazione

* La fn rimpiazza eventuali UPDATE/DELETE applicativi sparsi su
  `user_emittenti_fiscali`: per il drawer Operatore è il **single point
  of write** ammesso.
* L'attuale endpoint di cambio assegnazione (se esiste lato BE) deve
  passare a invocare questa fn invece di scrivere direttamente.
* Il BE deve mappare:
  * `E_OPERATORE_SCOPE_MULTI_NON_AMMESSO` → 400 con messaggio
    "Scope MULTI non ammesso".
  * `E_PROFILO_ULTIMO_SUPER_ADMIN` → 409 (o 400) con messaggio
    "Ultimo SUPER_ADMIN: cambio scope vietato".
  * (codice generico `22023`) → 400 con messaggio "ID non valido".

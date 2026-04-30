# fn_get_user_emittenti_scope

### Scopo

Vista dichiarativa dello **scope emittenti** per un singolo `auth_user`.
Risolve l'ambiguità single/multi/global che oggi nel drawer Operatore
(`OperatorePermessiTab`) viene dedotta a runtime contando le righe in
`config.user_emittenti_fiscali` (Fase 2 P1 2026-04-29).

Espone in modo coerente:

* lo **stato corrente** (`scope_mode`, `emittente_id`, `emittente_descrizione`)
* il **dominio dei valori ammessi** (`allowed_scope_modes`)
* la **capability di modifica** (`can_change_scope` + `change_scope_reason`)

> **Vedi anche**
>
> - [Architettura Multi-Face Auth](/guide/architettura-multi-face-auth)
> - [refactor operatore-emittenti — Fase 1](/dev/work-in-progress/refactor-operatore-emittenti) — vincolo `UNIQUE(auth_user_id)` di partenza
> - [fn_check_ultimo_super_admin_attivo](/dbzero/script/funzioni/fn_check_ultimo_super_admin_attivo) — primitiva di `can_change_scope`
> - [fn_change_user_emittenti_scope](/dbzero/script/funzioni/fn_change_user_emittenti_scope) — orchestrazione del cambio scope

## Schema

`script` (cross-dominio: legge `config.user_emittenti_fiscali` +
`anagrafiche.emittenti_fiscali` + chiama `script.fn_check_ultimo_super_admin_attivo`).

## Firma

```sql
script.fn_get_user_emittenti_scope(
    p_auth_user_id INTEGER
) RETURNS TABLE (...)
```

## Parametri

| Parametro | Tipo | Obbligatorio | Descrizione |
|---|---|:---:|---|
| `p_auth_user_id` | `INTEGER` | Sì | ID utente Django (`django.auth_user.id`). Tipo esplicito per la regola anti-pattern Liquibase/Django ordering. |

## Output

Tabella **a riga singola** (sempre 1 riga, anche se l'utente non ha mai
avuto associazioni emittente: in quel caso `scope_mode='GLOBAL'`).

| Colonna | Tipo | Significato |
|---|---|---|
| `auth_user_id` | `INTEGER` | Echo del parametro in input (utile per JOIN da query batch). |
| `scope_mode` | `TEXT` | `'GLOBAL'` o `'SINGLE'`. Il valore `'MULTI'` è chiuso applicativamente (vedi sotto). |
| `emittente_id` | `config.user_emittenti_fiscali.emittente_fiscale_id%TYPE` (`bigint`) | `NULL` se `scope_mode='GLOBAL'`, valorizzato se `'SINGLE'`. |
| `emittente_descrizione` | `TEXT` | `COALESCE(soggetti.ragione_sociale_completa, emittenti_fiscali.descrizione)`. Pre-aggregata per evitare N+1 al frontend. `NULL` se GLOBAL. |
| `allowed_scope_modes` | `TEXT[]` | Sempre `['GLOBAL','SINGLE']`. Tipo array `TEXT` per non vincolare il futuro (es. reintroduzione di MULTI). |
| `can_change_scope` | `BOOLEAN` | `false` sse l'utente è l'**ultimo** SUPER_ADMIN attivo del sistema. |
| `change_scope_reason` | `TEXT` | Motivo del blocco in `it-IT`, `NULL` se concesso. |

## Mappatura `scope_mode`

| Righe in `user_emittenti_fiscali` per `auth_user_id` | `scope_mode` |
|:---:|:---:|
| `0` | `GLOBAL` |
| `1` | `SINGLE` |
| `>1` | **impossibile** — `UNIQUE(auth_user_id)` introdotto in Fase 1 ([refactor 2026-04-08](/dev/work-in-progress/refactor-operatore-emittenti)) |

> **Perché non esporre `MULTI`** — il vincolo DB di Fase 1 garantisce
> che la fn vede al massimo 1 riga. Esporre `MULTI` come valore
> enumerato sarebbe codice morto. Il tipo `TEXT[]` di
> `allowed_scope_modes` mantiene aperto il futuro: se domani il vincolo
> cambia, la firma non cambia.

## Capability `can_change_scope`

Regola unica, allineata a Fase 1 (single source of truth):

```text
can_change_scope = NOT script.fn_check_ultimo_super_admin_attivo(p_auth_user_id)
```

| Stato utente | `can_change_scope` |
|---|:---:|
| Non SUPER_ADMIN | `true` |
| SUPER_ADMIN tra altri SA attivi | `true` |
| **Ultimo** SUPER_ADMIN attivo | `false` |

> Nota di design: la capability **non implementa** la regola "i SUPER_ADMIN
> globali devono restare GLOBAL" che era nel brief originale di Fase 2.
> Quel vincolo è stato **rifiutato** in fase di analisi: l'unico
> invariante che il sistema deve garantire è "esiste sempre un super-admin
> raggiungibile" — già coperto dal lockout-guard. Bloccare per dogma il
> cambio di scope di un SA non-ultimo non porta valore architetturale.

> Non considera il guard `is_active=true` di
> [`trgfn_user_emittenti_fiscali_guard_delete`](/dbzero/config/funzioni/trgfn_user_emittenti_fiscali_guard_delete):
> [`fn_change_user_emittenti_scope`](/dbzero/script/funzioni/fn_change_user_emittenti_scope)
> lo bypassa internamente con `SET LOCAL` per i flussi amministrativi.

## Caratteristiche

* `LANGUAGE sql STABLE` — read-only, **inlineable**, cache-friendly.
* Nessun riferimento a `django.*` → `LANGUAGE sql` ammesso.
* `LEFT JOIN` da una `(VALUES (p_auth_user_id))` base assicura **1 riga
  sempre**, anche in assenza di righe `user_emittenti_fiscali`.
* `emittente_descrizione` pre-aggregata via `COALESCE` (stesso pattern
  di [`fn_get_operatore_detail`](/dbzero/script/funzioni/fn_get_operatore_detail)).

## Tipi nel `RETURNS TABLE`

| Sorgente colonna | Tipo dichiarato | Ragione |
|---|---|---|
| `django.auth_user.id` (echo) | `INTEGER` esplicito | Anti-pattern Liquibase ordering |
| `config.user_emittenti_fiscali.emittente_fiscale_id` | **`%TYPE`** | Coerenza automatica, schema non-django |
| Tutto il resto | Esplicito | Computed (string_agg, capability) — nessuna colonna sorgente diretta |

## Dipendenze

### Tabelle

* `config.user_emittenti_fiscali`
* `anagrafiche.emittenti_fiscali`
* `anagrafiche.soggetti_ruoli`, `soggetti`

### Funzioni

* `script.fn_check_ultimo_super_admin_attivo(integer)` — primitiva capability

## Chi la chiama

* Drawer Operatore (BE service: lookup scope per auth_user_id).
* Lista operatori (potenziale colonna `scope_mode`).
* Test pgTAP: `db/pgtap/script/test-fn-get-user-emittenti-scope.sql`.

## Riferimenti

* WIP: [refactor operatore-emittenti](/dev/work-in-progress/refactor-operatore-emittenti) — Fase 2 capability scope
* Migration: `db/changelog/migrations_v2/20_code/script/20260429-03-create-fn-get-user-emittenti-scope-mctit.yaml`

## Esempio

```sql
-- Operatore non SA, senza assegnazione emittente
SELECT * FROM script.fn_get_user_emittenti_scope(42);
-- auth_user_id=42, scope_mode='GLOBAL', emittente_id=NULL, emittente_descrizione=NULL,
-- allowed_scope_modes=['GLOBAL','SINGLE'], can_change_scope=true, change_scope_reason=NULL

-- Operatore con emittente specifico
SELECT scope_mode, emittente_id, emittente_descrizione
  FROM script.fn_get_user_emittenti_scope(99);
-- 'SINGLE', 17, 'ACME S.R.L. - sede legale'

-- Ultimo SA attivo
SELECT can_change_scope, change_scope_reason
  FROM script.fn_get_user_emittenti_scope(7);
-- false, 'Ultimo SUPER_ADMIN attivo: il cambio scope è bloccato per evitare il lockout del sistema'
```

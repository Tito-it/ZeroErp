# trgfn_preventivi_default_emittente

### Scopo

Trigger function `BEFORE INSERT` su `vendite.preventivi` che valorizza automaticamente `emittente_fiscale_id` leggendo l'operatore loggato dalla GUC `app.current_user_id` (popolata dal middleware `JwtAuditAuthentication`) via `script.fn_resolve_emittente_for_user`.

Implementa il modello **user-derived** chiarito nella sessione 2026-05-01:

> L'emittente fiscale di un preventivo e' lo snapshot dell'emittente dell'**operatore creatore** della riga, non del BA del documento.

Skip se `NEW.emittente_fiscale_id` e' gia' valorizzato esplicitamente nel payload (caso ammesso per admin globale 1:N senza EF assegnato, o per chiamanti non-API che devono scegliere l'emittente).

## Schema

`vendite`

## Trigger associato

```sql
CREATE TRIGGER trg_preventivi_a10_default_emittente_ins
  BEFORE INSERT ON vendite.preventivi
  FOR EACH ROW
  EXECUTE FUNCTION vendite.trgfn_preventivi_default_emittente();
```

* **Fase**: `a10_default_*` (ordina alfabeticamente prima di `a10_guard_*` per firing order corretto)
* **Solo INSERT**: l'emittente e' immutabile post-create (vedi [automation_lock_columns](/dbzero/dbops/tabelle/automation_lock_columns) con codice `EMITTENTE_NON_MODIFICABILE`).

## Logica

1. Se `NEW.emittente_fiscale_id IS NOT NULL` → `RETURN NEW` (skip: payload esplicito).
2. Lettura GUC `app.current_user_id` con `current_setting(..., true)` (missing_ok). Se vuota o nulla → solleva `E_PREV_EMITTENTE_NON_RISOLTO`.
3. Cast a `integer` e chiamata a [`script.fn_resolve_emittente_for_user(v_user_id)`](/dbzero/script/funzioni/fn_resolve_emittente_for_user).
4. Se ritorna `NULL` (operatore admin globale senza riga in `config.user_emittenti_fiscali`) → solleva `E_PREV_EMITTENTE_NON_RISOLTO` con context `auth_user_id=...`.
5. Altrimenti → `NEW.emittente_fiscale_id := <risolto>` e `RETURN NEW`.

## Codice errore

| Codice                          | HTTP | Messaggio (CSV)                                                                                                  |
| ------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------- |
| `E_PREV_EMITTENTE_NON_RISOLTO`  | 400  | Operatore senza emittente fiscale assegnato: specificare emittente esplicitamente nel payload. %s                |

L'`%s` finale contiene il context diagnostico:

* GUC vuota: `'GUC vuota, numero=<numero>'`
* Admin globale: `'auth_user_id=<id>, numero=<numero>'`

## Contract GUC `app.current_user_id`

| Contesto chiamante                          | GUC | Comportamento                                  |
| ------------------------------------------- | --- | ---------------------------------------------- |
| Request API autenticata (`JwtAuditAuthentication`) | popolata sempre | Auto-fill standard via fn_resolve              |
| Admin globale (no riga in `user_emittenti_fiscali`) | popolata | Solleva: payload deve specificare emittente   |
| pgAgent job / Liquibase / DBA manuale       | vuota / unset | Solleva: caller deve specificare emittente    |

Per i contesti non-API che richiedono di inserire preventivi (es. seed dati di test, batch automatici), il chiamante DEVE valorizzare `NEW.emittente_fiscale_id` esplicitamente nel payload, oppure pre-impostare la GUC con `set_config('app.current_user_id', '<id>', true)` prima dell'INSERT.

## Caratteristiche

* **Skip esplicito**: il check `NEW.emittente_fiscale_id IS NOT NULL` permette al caller di overridare il default sempre (admin globale, batch).
* **Snapshot at INSERT**: il valore e' fissato al momento della creazione e non viene piu' aggiornato (lock_columns).
* **Idempotente nella creazione del trigger**: la migration usa `DROP TRIGGER IF EXISTS` + `CREATE TRIGGER` con `runOnChange: true`.

## Dipendenze

* GUC `app.current_user_id` (impostato dal middleware backend `JwtAuditAuthentication`)
* [`script.fn_resolve_emittente_for_user`](/dbzero/script/funzioni/fn_resolve_emittente_for_user)
* `script.fn_log_and_raise_error`
* Codice CSV `messaggi_errore.E_PREV_EMITTENTE_NON_RISOLTO`

## Lock columns

La colonna `vendite.preventivi.emittente_fiscale_id` e' protetta da `script.trgfn_lock_columns` via riga in `dbops.automation_lock_columns` (`error_code = EMITTENTE_NON_MODIFICABILE`). Tentativo di UPDATE solleva `EMITTENTE_NON_MODIFICABILE`. Per cambiare l'emittente di un preventivo esistente, usare [`fn_crea_revisione_preventivo`](/dbzero/vendite/funzioni/fn_crea_revisione_preventivo) (la nuova revisione nasce con l'emittente dell'operatore corrente).

## Vedi anche

* [`vendite.trgfn_preventivi_guard_utility_istanza_coerenza`](/dbzero/vendite/funzioni/trgfn_preventivi_guard_utility_istanza_coerenza) — guard fase `a10` che fires DOPO questo
* [`script.fn_resolve_emittente_for_user`](/dbzero/script/funzioni/fn_resolve_emittente_for_user) — resolver operatore↔emittente (1-a-1)
* [Tabella vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — sezione "Modello istanza/BA/emittente"
* Brief sessione 2026-05-01: `docs/it/dev/work-done/risposta-db-brief-preventivi-rev2.md`

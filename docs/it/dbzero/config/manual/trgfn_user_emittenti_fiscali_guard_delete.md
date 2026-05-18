# trgfn_user_emittenti_fiscali_guard_delete

### Scopo

Trigger function `BEFORE DELETE` su `config.user_emittenti_fiscali` che impone la regola del refactor 2026‑04‑08 (decisione D3 del [WIP](/dev/work-done/refactor-operatore-emittenti)): **l'associazione utente ↔ emittente può essere rimossa solo come parte della disattivazione dell'utente Django**.

Pattern: l'associazione operatore‑emittente è **immutabile**. Per "trasferire" un dipendente da un emittente A a un emittente B, l'admin disattiva l'utente esistente (cessazione tipica) e ne crea uno nuovo per l'altro emittente. Questo garantisce un audit trail naturale: ogni utente = una sola azienda, sempre.

## Schema

`config`

## Trigger associato

```sql
CREATE TRIGGER trg_user_emittenti_fiscali_a10_guard_delete_dlt
BEFORE DELETE ON config.user_emittenti_fiscali
FOR EACH ROW
EXECUTE FUNCTION config.trgfn_user_emittenti_fiscali_guard_delete();
```

* **Fase**: `a10` (guard precoce, prima del trigger di storicizzazione `z90`).

## Logica

1. **Override manutenzione**: se `current_setting('zeroerp.allow_user_emittente_delete_override', true) = 'on'`, il trigger consente la DELETE senza altri controlli (`RETURN OLD`).
2. Lookup di `django.auth_user.is_active` per `OLD.auth_user_id`.
3. Se l'utente Django **non esiste** (caso "DELETE in cascata da utente"): consenti DELETE — la cessazione è implicita.
4. Se l'utente è **ancora attivo** (`is_active = true`): solleva `E_USER_EMITTENTE_DELETE_VIETATO`.
5. Altrimenti (utente disattivato): consenti DELETE.

## Codice errore

| Codice                              | HTTP | Messaggio                                                                                                       |
| ----------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------- |
| `E_USER_EMITTENTE_DELETE_VIETATO`   | 400  | Eliminazione vietata: l'associazione utente‑emittente può essere rimossa solo come parte della disattivazione utente. |

## Override manutenzione

Per cleanup manuali autorizzati (es. correzione di righe inserite per errore):

```sql
BEGIN;
SET LOCAL zeroerp.allow_user_emittente_delete_override = 'on';
DELETE FROM config.user_emittenti_fiscali WHERE id = ...;
COMMIT;
```

L'override è **transazione‑locale** (`SET LOCAL`) e non viene mai propagato fuori dalla transazione.

## Caratteristiche

* **Single‑purpose**: si occupa solo del check su `is_active`. Tutta la logica di storicizzazione resta affidata al trigger separato `trg_user_emittenti_fiscali_z90_storico_upd_dlt`.
* **Lookup difensivo**: `is_active IS NULL` (utente già cancellato) consente la DELETE in cascata invece di fallire.

## Dipendenze

* `django.auth_user` — campo `is_active`
* `script.fn_log_and_raise_error`

## Vedi anche

* [`config.user_emittenti_fiscali`](/dbzero/config/tabelle/user_emittenti_fiscali) — tabella protetta
* `script.trgfn_lock_columns` — trigger gemello che impedisce la **modifica** di `emittente_fiscale_id` (vedi `trg_user_emittenti_fiscali_a10_lock_emittente_upd`)
* [Refactor operatore ↔ emittente §D3](/dev/work-done/refactor-operatore-emittenti)

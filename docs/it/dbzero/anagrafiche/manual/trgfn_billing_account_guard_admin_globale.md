# trgfn_billing_account_guard_admin_globale

### Scopo

Trigger function `BEFORE INSERT` su `anagrafiche.billing_account` che applica la regola del refactor 2026‑04‑08 (decisione Q6 del [WIP](/dev/work-in-progress/refactor-operatore-emittenti)): **gli admin globali non possono creare billing account quando esistono emittenti fiscali nel sistema**.

Pattern: defense‑in‑depth a livello DB. Anche se il backend prevede un check applicativo, il guard DB garantisce l'invarianza in caso di bypass o bug.

## Schema

`anagrafiche`

## Trigger associato

```sql
CREATE TRIGGER trg_billing_account_a10_guard_admin_globale_ins
BEFORE INSERT ON anagrafiche.billing_account
FOR EACH ROW
EXECUTE FUNCTION anagrafiche.trgfn_billing_account_guard_admin_globale();
```

* **Fase**: `a10` (guard precoce, prima dei guard di normalizzazione)
* **Ordine**: dopo `trg_billing_account_a10_gen_codice_ins_upd` (così `NEW.codice` è già popolato per il messaggio di errore), prima di `audit`, `tx_id`, `guard_normalize`.

## Logica

1. Lettura GUC `app.current_user_id` (settato dal middleware Django `JwtAuditMiddleware` per ogni request autenticata).
2. Se il GUC è `NULL` o stringa vuota → `RETURN NEW` (fail‑open mirato per seed/bootstrap/job CLI senza utente).
3. Chiamata a [`script.fn_check_user_can_create_ba(v_user_id)`](/dbzero/script/funzioni/fn_check_user_can_create_ba).
4. Se il check ritorna `false` → solleva `E_BA_ADMIN_GLOBALE_VIETATO` tramite `script.fn_log_and_raise_error`.
5. Altrimenti → `RETURN NEW`.

## Codice errore

| Codice                       | HTTP | Messaggio                                                                                                                            |
| ---------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `E_BA_ADMIN_GLOBALE_VIETATO` | 403  | Un amministratore globale non può creare billing account quando esistono emittenti fiscali. Operare come operatore di un emittente.  |

## Caratteristiche

* **Fail‑open in assenza di GUC**: pensato per non rompere seed Liquibase, comandi `manage.py`, job pgagent. Il guard è attivo solo per le richieste autenticate via Django.
* **Idempotente nella creazione del trigger**: la migration usa `DROP TRIGGER IF EXISTS` + `CREATE TRIGGER` con `runOnChange: true`.

## Dipendenze

* GUC `app.current_user_id` (impostato dal middleware backend)
* [`script.fn_check_user_can_create_ba`](/dbzero/script/funzioni/fn_check_user_can_create_ba)
* `script.fn_log_and_raise_error`

## Override / disattivazione

Non previsto un override esplicito (es. GUC `allow_admin_globale_create_ba`). Per intervenire manualmente su un BA in casi eccezionali, l'admin deve operare come operatore di emittente o disabilitare temporaneamente il trigger via `ALTER TABLE ... DISABLE TRIGGER ...` (operazione di manutenzione, da tracciare).

## Vedi anche

* [`anagrafiche.trgfn_billing_account_link_ef`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — gemello `AFTER INSERT` che esegue l'auto‑link.
* [Refactor operatore ↔ emittente](/dev/work-in-progress/refactor-operatore-emittenti)

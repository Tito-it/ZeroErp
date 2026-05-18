# trgfn_billing_account_link_ef

### Scopo

Trigger function `AFTER INSERT` su `anagrafiche.billing_account` che, dopo la creazione di un BA, **collega automaticamente** il BA all'emittente fiscale dell'operatore corrente, popolando `anagrafiche.emittenti_fiscali_billing_account` con un mapping specifico.

Introdotto dal refactor del 2026‑04‑08 (sezione 2.4 del [WIP](/dev/work-done/refactor-operatore-emittenti)) per rendere deterministico e immediato il legame BA → emittente, eliminando la dipendenza dal "default globale" come meccanismo principale (che resta come **rete di sicurezza**).

## Schema

`anagrafiche`

## Trigger associato

```sql
CREATE TRIGGER trg_billing_account_z90_link_ef_ins
AFTER INSERT ON anagrafiche.billing_account
FOR EACH ROW
EXECUTE FUNCTION anagrafiche.trgfn_billing_account_link_ef();
```

* **Fase**: `z90` (final / post‑insert)
* **Eseguito dopo** tutti i guard `BEFORE` e dopo che la riga è stata effettivamente scritta.

## Logica

1. Lettura GUC `app.current_user_id` (settato dal middleware Django).
2. Se NULL o stringa vuota → `RETURN NEW` (skip seed/bootstrap).
3. Chiama [`script.fn_resolve_emittente_for_user(v_user_id)`](/dbzero/script/funzioni/fn_resolve_emittente_for_user) → ritorna PK reale `emittenti_fiscali.id` o NULL.
4. Se NULL (admin globale o "0 emittenti") → `RETURN NEW`. Nota: il caso "admin globale + esistono emittenti" è già stato bloccato in fase `BEFORE INSERT` da [`trgfn_billing_account_guard_admin_globale`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale).
5. Conversione PK → `soggetto_ruolo_id` (la tabella di mapping `emittenti_fiscali_billing_account` usa `emittente_soggetto_ruolo_id`, non la PK reale).
6. **Idempotenza**: se esiste già un mapping per `NEW.id` → `RETURN NEW` senza fare nulla. (Difensivo: `uq_emittenti_fiscali_ba` lo impedirebbe comunque, ma il check esplicito evita errori di unicità in scenari di race.)
7. INSERT in `emittenti_fiscali_billing_account` con `(billing_account_id, emittente_soggetto_ruolo_id, is_default = false)` — mapping specifico, non default globale.

## Comportamento per scenario

| Scenario                                                       | Comportamento                                                                |
| -------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Operatore o admin di emittente crea BA via app                 | Mapping specifico creato verso il proprio EF                                 |
| Admin globale crea BA con emittenti presenti                   | Bloccato in `BEFORE` (mai si arriva qui)                                     |
| Seed Liquibase / manage.py / pgagent senza GUC                 | Nessun mapping creato (skip fail‑open)                                       |
| Istanza single‑tenant senza emittenti                          | Nessun mapping creato (resolver = NULL, gestore = emittente)                 |
| Riga di mapping già presente per quel BA                       | Skip idempotente                                                             |

## Caratteristiche

* **Idempotente**.
* **Fail‑open in assenza di GUC** (pari al guard gemello).
* Crea **solo mapping specifici** (`is_default = false`). La riga di default globale (`billing_account_id IS NULL`, `is_default = true`) **non viene mai toccata** dal trigger.

## Dipendenze

* GUC `app.current_user_id`
* [`script.fn_resolve_emittente_for_user`](/dbzero/script/funzioni/fn_resolve_emittente_for_user)
* `anagrafiche.emittenti_fiscali` — lookup `soggetto_ruolo_id` da PK
* `anagrafiche.emittenti_fiscali_billing_account` — destinazione INSERT

## Vedi anche

* [`anagrafiche.trgfn_billing_account_guard_admin_globale`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale) — gemello `BEFORE INSERT`
* [`anagrafiche.emittenti_fiscali_billing_account`](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account) — tabella di mapping
* [Refactor operatore ↔ emittente](/dev/work-done/refactor-operatore-emittenti)

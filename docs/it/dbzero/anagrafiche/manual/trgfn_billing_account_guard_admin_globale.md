# trgfn_billing_account_guard_admin_globale

### Scopo

Trigger function `BEFORE INSERT` su `anagrafiche.billing_account`: **un billing account si crea solo avendo un emittente fiscale su cui scriverlo**. Se nel sistema esistono emittenti attivi, l'utente deve appartenere a un emittente (riga in `config.user_emittenti_fiscali`) **oppure** lavorare dentro un emittente del suo perimetro (`app.current_emittente_id`, la combo in alto). Chi non ha né l'uno né l'altro — tipicamente il super admin in «Tutti gli emittenti» — viene rifiutato: non si saprebbe a quale emittente associare il nuovo cliente.

Nata col refactor 2026‑04‑08 (decisione Q6 del [WIP](/dev/work-done/refactor-operatore-emittenti)) come «gli admin globali non creano billing account»; dalla rev 2026‑08‑04 di [`script.fn_check_user_can_create_ba`](/dbzero/script/funzioni/fn_check_user_can_create_ba) il super admin **dentro** un emittente può creare. Il nome della funzione e del codice (`…ADMIN_GLOBALE…`) resta per non rompere i riferimenti del backend.

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
4. Se il check ritorna `false` (nessun emittente su cui scrivere, ed esistono emittenti attivi) → solleva `E_BA_ADMIN_GLOBALE_VIETATO` tramite `script.fn_log_and_raise_error`.
5. Altrimenti → `RETURN NEW`.

## Codice errore

| Codice                       | HTTP | Messaggio |
| ---------------------------- | ---- | --------- |
| `E_BA_ADMIN_GLOBALE_VIETATO` | 403  | Per creare un cliente serve un emittente fiscale su cui lavorare: scegli l'emittente in alto (con «Tutti gli emittenti» non si sa a quale associarlo). |

Il testo vive nel catalogo `config.messaggi_errore` (id 358): la tabella qui sopra è una copia di comodo.

## Caratteristiche

* **Fail‑open in assenza di GUC**: pensato per non rompere seed Liquibase, comandi `manage.py`, job pgagent. Il guard è attivo solo per le richieste autenticate via Django.
* **Idempotente nella creazione del trigger**: la migration di nascita usa `DROP TRIGGER IF EXISTS` + `CREATE TRIGGER`.

## Dipendenze

* GUC `app.current_user_id` (impostato dal middleware backend)
* [`script.fn_check_user_can_create_ba`](/dbzero/script/funzioni/fn_check_user_can_create_ba)
* `script.fn_log_and_raise_error`

## Override / disattivazione

Non previsto un override esplicito (es. GUC `allow_admin_globale_create_ba`), e non serve: il super admin sceglie l'emittente di lavoro dalla combo in alto e crea.

## Vedi anche

* [`anagrafiche.trgfn_billing_account_link_ef`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) — gemello `AFTER INSERT` che esegue l'auto‑link.
* [Refactor operatore ↔ emittente](/dev/work-done/refactor-operatore-emittenti)

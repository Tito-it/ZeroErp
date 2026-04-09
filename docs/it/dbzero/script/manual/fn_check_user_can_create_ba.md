# fn_check_user_can_create_ba

### Scopo

Pure check (boolean, no raise) usato dal trigger guard `BEFORE INSERT` su `anagrafiche.billing_account` per applicare la regola del refactor 2026‑04‑08: **gli admin globali non possono creare billing account quando esistono emittenti fiscali nel sistema**.

Convenzione `fn_check_*`: nessun raise, solo `boolean`. Il sollevamento dell'errore è delegato al trigger guard chiamante ([`trgfn_billing_account_guard_admin_globale`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale)).

## Schema

`script` (cross‑dominio).

## Firma

```sql
script.fn_check_user_can_create_ba(
    p_auth_user_id integer
) RETURNS boolean
```

## Parametri

| Parametro        | Tipo      | Obbligatorio | Descrizione                                      |
| ---------------- | --------- | :----------: | ------------------------------------------------ |
| `p_auth_user_id` | `integer` |      Si      | ID utente Django (`django.auth_user.id`).        |

## Regole di valutazione

| Caso                                                                            | Ritorno |
| ------------------------------------------------------------------------------- | :-----: |
| Utente con riga in `config.user_emittenti_fiscali` (operatore o admin di EF)    | `true`  |
| Utente senza riga, **nessun emittente attivo** nel sistema (gestore = emittente)| `true`  |
| Utente senza riga, esistono emittenti attivi (admin globale)                    | `false` |
| `p_auth_user_id` NULL o `<= 0`                                                  | `false` (no raise — pure check) |

## Caratteristiche

* **STABLE**: solo lettura.
* **No raise**: in caso di parametro invalido ritorna `false` invece di sollevare. Il guard chiamante decide se questo debba bloccare l'INSERT (e di norma sì, perché un BA inserito senza utente identificato è anomalo, ma il guard ha già la logica di "fail‑open in seed" tramite check sul GUC).
* **Coerente con `fn_resolve_emittente_for_user`**: entrambe valutano "esiste riga in user_emittenti_fiscali?" senza filtri ulteriori su `ef.attivo` (per costruzione l'EF associato è sempre attivo, vedi note sull'altra funzione).

## Dipendenze

* `config.user_emittenti_fiscali` — esistenza dell'associazione
* `anagrafiche.emittenti_fiscali` — conteggio EF attivi (caso "0 emittenti")

## Chi la chiama

* [`anagrafiche.trgfn_billing_account_guard_admin_globale`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale) — guard `BEFORE INSERT` su `billing_account`

## Esempio

```sql
-- Operatore con emittente assegnato
SELECT script.fn_check_user_can_create_ba(42);
-- true

-- Admin globale, sistema con emittenti
SELECT script.fn_check_user_can_create_ba(1);
-- false  (vietato)

-- Istanza single-tenant senza emittenti fiscali
-- (qualunque utente attivo)
SELECT script.fn_check_user_can_create_ba(1);
-- true   (gestore = emittente, regola sospesa)
```

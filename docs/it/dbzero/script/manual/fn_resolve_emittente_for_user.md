# fn_resolve_emittente_for_user

### Scopo

Resolver "emittente fiscale di un utente" nel modello operatore ↔ emittente **1‑a‑1** introdotto dal refactor del 2026‑04‑08. Restituisce la PK reale dell'emittente fiscale associato a un `auth_user`, oppure NULL se l'utente non ha alcuna associazione (admin globale o istanza con 0 emittenti).

Funzione **resolver pura**: non solleva eccezioni in caso di NULL — è il chiamante che decide la semantica.

## Schema

`script` (funzione cross‑dominio: legge `config.user_emittenti_fiscali` + `anagrafiche.emittenti_fiscali`).

> Collocazione coerente con il refactor permessi del 2026‑03‑08 che ha spostato i resolver di permessi cross‑dominio da `config` a `script`.

## Firma

```sql
script.fn_resolve_emittente_for_user(
    p_auth_user_id integer
) RETURNS anagrafiche.emittenti_fiscali.id%TYPE
```

## Parametri

| Parametro        | Tipo      | Obbligatorio | Descrizione                                                  |
| ---------------- | --------- | :----------: | ------------------------------------------------------------ |
| `p_auth_user_id` | `integer` |      Si      | ID utente Django (`django.auth_user.id`). Deve essere `> 0`. |

## Comportamento

| Caso                                                                | Ritorno                |
| ------------------------------------------------------------------- | ---------------------- |
| Utente con 1 riga in `config.user_emittenti_fiscali`                | `emittente_fiscale_id` |
| Utente senza riga (admin globale)                                   | `NULL`                 |
| Utente inesistente                                                  | `NULL`                 |
| Istanza "0 emittenti" (gestore = emittente)                         | `NULL`                 |
| `p_auth_user_id` NULL o `<= 0`                                      | solleva `E_PARAMETRO_INVALIDO` |

## Caratteristiche

* **STABLE**: solo lettura, non modifica dati.
* **Modello 1‑a‑1**: il vincolo `UNIQUE(auth_user_id)` su `config.user_emittenti_fiscali` (refactor 2026‑04‑08) garantisce al massimo una riga per utente.
* **Nessun filtro su `ef.attivo`**: per costruzione l'EF associato a un utente è sempre attivo. La protezione è data dai trigger di guardia su entrambi i lati:
  * `dbops.trgfn_child_requires_active_parent` su `user_emittenti_fiscali` blocca INSERT/UPDATE su EF non attivo.
  * `dbops.trgfn_prevent_deactivate_if_children` su `emittenti_fiscali` blocca la disattivazione di un EF con righe figlie in `user_emittenti_fiscali`.
* Aggiungere il filtro qui creerebbe **incoerenza** con [`script.fn_check_user_can_create_ba`](/dbzero/script/funzioni/fn_check_user_can_create_ba) (che non filtra).

## Restituisce sempre la PK reale

Convenzione: ritorna `anagrafiche.emittenti_fiscali.id` (PK numerica reale), **non** `soggetto_ruolo_id`. Il chiamante che ha bisogno del `soggetto_ruolo_id` (es. tabelle di mapping `emittenti_fiscali_billing_account`, `emittenti_fiscali_utilities`) deve fare lookup su `emittenti_fiscali`.

## Dipendenze

* `config.user_emittenti_fiscali` — associazione operatore‑emittente
* `anagrafiche.emittenti_fiscali` — non utilizzata direttamente, ma il dominio FK garantisce la coerenza referenziale

## Chi la chiama

* `anagrafiche.trgfn_billing_account_link_ef` — auto‑link BA → emittente alla creazione
* Backend Python: wrapper `PermissionResolver.get_emittente_for_user(user)` (vedi [refactor WIP §5.2](/dev/work-in-progress/refactor-operatore-emittenti))

## Esempio

```sql
-- Operatore con emittente assegnato
SELECT script.fn_resolve_emittente_for_user(42);
-- 7  (PK dell'emittente)

-- Admin globale (nessuna riga in user_emittenti_fiscali)
SELECT script.fn_resolve_emittente_for_user(1);
-- NULL

-- Parametro invalido
SELECT script.fn_resolve_emittente_for_user(NULL);
-- ERROR: E_PARAMETRO_INVALIDO
```

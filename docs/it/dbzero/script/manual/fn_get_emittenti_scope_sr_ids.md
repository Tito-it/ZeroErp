## Documentazione Concettuale – Funzione `script.fn_get_emittenti_scope_sr_ids`

> ⚠️ **Refactor 2026-05-02**: la fn e' diventata un **wrapper thin** su [`script.fn_get_emittenti_scope_pk_ids`](/dbzero/script/funzioni/fn_get_emittenti_scope_pk_ids) (single source of truth dei guard, zero drift). Firma e semantica invariate per i caller esistenti. Vedi [guida soggetti-e-ruoli §5b](/it/guide/soggetti-e-ruoli-anagrafici#5b-identificazione-canonica-di-un-ruolo-specializzato--pk-reale-vs-soggetto_ruolo_id) per la decisione "quando usare _sr_ids vs _pk_ids".
>
> **Vedi anche**
>
**Tabelle correlate:**
>
[config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
> [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
**Funzioni correlate:**
>
[script.fn_get_emittenti_scope_pk_ids](/dbzero/script/funzioni/fn_get_emittenti_scope_pk_ids) — **canonica** (questa e' wrapper)
> [script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin)
> [script.fn_has_identita_attiva](/dbzero/script/funzioni/fn_has_identita_attiva)
> [script.fn_resolve_emittente_for_user](/dbzero/script/funzioni/fn_resolve_emittente_for_user)

---
### 🎯 Scopo Principale
(latest review 02-05-2026 — wrapper su `_pk_ids`)

La funzione **`script.fn_get_emittenti_scope_sr_ids`** restituisce i `soggetto_ruolo_id`
degli emittenti fiscali autorizzati per un utente.

Da usare quando il filtro va su una colonna che contiene **SR id** (es. tabelle dei
documenti contrattuali: `vendite.fatture.emittente_soggetto_ruolo_id`,
`vendite.commesse.emittente_soggetto_ruolo_id`, `vendite.listini.emittente_soggetto_ruolo_id`,
`anagrafiche.emittenti_fiscali_billing_account.emittente_soggetto_ruolo_id`, ecc.).

Per filtri su colonne **PK reale** (es. `vw_preventivi_list.emittente_fiscale_id`,
`config.parameter_overrides.emittente_fiscale_id`, `vendite.preventivi.emittente_fiscale_id`)
usare invece [`fn_get_emittenti_scope_pk_ids`](/dbzero/script/funzioni/fn_get_emittenti_scope_pk_ids).

#### Implementazione

Dal refactor 2026-05-02, la fn e' un **wrapper thin**:

1. Delega tutti i guard alla canonica `fn_get_emittenti_scope_pk_ids` (no identita' OPERATORE → `'{}'`; super admin → `NULL`; whitelist PK altrimenti)
2. Pass-through dei sentinel `NULL` e `'{}'`
3. Mappa l'array PK → SR id via JOIN su `anagrafiche.emittenti_fiscali`

Vantaggio: single source of truth dei guard, zero drift tra le due fn gemelle.

---

### Parametri di input

| Parametro        | Tipo                                                    | Descrizione            |
| ---------------- | ------------------------------------------------------- | ---------------------- |
| `p_auth_user_id` | `anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE` | ID dell'utente Django. |

---

### Output

Ritorna `bigint[]`:

| Caso                           | Ritorno          | Effetto sul WHERE      |
| ------------------------------ | ---------------- | ---------------------- |
| ADMIN                          | `NULL`           | Nessun filtro          |
| OPERATIVO senza whitelist      | `NULL`           | Nessun filtro          |
| OPERATIVO con whitelist [A, B] | `{srA, srB}`     | `= ANY(array)`         |
| DISABILITATO / senza bridge    | `'{}'::bigint[]` | Nessun match → 0 righe |

---

### Regole principali

* Funzione **STABLE**.
* A differenza di `fn_get_emittenti_scope` (che ritorna `emittente_fiscale_id`),
  questa mappa a `soggetto_ruolo_id` via JOIN su `anagrafiche.emittenti_fiscali`.
* Usata dal backend `VenditeRepository` per filtrare lotti e fatture per emittente.
* DISABILITATO/senza bridge ritorna array vuoto (non NULL) per garantire 0 risultati.

---

### Esempio d'uso

```sql
-- Nella clausola WHERE di una query vendite:
WHERE (script.fn_get_emittenti_scope_sr_ids(42) IS NULL
   OR fl.emittente_soggetto_ruolo_id = ANY(
      script.fn_get_emittenti_scope_sr_ids(42)))
```

---

{% include-markdown "signature-core.md" %}

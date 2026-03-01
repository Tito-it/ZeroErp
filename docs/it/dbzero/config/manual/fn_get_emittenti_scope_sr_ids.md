## Documentazione Concettuale – Funzione `config.fn_get_emittenti_scope_sr_ids`

> **Vedi anche**
>
> **Tabelle correlate:**
>
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>
> **Funzioni correlate:**
>
> * [config.fn_get_ruolo_sistema](/dbzero/config/funzioni/fn_get_ruolo_sistema)
> * [config.fn_get_emittenti_scope](/dbzero/config/funzioni/fn_get_emittenti_scope)

---

### Scopo Principale

(latest review 01-03-2026)
La funzione **`config.fn_get_emittenti_scope_sr_ids`** restituisce i `soggetto_ruolo_id`
degli emittenti fiscali autorizzati per un utente.

Le tabelle vendite usano `emittente_soggetto_ruolo_id` (FK a `anagrafiche.soggetti_ruoli`),
non `emittente_fiscale_id`, quindi serve questa mappatura aggiuntiva rispetto a
`fn_get_emittenti_scope`.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
| --------- | ---- | ----------- |
| `p_auth_user_id` | integer | ID dell'utente Django. |

---

### Output

Ritorna `bigint[]`:

| Caso | Ritorno | Effetto sul WHERE |
| ---- | ------- | ----------------- |
| ADMIN | `NULL` | Nessun filtro |
| OPERATIVO senza whitelist | `NULL` | Nessun filtro |
| OPERATIVO con whitelist [A, B] | `{srA, srB}` | `= ANY(array)` |
| DISABILITATO / senza bridge | `'{}'::bigint[]` | Nessun match → 0 righe |

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
WHERE (config.fn_get_emittenti_scope_sr_ids(42) IS NULL
   OR fl.emittente_soggetto_ruolo_id = ANY(
      config.fn_get_emittenti_scope_sr_ids(42)))
```

---

{% include-markdown "signature-core.md" %}

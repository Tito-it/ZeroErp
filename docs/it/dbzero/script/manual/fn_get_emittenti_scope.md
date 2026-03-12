## Documentazione Concettuale – Funzione `script.fn_get_emittenti_scope`

> **Vedi anche**
>
> **Tabelle correlate:**
>
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
> **Funzioni correlate:**
>
> * [script.fn_check_user_emittente_scope](/dbzero/script/funzioni/fn_check_user_emittente_scope)

---

### 🎯 Scopo Principale

(latest review 08-03-2026)
La funzione **`script.fn_get_emittenti_scope`** restituisce l'array di ID emittenti
fiscali autorizzati per un utente, letti dalla whitelist `config.user_emittenti_fiscali`.

---

### Parametri di input

| Parametro        | Tipo                                                    | Descrizione            |
| ---------------- | ------------------------------------------------------- | ---------------------- |
| `p_auth_user_id` | `anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE` | ID dell'utente Django. |

---

### Output

Ritorna `bigint[]`:

* **`NULL`** = nessuna restrizione (whitelist vuota, l'utente vede tutti gli emittenti)
* **array di ID** = l'utente e limitato agli emittenti elencati

---

### Regole principali

* Funzione **STABLE**.
* Usa `array_agg()` che ritorna `NULL` quando non ci sono righe (semantica whitelist vuota = accesso completo).
* Pensata per essere usata dal backend Django per filtrare query su fatture, ordini,
  pagamenti in base all'emittente.

---

### Esempio d'uso

```sql
-- Utente con whitelist
SELECT script.fn_get_emittenti_scope(42);
-- Ritorna: '{1,3}'::bigint[]

-- Utente senza whitelist
SELECT script.fn_get_emittenti_scope(99);
-- Ritorna: NULL (nessuna restrizione)
```

---

{% include-markdown "signature-core.md" %}

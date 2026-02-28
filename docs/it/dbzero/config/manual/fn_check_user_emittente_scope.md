## Documentazione Concettuale – Funzione `config.fn_check_user_emittente_scope`

> **Vedi anche**
>
> **Tabelle correlate:**
>
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
> **Funzioni correlate:**
>
> * [config.fn_get_ruolo_sistema](/dbzero/config/funzioni/fn_get_ruolo_sistema)
> * [config.fn_get_emittenti_scope](/dbzero/config/funzioni/fn_get_emittenti_scope)
> * [config.trgfn_guard_emittente_scope](/dbzero/config/funzioni/trgfn_guard_emittente_scope)

---

### Scopo Principale

(latest review 28-02-2026)
La funzione **`config.fn_check_user_emittente_scope`** verifica se un utente ha
accesso a uno specifico emittente fiscale. Pensata per i trigger defense-in-depth
su tabelle operative (fatture, pagamenti).

Funzione `fn_check_*`: puro boolean, no RAISE.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
| --------- | ---- | ----------- |
| `p_auth_user_id` | integer | ID utente Django (o `NULL` per job batch). |
| `p_emittente_fiscale_id` | bigint | ID emittente fiscale da verificare. |

---

### Output

Ritorna `boolean`.

---

### Regole di risoluzione

1. **`p_auth_user_id` NULL** → `true` (job batch, nessun filtro utente)
2. **ADMIN** → `true` (accesso completo a tutti gli emittenti)
3. **Whitelist vuota** (nessuna riga in `user_emittenti_fiscali`) → `true` (nessuna restrizione)
4. **Whitelist con righe** → `true` solo se l'emittente e presente nella whitelist

---

### Regole principali

* Funzione **STABLE**.
* Chiamata internamente da `trgfn_guard_emittente_scope` per i trigger defense-in-depth.
* Puo essere chiamata direttamente dal backend per controlli preventivi.

---

### Esempio d'uso

```sql
-- Job batch (nessun utente)
SELECT config.fn_check_user_emittente_scope(NULL, 1);
-- Ritorna: true

-- ADMIN
SELECT config.fn_check_user_emittente_scope(42, 1);
-- Ritorna: true (se ruolo = ADMIN)

-- OPERATIVO con whitelist
SELECT config.fn_check_user_emittente_scope(42, 99);
-- Ritorna: false (se 99 non e nella whitelist)
```

---

{% include-markdown "signature-core.md" %}

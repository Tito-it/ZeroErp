## Documentazione Concettuale – Funzione `script.fn_check_user_emittente_scope`

> **Vedi anche**
>
> **Tabelle correlate:**
>
> * [config.user_emittenti_fiscali](/dbzero/config/tabelle/user_emittenti_fiscali)
> * [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
>
> **Funzioni correlate:**
>
> * [script.fn_get_ruolo_sistema](/dbzero/script/funzioni/fn_get_ruolo_sistema)
> * [script.fn_get_emittenti_scope](/dbzero/script/funzioni/fn_get_emittenti_scope)
> * [script.trgfn_guard_emittente_scope](/dbzero/script/funzioni/trgfn_guard_emittente_scope)

---

### Scopo Principale

(latest review 08-03-2026)
La funzione **`script.fn_check_user_emittente_scope`** verifica se un utente ha
accesso a uno specifico emittente fiscale. Pensata per i trigger defense-in-depth
su tabelle operative (fatture, pagamenti).

Funzione `fn_check_*`: puro boolean, no RAISE.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
| --------- | ---- | ----------- |
| `p_auth_user_id` | `anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE` | ID utente Django (o `NULL` per job batch). |
| `p_emittente_fiscale_id` | `anagrafiche.emittenti_fiscali.id%TYPE` | ID emittente fiscale da verificare. |

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
SELECT script.fn_check_user_emittente_scope(NULL, 1);
-- Ritorna: true

-- ADMIN
SELECT script.fn_check_user_emittente_scope(42, 1);
-- Ritorna: true (se ruolo = ADMIN)

-- OPERATIVO con whitelist
SELECT script.fn_check_user_emittente_scope(42, 99);
-- Ritorna: false (se 99 non e nella whitelist)
```

---

{% include-markdown "signature-core.md" %}

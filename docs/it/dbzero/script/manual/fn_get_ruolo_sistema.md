## Documentazione Concettuale – Funzione `script.fn_get_ruolo_sistema`

> **Vedi anche**
>
**Tabelle correlate:**
>
[anagrafiche.risorse_umane_auth_user](/dbzero/anagrafiche/tabelle/risorse_umane_auth_user)

---
### 🎯 Scopo Principale
(latest review 08-03-2026)
La funzione **`script.fn_get_ruolo_sistema`** restituisce il `ruolo_sistema`
(`ADMIN`, `OPERATIVO`, `DISABILITATO`) di un utente dalla tabella ponte
`anagrafiche.risorse_umane_auth_user`.

Ritorna `NULL` se l'utente non ha record ponte (utente non mappato a risorsa umana).

---

### Parametri di input

| Parametro        | Tipo                                                    | Descrizione                             |
| ---------------- | ------------------------------------------------------- | --------------------------------------- |
| `p_auth_user_id` | `anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE` | ID dell'utente Django (`auth_user.id`). |

---

### Output

Ritorna `config.ruolo_sistema` (ENUM) oppure `NULL`.

---

### Regole principali

* Funzione **STABLE** (nessun side-effect).
* Blocco base riusato da tutte le funzioni di risoluzione permessi:
  `fn_resolve_livello_area`, `fn_resolve_livello_oggetto`,
  `fn_check_azione_processo`, `fn_check_user_emittente_scope`.
* Un singolo `SELECT INTO` sulla tabella ponte; nessun fallback o default.

---

### Esempio d'uso

```sql
SELECT script.fn_get_ruolo_sistema(42);
-- Ritorna: 'OPERATIVO'::config.ruolo_sistema (o NULL se non mappato)
```

---

{% include-markdown "signature-core.md" %}

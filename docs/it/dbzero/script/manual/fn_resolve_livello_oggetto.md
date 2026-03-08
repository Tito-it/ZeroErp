## Documentazione Concettuale – Funzione `script.fn_resolve_livello_oggetto`

> **Vedi anche**
>
> **Tabelle correlate:**
>
> * [config.user_override_oggetti](/dbzero/config/tabelle/user_override_oggetti)
> * [config.area_model_overrides](/dbzero/config/tabelle/area_model_overrides)
>
> **Funzioni correlate:**
>
> * [script.fn_resolve_livello_area](/dbzero/script/funzioni/fn_resolve_livello_area)
> * [script.fn_get_ruolo_sistema](/dbzero/script/funzioni/fn_get_ruolo_sistema)

---

### Scopo Principale

(latest review 08-03-2026)
La funzione **`script.fn_resolve_livello_oggetto`** risolve il livello di accesso
per un singolo model Django (`app_label` + `model_name`).

Se esiste un override oggetto lo usa; altrimenti risale alla catena area
via `fn_resolve_livello_area`.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
| --------- | ---- | ----------- |
| `p_auth_user_id` | `anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE` | ID dell'utente Django. |
| `p_app_label` | `config.user_override_oggetti.app_label%TYPE` | App Django (es. `'vendite'`). |
| `p_model_name` | `config.user_override_oggetti.model_name%TYPE` | Nome model Django (es. `'fatture'`). |
| `p_area_schema_db` | `config.aree_funzionali.schema_db%TYPE` | Schema DB dell'area, usato per fallback. |

---

### Output

Ritorna `config.livello_accesso` (ENUM): `TUTTO`, `LETTURA` o `BLOCCATO`.

---

### Catena di risoluzione

1. **Ruolo sistema** — `NULL`/`DISABILITATO` → `BLOCCATO`; `ADMIN` → `TUTTO`
2. **Override utente oggetto** — se presente e temporalmente valido
3. **Fallback** → `fn_resolve_livello_area(p_auth_user_id, p_area_schema_db)`

---

### Regole principali

* Funzione **STABLE**.
* L'override oggetto ha precedenza sull'area: consente di dare accesso
  granulare a un singolo model indipendentemente dal livello area.
* Il parametro `p_area_schema_db` e necessario per il fallback; il chiamante
  deve fornirlo (tipicamente dal mapping `area_model_overrides`).

---

### Esempio d'uso

```sql
SELECT script.fn_resolve_livello_oggetto(42, 'vendite', 'fatture', 'vendite');
-- Ritorna: 'TUTTO'::config.livello_accesso
```

---

{% include-markdown "signature-core.md" %}

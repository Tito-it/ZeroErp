## Documentazione Concettuale – Funzione `config.fn_resolve_livello_area`

> **Vedi anche**
>
> **Tabelle correlate:**
>
> * [config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali)
> * [config.user_override_aree](/dbzero/config/tabelle/user_override_aree)
> * [config.profili_reparto_aree](/dbzero/config/tabelle/profili_reparto_aree)
>
> **Funzioni correlate:**
>
> * [config.fn_get_ruolo_sistema](/dbzero/config/funzioni/fn_get_ruolo_sistema)

---

### Scopo Principale

(latest review 28-02-2026)
La funzione **`config.fn_resolve_livello_area`** risolve il livello di accesso
effettivo di un utente per un'area funzionale, identificata tramite `schema_db`.

---

### Parametri di input

| Parametro | Tipo | Descrizione |
| --------- | ---- | ----------- |
| `p_auth_user_id` | integer | ID dell'utente Django. |
| `p_area_schema_db` | varchar(50) | Schema DB dell'area (es. `'vendite'`, `'anagrafiche'`). |

---

### Output

Ritorna `config.livello_accesso` (ENUM): `TUTTO`, `LETTURA` o `BLOCCATO`.

---

### Catena di risoluzione

1. **Ruolo sistema** — `NULL` o `DISABILITATO` → `BLOCCATO`; `ADMIN` → `TUTTO`
2. **Override utente area** — se presente e temporalmente valido (`valido_dal` / `valido_al`)
3. **Profilo reparto** — ereditato dall'unita organizzativa della risorsa umana
4. **Default** → `BLOCCATO`

---

### Regole principali

* Funzione **STABLE**.
* La validita temporale degli override e controllata con `CURRENT_DATE`.
* Il profilo reparto e legato all'unita organizzativa via `risorse_umane.unita_organizzativa_id`.

---

### Esempio d'uso

```sql
SELECT config.fn_resolve_livello_area(42, 'vendite');
-- Ritorna: 'LETTURA'::config.livello_accesso
```

---

{% include-markdown "signature-core.md" %}

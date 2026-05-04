## Documentazione Concettuale – Funzione `script.fn_resolve_livello_area`

> **Vedi anche**
>
**Tabelle correlate:**
>
[config.aree_funzionali](/dbzero/config/tabelle/aree_funzionali)
> [config.user_override_aree](/dbzero/config/tabelle/user_override_aree)
> [config.profili_accesso](/dbzero/config/tabelle/profili_accesso)
> [config.profili_accesso_aree](/dbzero/config/tabelle/profili_accesso_aree)
> [config.profili_accesso_bindings](/dbzero/config/tabelle/profili_accesso_bindings)
>
**Funzioni correlate:**
>
[script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin),
[script.fn_has_identita_attiva](/dbzero/script/funzioni/fn_has_identita_attiva),
[script.fn_get_profili_accesso_applicabili](/dbzero/script/funzioni/fn_get_profili_accesso_applicabili)

---
### 🎯 Scopo Principale
(latest review 04-05-2026 — modello legacy `profili_reparto_*` dismesso)

La funzione **`script.fn_resolve_livello_area`** risolve il livello di accesso
effettivo di un utente per un'area funzionale, identificata tramite `schema_db`.

---

### Parametri di input

| Parametro          | Tipo                                                    | Descrizione                                             |
| ------------------ | ------------------------------------------------------- | ------------------------------------------------------- |
| `p_auth_user_id`   | `anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE` | ID dell'utente Django.                                  |
| `p_area_schema_db` | `config.aree_funzionali.schema_db%TYPE`                 | Schema DB dell'area (es. `'vendite'`, `'anagrafiche'`). |

---

### Output

Ritorna `config.livello_accesso` (ENUM): `TUTTO`, `LETTURA` o `BLOCCATO`.

---

### Catena di risoluzione

1. **SUPER_ADMIN** — binding attivo a profilo SUPER_ADMIN → `TUTTO`
2. **Identita attiva** — nessuna identita attiva nella finestra → `BLOCCATO`
3. **Override utente area** — se presente e temporalmente valido (`valido_dal` / `valido_al`)
4. **Profili accesso** — risolti via [`fn_get_profili_accesso_applicabili`](/dbzero/script/funzioni/fn_get_profili_accesso_applicabili) (AD_HOC vince su REPARTO/PORTALE)
5. **Default** → `BLOCCATO`

---

### Regole principali

* Funzione **STABLE**.
* La validita temporale degli override e controllata con `CURRENT_DATE`.
* I profili applicabili (REPARTO via `risorse_umane.unita_organizzativa_id`, PORTALE per ruolo applicativo, AD_HOC per identita) sono calcolati centralmente da `fn_get_profili_accesso_applicabili`.

---

### Esempio d'uso

```sql
SELECT script.fn_resolve_livello_area(42, 'vendite');
-- Ritorna: 'LETTURA'::config.livello_accesso
```

---

{% include-markdown "signature-core.md" %}

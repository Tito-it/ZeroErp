## Documentazione Concettuale – Funzione `script.fn_check_azione_processo`

> **Vedi anche**
>
**Tabelle correlate:**
>
[config.azioni_processo](/dbzero/config/tabelle/azioni_processo)
> [config.user_override_azioni](/dbzero/config/tabelle/user_override_azioni)
> [config.profili_reparto_azioni](/dbzero/config/tabelle/profili_reparto_azioni)
>
**Funzioni correlate:**
>
[script.fn_is_super_admin](/dbzero/script/funzioni/fn_is_super_admin),
[script.fn_has_identita_attiva](/dbzero/script/funzioni/fn_has_identita_attiva)

---
### 🎯 Scopo Principale
(latest review 08-03-2026)
La funzione **`script.fn_check_azione_processo`** verifica se un'azione di processo
(identificata da `permission_codename`) e abilitata per un utente.

Funzione `fn_check_*`: puro boolean, no RAISE.

---

### Parametri di input

| Parametro               | Tipo                                                    | Descrizione                               |
| ----------------------- | ------------------------------------------------------- | ----------------------------------------- |
| `p_auth_user_id`        | `anagrafiche.risorse_umane_auth_user.auth_user_id%TYPE` | ID dell'utente Django.                    |
| `p_permission_codename` | `config.azioni_processo.permission_codename%TYPE`       | Codice azione (es. `'can_emit_invoice'`). |

---

### Output

Ritorna `boolean`: `true` se l'azione e abilitata, `false` altrimenti.

---

### Catena di risoluzione

1. **Ruolo sistema** — `NULL`/`DISABILITATO` → `false`; `ADMIN` → `true`
2. **Override utente azione** — se presente e temporalmente valido (`valido_dal`/`valido_al`)
3. **Profilo reparto azione** — ereditato dall'unita organizzativa
4. **Default** → `false` (negata)

---

### Regole principali

* Funzione **STABLE**.
* Il codename dell'azione viene risolto tramite JOIN su `config.azioni_processo`.
* Pensata per essere chiamata dal backend Django per controllo permessi su azioni
  specifiche (es. emissione fattura, annullamento lotto).

---

### Esempio d'uso

```sql
SELECT script.fn_check_azione_processo(42, 'can_emit_invoice');
-- Ritorna: true/false
```

---

{% include-markdown "signature-core.md" %}

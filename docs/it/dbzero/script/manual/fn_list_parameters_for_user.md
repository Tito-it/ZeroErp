## Documentazione Concettuale -- Funzione `script.fn_list_parameters_for_user()`

### Scopo

Restituisce **tutti i parametri** di `config.parameters` con i valori override risolti
per un dato utente Django, i suoi gruppi e il suo emittente fiscale di contesto.

Pensata per la UI di gestione parametri: mostra a colpo d'occhio il valore
effettivo di ogni parametro e da quale livello proviene.

### Firma

```sql
script.fn_list_parameters_for_user(
    p_django_user_id        integer,
    p_group_ids             integer[]  DEFAULT NULL,
    p_emittente_fiscale_id  bigint     DEFAULT NULL
)
RETURNS TABLE (
    code              varchar,
    description       text,
    default_value     text,
    emittente_value   text,
    group_value       text,
    user_value        text,
    user_override_id  bigint,
    resolved_value    text
)
```

### Parametri

| Parametro | Tipo | Descrizione |
|-----------|------|-------------|
| `p_django_user_id` | integer | ID utente Django (obbligatorio) |
| `p_group_ids` | integer[] | Array ID gruppi Django dell'utente (opzionale) |
| `p_emittente_fiscale_id` | bigint | ID emittente fiscale di contesto (opzionale) |

### Colonne restituite

| Colonna | Descrizione |
|---------|-------------|
| `code` | Codice parametro (`config.parameters.code`) |
| `description` | Descrizione parametro |
| `default_value` | Valore di default globale |
| `emittente_value` | Override a livello emittente (NULL se assente) |
| `group_value` | Override a livello gruppo (NULL se assente) |
| `user_value` | Override a livello utente (NULL se assente) |
| `user_override_id` | ID record override utente (per edit/delete da UI) |
| `resolved_value` | Valore finale risolto |

### Regole di priorita'

La risoluzione del `resolved_value` segue la catena:

```
user_value > group_value > emittente_value > default_value
```

Il primo valore non-NULL vince (`COALESCE`).

### Dipendenze DB

- `config.parameters` — tabella parametri
- `config.parameter_overrides` — tabella override con `emittente_fiscale_id`

### Note

- Per il livello **gruppo**, se l'utente appartiene a piu' gruppi con override
  diversi sullo stesso parametro, viene preso il primo per `id` (determinismo).
- Vengono considerati solo override con `attivo = true`.
- L'ordinamento e' per `code ASC`.

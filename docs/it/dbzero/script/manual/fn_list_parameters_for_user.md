## Documentazione Concettuale -- Funzione `script.fn_list_parameters_for_user()`

### Scopo

Restituisce **tutti i parametri** di `config.parameters` con i valori override risolti
per un dato utente Django, i suoi gruppi, il suo emittente fiscale di contesto e la
categoria_cliente del billing account destinatario.

Pensata per la UI di gestione parametri: mostra a colpo d'occhio il valore
effettivo di ogni parametro e da quale livello proviene, con gli ID necessari
per la modifica/eliminazione mirata degli override.

### Firma

```sql
script.fn_list_parameters_for_user(
    p_django_user_id        integer,
    p_group_ids             integer[]  DEFAULT NULL,
    p_emittente_fiscale_id  bigint     DEFAULT NULL,
    p_categoria_cliente_id  smallint   DEFAULT NULL   -- aggiunto in 20260519-01
)
RETURNS TABLE (
    code                          varchar,
    description                   text,
    default_value                 text,
    emittente_value               text,
    emittente_override_id         bigint,
    group_value                   text,
    user_value                    text,
    user_override_id              bigint,
    categoria_cliente_value       text,
    categoria_cliente_override_id bigint,
    resolved_value                text
)
```

### Parametri

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_django_user_id` | integer | ID utente Django (obbligatorio) |
| `p_group_ids` | integer[] | Array ID gruppi Django dell'utente (opzionale) |
| `p_emittente_fiscale_id` | bigint | ID emittente fiscale di contesto (opzionale) |
| `p_categoria_cliente_id` | smallint | ID categoria_cliente del BA destinatario (opzionale, default NULL) |

### Colonne restituite

| Colonna | Descrizione |
| --- | --- |
| `code` | Codice parametro (`config.parameters.code`) |
| `description` | Descrizione parametro |
| `default_value` | Valore di default globale |
| `emittente_value` | Override a livello emittente puro (NULL se assente) |
| `emittente_override_id` | ID record override emittente (per edit/delete da UI) |
| `group_value` | Override a livello gruppo (NULL se assente) |
| `user_value` | Override a livello utente (NULL se assente) |
| `user_override_id` | ID record override utente (per edit/delete da UI) |
| `categoria_cliente_value` | Override a livello categoria_cliente puro (NULL se assente o p_categoria_cliente_id IS NULL) |
| `categoria_cliente_override_id` | ID record override categoria (per edit/delete da UI; bigint) |
| `resolved_value` | Valore finale risolto secondo la cascata |

### Regole di priorita'

La risoluzione del `resolved_value` segue la cascata (coerente con
`fn_get_parameter_full` overload 7-arg, migration `20260515-08`):

```text
user_value > categoria_cliente_value > group_value > emittente_value > default_value
```

Il primo valore non-NULL vince (`COALESCE` su subquery indipendenti).

### Architettura a due livelli

La funzione usa due logiche distinte per coprire visualizzazione e risoluzione:

- **LEFT JOIN "puri"** (per `*_value` e `*_override_id`): filtrano ogni livello
  con scope esclusivo (es. il livello categoria_cliente usa `django_user_id IS NULL
  AND django_group_id IS NULL AND emittente_fiscale_id IS NULL AND ...`).
  Mostrano solo override "di livello puro", utili per la UI admin.

- **Subquery COALESCE** (per `resolved_value`): replicano esattamente la logica
  di `fn_get_parameter_full` senza filtri IS NULL aggiuntivi sul livello categoria,
  garantendo che il valore visualizzato sia identico a quello usato dal runtime.

### Retro-compatibilita'

Con `p_categoria_cliente_id = NULL` (default):

- Il confronto `NULL = NULL` è sempre false: `po_cat` non matcha nessuna riga
- `categoria_cliente_value` e `categoria_cliente_override_id` restano NULL
- La subquery categoria nel resolver non matcha → cascata identica alla firma 3-arg

I caller SQL che passano 3 argomenti continuano a funzionare senza modifiche.

### Dipendenze DB

- `config.parameters` — tabella parametri
- `config.parameter_overrides` — override con tutti i livelli di scope
- `anagrafiche.categorie_clienti` — FK di `categoria_cliente_id`

### Note

- Per il livello **gruppo**, se l'utente appartiene a più gruppi con override
  diversi sullo stesso parametro, viene preso il primo per `id` (determinismo).
- Per il livello **gruppo** non viene esposto un `group_override_id`: il LATERAL
  gestisce il multi-gruppo e l'ID non è univoco per design.
- Vengono considerati solo override con `attivo = true`.
- L'ordinamento è per `code ASC`.
- I livelli `session` e `function` (presenti in `fn_get_parameter_full`) non sono
  esposti: sono scope dinamici di runtime, non gestibili via UI admin statica.

### Storia

| Data | Migration | Modifica |
| --- | --- | --- |
| 2026-04-03 | `20260403-16` | Creazione funzione 3-arg |
| 2026-04-06 | `20260406-02` | Aggiunta colonna `emittente_override_id` |
| 2026-05-19 | `20260519-01` | Aggiunto 4° param `p_categoria_cliente_id`; nuove colonne `categoria_cliente_value` e `categoria_cliente_override_id` (bigint); `resolved_value` ricalcolato con subquery coerenti con `fn_get_parameter_full` 7-arg |

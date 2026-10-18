## Documentazione Concettuale — Funzione `script.fn_get_parameter_full()`

> **Vedi anche**
>
> [config.parameters](/dbzero/config/tabelle/parameters)
> [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [script.fn_list_parameters_for_user](/dbzero/script/funzioni/fn_list_parameters_for_user)
> [script.fn_get_parameter_di_sessione](/dbzero/script/manual/fn_get_parameter_di_sessione) — per chi legge dentro il database: il contesto dalla sessione

---

### Scopo

Restituisce il valore di un parametro di sistema applicando la cascata di override
multi-livello definita in `config.parameter_overrides`. È il **punto unico di verità**
per la risoluzione parametri: nessun modulo deve leggere direttamente `config.parameters`
o `config.parameter_overrides` per ottenere il valore finale.

---

### Overload disponibili

La funzione esiste in **due overload** con firma distinta:

#### Overload originale — 6 parametri (backward compatible)

```sql
script.fn_get_parameter_full(
    p_code                  text,
    p_emittente_fiscale_id  bigint    DEFAULT NULL,
    p_django_user_id        integer   DEFAULT NULL,
    p_group_ids             integer[] DEFAULT NULL,
    p_session_key           text      DEFAULT NULL,
    p_function_name         text      DEFAULT NULL
) RETURNS text
```

Cascata: `user → group → emittente → session → function → default`

Tutti i caller esistenti che non passano `categoria_cliente_id` continuano
a usare questo overload senza modifiche.

#### Overload esteso — 7 parametri (con categoria cliente)

```sql
script.fn_get_parameter_full(
    p_code                  text,
    p_emittente_fiscale_id  config.parameter_overrides.emittente_fiscale_id%TYPE  DEFAULT NULL,
    p_django_user_id        config.parameter_overrides.django_user_id%TYPE        DEFAULT NULL,
    p_group_ids             integer[]                                              DEFAULT NULL,
    p_session_key           config.parameter_overrides.session_key%TYPE           DEFAULT NULL,
    p_function_name         config.parameter_overrides.function_name%TYPE         DEFAULT NULL,
    p_categoria_cliente_id  config.parameter_overrides.categoria_cliente_id%TYPE  DEFAULT NULL
) RETURNS text
```

Cascata: `user → categoria_cliente → group → emittente → session → function → default`

`p_categoria_cliente_id` è l'**ultimo parametro** per garantire backward compatibility:
i caller posizionali con 6 argomenti usano il vecchio overload automaticamente.
`p_group_ids` rimane `integer[]` esplicito — `%TYPE[]` non è sintassi valida in PostgreSQL.

Per invocare l'overload esteso, passare esplicitamente il 7° argomento o usare
named arg: `p_categoria_cliente_id => val`.

---

### Cascata di risoluzione (overload esteso)

La funzione usa `COALESCE` su subquery indipendenti, valutate in cortocircuito:
appena un livello restituisce un valore non-NULL, i livelli successivi non vengono
eseguiti.

| Priorità | Livello | Parametro | Condizione WHERE |
|---|---|---|---|
| 1 | user | `p_django_user_id` | `django_user_id = p_django_user_id` |
| 2 | categoria_cliente | `p_categoria_cliente_id` | `categoria_cliente_id = p_categoria_cliente_id` |
| 3 | group | `p_group_ids` | `django_group_id = ANY(p_group_ids)` |
| 4 | emittente | `p_emittente_fiscale_id` | `emittente_fiscale_id = p_emittente_fiscale_id` |
| 5 | session | `p_session_key` | `session_key = p_session_key` |
| 6 | function | `p_function_name` | `function_name = p_function_name` |
| 7 | default | — | `config.parameters.default_value` |

**Gestione NULL dei parametri di scope**: se un parametro di scope è `NULL`,
la condizione `col = NULL` è sempre FALSE in SQL → il livello viene saltato
automaticamente senza IF espliciti.

**Motivazione ordine categoria_cliente > group**: la regola commerciale (es.
categoria PREMIUM max sconto 5%) deve vincere sul seniority dell'operatore
(gruppo SENIOR max 20%). Eccezioni individuali si configurano al livello user
(priorità 1), che sovrascrive tutto.

---

### Parametri

| Nome | Tipo | Default | Descrizione |
|---|---|---|---|
| `p_code` | `text` | obbligatorio | Codice parametro (`config.parameters.code`) |
| `p_emittente_fiscale_id` | `bigint NULL` | `NULL` | Override per emittente fiscale specifico |
| `p_django_user_id` | `integer NULL` | `NULL` | Override per utente Django |
| `p_group_ids` | `integer[] NULL` | `NULL` | Override per gruppi Django (array di id) |
| `p_session_key` | `text NULL` | `NULL` | Override per sessione web |
| `p_function_name` | `text NULL` | `NULL` | Override per funzione chiamante |
| `p_categoria_cliente_id` | `smallint NULL` | `NULL` | Override per categoria cliente (solo overload 7-param) |

---

### Valore di ritorno

`TEXT` — il valore override più specifico trovato nella cascata, oppure
`config.parameters.default_value` se nessun override applicabile.

---

### Gestione errori

Se `p_code` non esiste in `config.parameters`, la funzione chiama
`script.fn_log_and_raise_error(...)` con codice `ERRORE_PARAMETRI_TABELLA` e
solleva eccezione (SQLSTATE `P0001`). `fn_log_and_raise_error` gestisce
internamente il raise — non occorre un `RAISE EXCEPTION` aggiuntivo dopo il
`PERFORM`.

---

### Volatilità e performance

- **`STABLE`**: il planner può riutilizzare il risultato per chiamate identiche
  nella stessa query.
- **Indici**: ogni livello dei 4 più frequenti ha un indice composto su
  `(parameter_id, <dimensione>)` — vedi [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides).
- **Cortocircuito**: il COALESCE si ferma al primo livello che ritorna un valore;
  i livelli successivi non eseguono la subquery.
- **Determinismo group**: se l'utente appartiene a più gruppi con override diversi,
  viene restituito l'override con `id` più basso (`ORDER BY po.id LIMIT 1`).

---

### Esempi

#### Risoluzione semplice (solo default)

```sql
SELECT script.fn_get_parameter_full('VENDITE_MAX_SCONTO_PCT');
-- ritorna: '0' (default sicuro)
```

#### Con utente e categoria cliente (overload esteso)

```sql
SELECT script.fn_get_parameter_full(
    'VENDITE_MAX_SCONTO_PCT',
    p_django_user_id       => 42,
    p_group_ids            => ARRAY[10, 15],
    p_emittente_fiscale_id => 1,
    p_categoria_cliente_id => 3   -- categoria PREMIUM
);
-- La cascata trova prima il match a livello user se esiste,
-- altrimenti categoria (PREMIUM), poi group, poi emittente, poi default.
```

#### Chiamata dall'overload originale (6 parametri)

```sql
-- Chiamata posizionale a 6 arg: usa il vecchio overload, no categoria_cliente
SELECT script.fn_get_parameter_full(
    'VENDITE_MAX_SCONTO_PCT',
    1,      -- emittente_fiscale_id
    42,     -- django_user_id
    ARRAY[10, 15],  -- group_ids
    NULL,   -- session_key
    NULL    -- function_name
);
```

---

### Cronologia modifiche

| Data | Versione | Modifica |
|---|---|---|
| 2025-09-26 | v1 | Prima versione (user → group → session → function → default) |
| 2026-04-03 | v2 | Aggiunto livello emittente_fiscale_id (migrazione da tenant_id) |
| 2026-05-15 | v3 | Nuovo overload 7-param con livello categoria_cliente (priorità 2, tra user e group) |

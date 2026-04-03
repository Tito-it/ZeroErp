## Documentazione Concettuale -- Funzione `script.fn_get_parameter_full()`

> **Vedi anche**
>
> **Approfondimento Tabelle:**
>
> [config.parameters](/dbzero/config/tabelle/parameters)
> [config.parameter_overrides](/dbzero/config/tabelle/parameter_overrides)
>
> **Approfondimento funzioni:**
>
> [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)
> [script.fn_list_parameters_for_user](/dbzero/script/funzioni/fn_list_parameters_for_user)

---

La funzione **`script.fn_get_parameter_full(...) RETURNS TEXT`** restituisce il valore di un parametro applicando:

* **default** da `config.parameters.default_value`
* eventuali **override** da `config.parameter_overrides`

con una **precedenza deterministica**.

---
### Scopo Principale

(latest update 03-04-26)

* **Ricerca safe del parametro**
  Verifica l'esistenza del parametro in `config.parameters` e recupera `id` + `default_value`.

* **Override gerarchico**
  Cerca un override in `config.parameter_overrides` secondo la precedenza implementata.

* **Centralizzazione**
  Un unico punto di verita' per la risoluzione parametri, evitando duplicazioni nel codice DB/app.

* **Gestione errori**
  Se `p_code` non esiste in `config.parameters`, logga (`ERRORE_PARAMETRI_TABELLA`) e solleva eccezione.

---

### Firma e Parametri di Input

```sql
script.fn_get_parameter_full(
  p_code                  text,
  p_emittente_fiscale_id  bigint   DEFAULT NULL,
  p_django_user_id        integer  DEFAULT NULL,
  p_group_ids             integer[] DEFAULT NULL,
  p_session_key           text     DEFAULT NULL,
  p_function_name         text     DEFAULT NULL
) RETURNS text
```

| Nome                     | Tipo        | Default | Descrizione                                          |
| ------------------------ | ----------- | ------- | ---------------------------------------------------- |
| `p_code`                 | `text`      | --      | Codice parametro (`config.parameters.code`).         |
| `p_emittente_fiscale_id` | `bigint`    | `NULL`  | Override ambito emittente fiscale.                   |
| `p_django_user_id`       | `integer`   | `NULL`  | Override ambito utente (Django).                     |
| `p_group_ids`            | `integer[]` | `NULL`  | Override ambito gruppi (Django groups).               |
| `p_session_key`          | `text`      | `NULL`  | Override ambito sessione.                            |
| `p_function_name`        | `text`      | `NULL`  | Override ambito funzione/chiamante.                  |

---

### Precedenza Override

La funzione risolve l'override tramite `COALESCE` su subquery indipendenti, ciascuna mirata a un singolo livello di scope. Ogni subquery usa l'indice composto `(parameter_id, <scope>)` e viene valutata in cortocircuito: se il livello superiore ha un override, i successivi non vengono eseguiti.

1. **User** (`django_user_id`) -- massima priorita'
2. **Group** (`django_group_id IN p_group_ids`)
3. **Emittente** (`emittente_fiscale_id`)
4. **Session** (`session_key`)
5. **Function** (`function_name`)
6. **Default** (`config.parameters.default_value`)

Vengono considerati solo override con `attivo = true`.

---

### Flusso Logico

1. **Recupero parametro base** (`id`, `default_value`) da `config.parameters`.
2. Se non trovato:
   * `script.fn_log_and_raise_error(..., 'ERRORE_PARAMETRI_TABELLA', ...)`
   * `RAISE EXCEPTION ...` (ERRCODE `22023`).
3. **Risoluzione override** via COALESCE su 5 subquery indipendenti, una per livello di scope.
   Se il parametro di scope e' NULL, la subquery ritorna NULL senza accesso a disco.
4. Ritorna il primo valore non-NULL trovato nella catena, o `default_value`.

---

### Valore di Ritorno

* **`TEXT`**: valore override piu' specifico trovato, o `default_value` se nessun override applicabile.

---

### Note Operative

* **Multi-ambito reale:** supporta contemporaneamente user/group/emittente/session/function.
* **Cortocircuito:** grazie a COALESCE + subquery, se l'override user esiste le query successive non vengono eseguite.
* **Performance:** ogni subquery usa un indice composto dedicato (`ix_overrides_param_user`, `ix_overrides_param_group`, `ix_parameter_overrides_emittente`). Nessun sort richiesto.
* **Determinismo per gruppo:** se l'utente appartiene a piu' gruppi con override diversi, viene preso il primo per `id` (`ORDER BY po.id LIMIT 1`).

---

> **"`fn_get_parameter_full` risolve in modo deterministico il valore di un parametro applicando override multi-ambito (user -> group -> emittente -> session -> function), con valutazione in cortocircuito e logging centralizzato."**

{% include-markdown "signature-core.md" %}

## Documentazione Concettuale -- Funzione `script.fn_list_parameters_for_user()`

> **Ultimo aggiornamento**: 9 novembre 2026

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

Il `resolved_value` lo calcola `script.fn_get_parameter_full`, che è la sede
della cascata (l'ordine dei livelli sta lì):

```text
utente > categoria_cliente > gruppo > emittente > default
```

### Architettura a due livelli

La funzione usa due logiche distinte per coprire visualizzazione e risoluzione:

- **LEFT JOIN per livello** (per `*_value` e `*_override_id`): ogni livello
  (emittente, gruppo, utente, categoria_cliente) legge l'override della sua
  dimensione. Ogni override ha esattamente un ambito
  (`chk_parameter_overrides_un_ambito`) e ce n'è al più uno per parametro e ambito
  (`uq_overrides_full_scope_v6`, `NULLS NOT DISTINCT`): la lista ha **una riga per
  parametro** per costruzione, e le regole stanno nei vincoli, non nella query.
  Gli id servono alla DELETE del backend.

- **`resolved_value`**: è `script.fn_get_parameter_full` chiamata **per nome** con
  gli stessi ambiti (funzione `NULL`). Non una copia della cascata: il valore
  mostrato è quello del runtime per costruzione.

### Retro-compatibilita'

Con `p_categoria_cliente_id = NULL` (default):

- Il confronto `NULL = NULL` è sempre false: `po_cat` non matcha nessuna riga
- `categoria_cliente_value` e `categoria_cliente_override_id` restano NULL
- Il livello categoria della cascata non trova righe → cascata identica alla firma 3-arg

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
- Il livello `function` (presente in `fn_get_parameter_full`) non è esposto: è uno
  scope dinamico di runtime, non gestibile via UI admin statica. Un livello «sessione»
  non esiste più (2026-11-09).

### Storia

| Data | Migration | Modifica |
| --- | --- | --- |
| 2026-04-03 | `20260403-16` | Creazione funzione 3-arg |
| 2026-04-06 | `20260406-02` | Aggiunta colonna `emittente_override_id` |
| 2026-05-19 | `20260519-01` | Aggiunto 4° param `p_categoria_cliente_id`; nuove colonne `categoria_cliente_value` e `categoria_cliente_override_id` (bigint); `resolved_value` ricalcolato con subquery coerenti con `fn_get_parameter_full` 7-arg |
| 2026-10-07 | `20261007-71` | Livelli puri su tutti e quattro i JOIN (prima l'utente filtrava la sola sua dimensione, emittente e gruppo non tutte: una riga mista compariva come override personale con un id che la DELETE rifiuta, e duplicava la riga); `resolved_value` delegato a `fn_get_parameter_full` invece di ricopiarne la cascata. Firma invariata |
| 2026-10-07 | `20261007-73` | Escono i filtri «altre dimensioni `NULL`» del `-71`: col vincolo `chk_parameter_overrides_un_ambito` (`-72`) ogni override è puro per costruzione |
| 2026-11-09 | `20261111-16` | Esce il livello sessione: `resolved_value` chiama `fn_get_parameter_full` per nome, sulla firma nuova senza `p_session_key`; il commento nomina il vincolo `uq_overrides_full_scope_v6`. Colonne e firma invariate. `brief-db-revisione-dbops`, giro 13 |

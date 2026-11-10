{% include-markdown "it/dbzero/dbops/manual/automazione_overlap.md" %}
# 📚 Tabella `automazione_overlap`

> 📝 **Descrizione**
>
> Il registro dei vincoli anti-sovrapposizione temporale: una riga per tabella (target_schema, target_table) da cui dbops.fn_apply_automazione_overlap genera un EXCLUDE GiST. La chiave di gruppo e' key_columns (array JSON di nomi di colonna) piu' key_expressions (array JSON di espressioni), nell'ordine dell'array (chk_automazione_overlap_chiavi); il periodo e' range_col, o in sua assenza valido_dal_col/valido_al_col con range_bounds; where_predicate rende il vincolo parziale. Il nome e' constraint_name o il template ex_&lt;tabella&gt;_no_overlap. Si applicano le righe active con exec_mode AUTO o uguale a quello della corsa. key_expressions e where_predicate sono DDL di fiducia: le scrive solo chi migra. Seed da 80_data (CSV dbops/automazione_overlap.csv).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| target_schema | text | NO |  |
| target_table | text | NO |  |
| key_columns | jsonb | YES |  |
| valido_dal_col | text | NO | 'valido_dal'::text |
| valido_al_col | text | NO | 'valido_al'::text |
| range_bounds | text | NO | '[]'::text |
| constraint_name | text | YES |  |
| active | boolean | NO | false |
| exec_mode | text | NO | 'AUTO'::text |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| range_col | text | YES |  |
| where_predicate | text | YES |  |
| key_expressions | jsonb | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_automazione_overlap_chiavi |  |
| PRIMARY KEY | pk_automazione_overlap | target_schema, target_table |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automazione_overlap | `CREATE UNIQUE INDEX pk_automazione_overlap ON dbops.automazione_overlap USING btree (target_schema, target_table)` |

---
{% include-markdown "signature-core.md" %}

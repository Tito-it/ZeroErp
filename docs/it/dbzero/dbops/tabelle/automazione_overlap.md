{% include-markdown "it/dbzero/dbops/manual/automazione_overlap.md" %}
# 📚 Tabella `automazione_overlap`

> 📝 **Descrizione**
>
> Configura anti-overlap temporale per tabelle con valido_dal/valido_al o valid_from/valid_to.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| target_schema | text | NO |  |
| target_table | text | NO |  |
| key_columns | text[] | YES |  |
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
| key_expressions | text[] | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_automazione_overlap | target_schema, target_table |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automazione_overlap | `CREATE UNIQUE INDEX pk_automazione_overlap ON dbops.automazione_overlap USING btree (target_schema, target_table)` |

---
{% include-markdown "signature-core.md" %}

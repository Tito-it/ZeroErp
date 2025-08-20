# 📚 Tabella `automation_rules_tbl`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| enabled | boolean | NO | true |
| rule_type | text | NO |  |
| target_schema | text | NO |  |
| target_table | text | YES |  |
| exec_mode | text | NO | 'AUTO'::text |
| name_template | text | YES |  |
| existence_strategy | text | NO | 'BY_NAME'::text |
| params | jsonb | NO | '{}'::jsonb |
| priority | integer | NO | 100 |
| note | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | automation_rules_tbl_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| automation_rules_tbl_pkey | `CREATE UNIQUE INDEX automation_rules_tbl_pkey ON dbops.automation_rules_tbl USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

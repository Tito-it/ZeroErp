{% include-markdown "it/dbzero/dbops/manual/automation_rules_tbl.md" %}
# 📚 Tabella `automation_rules_tbl`

> 📝 **Descrizione**
>
> Regole di automazione per tabella/ambito

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| enabled | boolean | NO | true |
| rule_type | text | NO |  |
| target_schema | text | NO | '*all'::text |
| target_table | text | NO | '*all'::text |
| exec_mode | text | NO | 'AUTO'::text |
| name_template | text | YES |  |
| params | jsonb | NO | '{}'::jsonb |
| priority | integer | NO | 100 |
| note | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_automation_rules_tbl_exec_mode |  |
| CHECK | chk_automation_rules_tbl_name_template_non_vuoto |  |
| CHECK | chk_automation_rules_tbl_regola_valida |  |
| CHECK | chk_automation_rules_tbl_rule_type |  |
| PRIMARY KEY | automation_rules_tbl_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| automation_rules_tbl_pkey | `CREATE UNIQUE INDEX automation_rules_tbl_pkey ON dbops.automation_rules_tbl USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

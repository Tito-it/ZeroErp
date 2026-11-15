{% include-markdown "it/dbzero/dbops/manual/automation_delete_block.md" %}
# 📚 Tabella `automation_delete_block`

> 📝 **Descrizione**
>
> Il registro del blocco delle DELETE: una riga per tabella (uq_automation_delete_block_table) su cui una DELETE passa solo se la GUC guc_key e' accesa nella sessione. dbops.fn_run_automations_delete_block porta i trigger (script.trgfn_delete_block_by_guc, BEFORE DELETE FOR EACH ROW) allo stato del registro: crea quello atteso, rigenera quello diverso, toglie quello di una riga spenta (enabled = false); il nome e' trigger_name o il template di dbops.fn_nome_oggetto_dichiarato. Un trigger della funzione su una tabella che il registro non nomina ferma il giro (E_DELETE_BLOCK). Il confronto fra registro e trigger vivi e' dbops.fn_delete_block_divergenze.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| schema_name | text | NO |  |
| table_name | text | NO |  |
| guc_key | text | NO |  |
| enabled | boolean | NO | true |
| trigger_name | text | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_automation_delete_block_trigger_name_non_vuoto |  |
| PRIMARY KEY | pk_automation_delete_block | id |
| UNIQUE | uq_automation_delete_block_table | schema_name, table_name |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_automation_delete_block | `CREATE UNIQUE INDEX pk_automation_delete_block ON dbops.automation_delete_block USING btree (id)` |
| uq_automation_delete_block_table | `CREATE UNIQUE INDEX uq_automation_delete_block_table ON dbops.automation_delete_block USING btree (schema_name, table_name)` |

---
{% include-markdown "signature-core.md" %}

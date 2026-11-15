{% include-markdown "it/dbzero/config/manual/sistema_codici.md" %}
# 📚 Tabella `sistema_codici`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice_interno | text | NO |  |
| descrizione | text | YES |  |
| prefisso | text | NO |  |
| separatore | text | NO | ''::text |
| lunghezza_numero | integer | NO | 6 |
| usa_sequenza | boolean | YES | true |
| data_insert | timestamp with time zone | YES | now() |
| user_insert | text | YES | CURRENT_USER |
| data_update | timestamp with time zone | YES | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| schema_tabella | text | YES |  |
| nome_tabella | text | YES |  |
| nome_colonna | text | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_sistema_codici | id |
| UNIQUE | uq_sistema_codici_codice_interno | codice_interno |
| UNIQUE | uq_sistema_codici_prefisso | prefisso |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_sistema_codici | `CREATE UNIQUE INDEX pk_sistema_codici ON config.sistema_codici USING btree (id)` |
| uq_sistema_codici_codice_interno | `CREATE UNIQUE INDEX uq_sistema_codici_codice_interno ON config.sistema_codici USING btree (codice_interno)` |
| uq_sistema_codici_prefisso | `CREATE UNIQUE INDEX uq_sistema_codici_prefisso ON config.sistema_codici USING btree (prefisso)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sistema_codici_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'E_CODICE_NON_MODIFICABILE')` |
| trg_sistema_codici_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_sistema_codici_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_sistema_codici_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_sistema_codici_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_sistema_codici_z90_sync_gen_codice_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION script.trgfn_config_sistema_codici_sync_gen_codice()` |
| trg_sistema_codici_z90_sync_gen_codice_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION script.trgfn_config_sistema_codici_sync_gen_codice()` |
| trg_sistema_codici_z90_sync_gen_codice_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION script.trgfn_config_sistema_codici_sync_gen_codice()` |

---
{% include-markdown "signature-core.md" %}

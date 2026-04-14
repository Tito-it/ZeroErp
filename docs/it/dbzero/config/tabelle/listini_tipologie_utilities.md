{% include-markdown "it/dbzero/config/manual/listini_tipologie_utilities.md" %}
# 📚 Tabella `listini_tipologie_utilities`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| utility_id | integer | NO |  |
| tipologia_id | smallint | NO |  |
| attivo | boolean | NO | true |
| storicizza | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | listini_tipologie_utilities_tipologia_id_fkey | tipologia_id |
| FOREIGN KEY | listini_tipologie_utilities_utility_id_fkey | utility_id |
| PRIMARY KEY | pk_listini_tipologie_utilities | id |
| UNIQUE | uq_listini_tipologie_utilities | utility_id, tipologia_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_listini_tipologie_utilities | `CREATE UNIQUE INDEX pk_listini_tipologie_utilities ON config.listini_tipologie_utilities USING btree (id)` |
| uq_listini_tipologie_utilities | `CREATE UNIQUE INDEX uq_listini_tipologie_utilities ON config.listini_tipologie_utilities USING btree (utility_id, tipologia_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_listini_tipologie_utilities_a10_listini_tipologie_re_3c42df | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'listini_tipologie', 'attivo', 'tipologia_id', 'id')` |
| trg_listini_tipologie_utilities_a10_listini_tipologie_re_3c42df | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'listini_tipologie', 'attivo', 'tipologia_id', 'id')` |
| trg_listini_tipologie_utilities_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_tipologie_utilities_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_listini_tipologie_utilities_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_tipologie_utilities_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_listini_tipologie_utilities_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('listini_tipologie_utilities_id')` |
| trg_listini_tipologie_utilities_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('listini_tipologie_utilities_id')` |

---
{% include-markdown "signature-core.md" %}

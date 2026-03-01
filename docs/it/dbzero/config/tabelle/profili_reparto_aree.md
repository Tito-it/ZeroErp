{% include-markdown "it/dbzero/config/manual/profili_reparto_aree.md" %}
# 📚 Tabella `profili_reparto_aree`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| unita_organizzativa_id | integer | NO |  |
| area_id | integer | NO |  |
| livello | USER-DEFINED | NO | 'BLOCCATO'::config.livello_accesso |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_profili_reparto_aree_area | area_id |
| FOREIGN KEY | fk_profili_reparto_aree_unita_organizzativa | unita_organizzativa_id |
| PRIMARY KEY | pk_profili_reparto_aree | id |
| UNIQUE | uq_profili_reparto_aree_uo_area | unita_organizzativa_id, area_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_profili_reparto_aree_area_id | `CREATE INDEX ix_profili_reparto_aree_area_id ON config.profili_reparto_aree USING btree (area_id)` |
| ix_profili_reparto_aree_uo_id | `CREATE INDEX ix_profili_reparto_aree_uo_id ON config.profili_reparto_aree USING btree (unita_organizzativa_id)` |
| pk_profili_reparto_aree | `CREATE UNIQUE INDEX pk_profili_reparto_aree ON config.profili_reparto_aree USING btree (id)` |
| uq_profili_reparto_aree_uo_area | `CREATE UNIQUE INDEX uq_profili_reparto_aree_uo_area ON config.profili_reparto_aree USING btree (unita_organizzativa_id, area_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_profili_reparto_aree_a10_aree_funzionali_require_att_9cb941 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id')` |
| trg_profili_reparto_aree_a10_aree_funzionali_require_att_9cb941 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'aree_funzionali', 'attivo', 'area_id')` |
| trg_profili_reparto_aree_a10_unita_organizzative_require_e4ae20 | AFTER | INSERT | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id')` |
| trg_profili_reparto_aree_a10_unita_organizzative_require_e4ae20 | AFTER | UPDATE | `EXECUTE FUNCTION dbops.trgfn_child_requires_active_parent('config', 'unita_organizzative', 'attivo', 'unita_organizzativa_id')` |
| trg_profili_reparto_aree_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_profili_reparto_aree_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_profili_reparto_aree_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_reparto_aree_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_reparto_aree_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('profili_reparto_aree_id')` |
| trg_profili_reparto_aree_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('profili_reparto_aree_id')` |

---
{% include-markdown "signature-core.md" %}

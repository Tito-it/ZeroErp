{% include-markdown "it/dbzero/config/manual/toponomastica.md" %}
# 📚 Tabella `toponomastica`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| descrizione | character varying | NO |  |
| stato_id | integer | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| attivo | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_toponomastica_stato_id | stato_id |
| PRIMARY KEY | pk_toponomastica | id |
| UNIQUE | uq_toponomastica_descrizione | descrizione |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_config_toponomastica_stato_id | `CREATE INDEX ix_config_toponomastica_stato_id ON config.toponomastica USING btree (stato_id)` |
| pk_toponomastica | `CREATE UNIQUE INDEX pk_toponomastica ON config.toponomastica USING btree (id)` |
| uq_toponomastica_descrizione | `CREATE UNIQUE INDEX uq_toponomastica_descrizione ON config.toponomastica USING btree (descrizione)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_block_deact_toponomastica_stradario_generale | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'stradario_generale', 'toponomastica_id', 'id')` |
| trg_toponomastica_audit_data_user_generic_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_toponomastica_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_toponomastica_bump_normalize_aft_upd | AFTER | UPDATE | `EXECUTE FUNCTION config.trgfn_toponomastica_bump_normalize()` |
| trg_toponomastica_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_toponomastica_normalize()` |
| trg_toponomastica_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_toponomastica_normalize()` |
| trg_toponomastica_protect_update_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_toponomastica_protect_update()` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/config/manual/unita_organizzative.md" %}
# 📚 Tabella `unita_organizzative`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | text | NO |  |
| parent_id | integer | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_unita_organizzative_parent_not_self |  |
| FOREIGN KEY | fk_unita_organizzative_parent | parent_id |
| PRIMARY KEY | pk_unita_organizzative | id |
| UNIQUE | uq_unita_organizzative_codice | codice |
| UNIQUE | uq_unita_organizzative_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_unita_organizzative_parent_id | `CREATE INDEX ix_unita_organizzative_parent_id ON config.unita_organizzative USING btree (parent_id)` |
| pk_unita_organizzative | `CREATE UNIQUE INDEX pk_unita_organizzative ON config.unita_organizzative USING btree (id)` |
| uq_unita_organizzative_codice | `CREATE UNIQUE INDEX uq_unita_organizzative_codice ON config.unita_organizzative USING btree (codice)` |
| uq_unita_organizzative_codice_interno | `CREATE UNIQUE INDEX uq_unita_organizzative_codice_interno ON config.unita_organizzative USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_unita_organizzative_a10_contatti_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'contatti', 'unita_organizzativa_id', 'id')` |
| trg_unita_organizzative_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_unita_organizzative_a10_risorse_umane_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('anagrafiche', 'risorse_umane', 'unita_organizzativa_id', 'id')` |
| trg_unita_organizzative_a10_unita_organizzative_block_de_619e29 | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('config', 'unita_organizzative', 'parent_id', 'id')` |
| trg_unita_organizzative_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

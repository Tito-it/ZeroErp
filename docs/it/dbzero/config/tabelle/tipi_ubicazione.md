# 📚 Tabella `tipi_ubicazione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | NO | 0 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_cfg_tipi_ubicazione | id |
| UNIQUE | uq_cfg_tipi_ubicazione_codice | codice |
| UNIQUE | uq_cfg_tipi_ubicazione_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_cfg_tipi_ubicazione_attivo | `CREATE INDEX ix_cfg_tipi_ubicazione_attivo ON config.tipi_ubicazione USING btree (attivo)` |
| ix_cfg_tipi_ubicazione_ordine | `CREATE INDEX ix_cfg_tipi_ubicazione_ordine ON config.tipi_ubicazione USING btree (ordine)` |
| pk_cfg_tipi_ubicazione | `CREATE UNIQUE INDEX pk_cfg_tipi_ubicazione ON config.tipi_ubicazione USING btree (id)` |
| uq_cfg_tipi_ubicazione_codice | `CREATE UNIQUE INDEX uq_cfg_tipi_ubicazione_codice ON config.tipi_ubicazione USING btree (codice)` |
| uq_cfg_tipi_ubicazione_codice_interno | `CREATE UNIQUE INDEX uq_cfg_tipi_ubicazione_codice_interno ON config.tipi_ubicazione USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_ubicazione_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_tipi_ubicazione_a10_ubicazioni_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'ubicazioni', 'tipo_id', 'id')` |
| trg_tipi_ubicazione_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_tipi_ubicazione_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

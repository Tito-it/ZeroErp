{% include-markdown "it/dbzero/config/manual/assets_ownership.md" %}
# 📚 Tabella `assets_ownership`

> 📝 **Descrizione**
>
> Dominio proprietario asset.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_cfg_assets_ownership | id |
| UNIQUE | uq_cfg_assets_ownership_codice | codice |
| UNIQUE | uq_cfg_assets_ownership_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_cfg_assets_ownership_attivo | `CREATE INDEX ix_cfg_assets_ownership_attivo ON config.assets_ownership USING btree (attivo)` |
| pk_cfg_assets_ownership | `CREATE UNIQUE INDEX pk_cfg_assets_ownership ON config.assets_ownership USING btree (id)` |
| uq_cfg_assets_ownership_codice | `CREATE UNIQUE INDEX uq_cfg_assets_ownership_codice ON config.assets_ownership USING btree (codice)` |
| uq_cfg_assets_ownership_codice_interno | `CREATE UNIQUE INDEX uq_cfg_assets_ownership_codice_interno ON config.assets_ownership USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_assets_ownership_a10_assets_block_deact_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_prevent_deactivate_if_children('magazzino', 'assets', 'ownership_id', 'id', 'attivo')` |
| trg_assets_ownership_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_assets_ownership_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_assets_ownership_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/config/manual/assets_ownership.md" %}
# 📚 Tabella `assets_ownership`

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
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | character varying | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_cfg_assets_ownership | id |
| UNIQUE | uq_cfg_assets_ownership_codice | codice |
| UNIQUE | uq_cfg_assets_ownership_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_assets_ownership_codice_interno_upper | `CREATE INDEX ix_assets_ownership_codice_interno_upper ON config.assets_ownership USING btree (upper((codice_interno)::text))` |
| ix_assets_ownership_codice_upper | `CREATE INDEX ix_assets_ownership_codice_upper ON config.assets_ownership USING btree (upper((codice)::text))` |
| ix_assets_ownership_descrizione_upper | `CREATE INDEX ix_assets_ownership_descrizione_upper ON config.assets_ownership USING btree (upper((descrizione)::text))` |
| ix_cfg_assets_ownership_attivo | `CREATE INDEX ix_cfg_assets_ownership_attivo ON config.assets_ownership USING btree (attivo)` |
| pk_cfg_assets_ownership | `CREATE UNIQUE INDEX pk_cfg_assets_ownership ON config.assets_ownership USING btree (id)` |
| uq_cfg_assets_ownership_codice | `CREATE UNIQUE INDEX uq_cfg_assets_ownership_codice ON config.assets_ownership USING btree (codice)` |
| uq_cfg_assets_ownership_codice_interno | `CREATE UNIQUE INDEX uq_cfg_assets_ownership_codice_interno ON config.assets_ownership USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}

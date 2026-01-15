# 📚 Tabella `tipi_evento_assets`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_tipi_evento_assets | id |
| UNIQUE | uq_tipi_evento_assets_codice | codice |
| UNIQUE | uq_tipi_evento_assets_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_evento_assets_attivo | `CREATE INDEX ix_tipi_evento_assets_attivo ON config.tipi_evento_assets USING btree (attivo)` |
| pk_tipi_evento_assets | `CREATE UNIQUE INDEX pk_tipi_evento_assets ON config.tipi_evento_assets USING btree (id)` |
| uq_tipi_evento_assets_codice | `CREATE UNIQUE INDEX uq_tipi_evento_assets_codice ON config.tipi_evento_assets USING btree (codice)` |
| uq_tipi_evento_assets_codice_interno | `CREATE UNIQUE INDEX uq_tipi_evento_assets_codice_interno ON config.tipi_evento_assets USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_evento_assets_a10_lock_columns_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')` |
| trg_tipi_evento_assets_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

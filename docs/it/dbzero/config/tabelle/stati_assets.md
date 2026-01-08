{% include-markdown "it/dbzero/config/manual/stati_assets.md" %}
# 📚 Tabella `stati_assets`

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
| PRIMARY KEY | pk_stati_assets | id |
| UNIQUE | uq_stati_assets_codice | codice |
| UNIQUE | uq_stati_assets_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_assets_attivo | `CREATE INDEX ix_stati_assets_attivo ON config.stati_assets USING btree (attivo)` |
| ix_stati_assets_codice_interno_upper | `CREATE INDEX ix_stati_assets_codice_interno_upper ON config.stati_assets USING btree (upper((codice_interno)::text))` |
| ix_stati_assets_codice_upper | `CREATE INDEX ix_stati_assets_codice_upper ON config.stati_assets USING btree (upper((codice)::text))` |
| ix_stati_assets_descrizione_upper | `CREATE INDEX ix_stati_assets_descrizione_upper ON config.stati_assets USING btree (upper((descrizione)::text))` |
| pk_stati_assets | `CREATE UNIQUE INDEX pk_stati_assets ON config.stati_assets USING btree (id)` |
| uq_stati_assets_codice | `CREATE UNIQUE INDEX uq_stati_assets_codice ON config.stati_assets USING btree (codice)` |
| uq_stati_assets_codice_interno | `CREATE UNIQUE INDEX uq_stati_assets_codice_interno ON config.stati_assets USING btree (codice_interno)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_assets_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

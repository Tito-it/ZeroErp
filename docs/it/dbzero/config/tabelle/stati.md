{% include-markdown "it/dbzero/config/manual/stati.md" %}
# 📚 Tabella `stati`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.stati_id_seq'::regclass) |
| sigla_stato | character varying | YES |  |
| descrizione | character varying | NO |  |
| codice_iso2 | character | YES |  |
| codice_iso3 | character | YES |  |
| codice_telefonico | character varying | YES |  |
| continente | character varying | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_descrizione_stato | `CREATE INDEX ix_descrizione_stato ON config.stati USING btree (descrizione)` |
| ix_iso2 | `CREATE INDEX ix_iso2 ON config.stati USING btree (codice_iso2)` |
| ix_iso3 | `CREATE INDEX ix_iso3 ON config.stati USING btree (codice_iso3)` |
| ix_sigla_stato | `CREATE INDEX ix_sigla_stato ON config.stati USING btree (sigla_stato)` |
| ix_stato_utilizzo_jsonb | `CREATE INDEX ix_stato_utilizzo_jsonb ON config.stati USING btree (((extra_country ->> 'stato_utilizzo'::text)))` |
| pk_stati | `CREATE UNIQUE INDEX pk_stati ON config.stati USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_stati_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

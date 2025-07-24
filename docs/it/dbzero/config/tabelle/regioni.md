{% include-markdown "it/dbzero/config/manual/regioni.md" %}
# 📚 Tabella `regioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('regioni_id_seq'::regclass) |
| descrizione | character | NO |  |
| stato_id | integer | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_regioni_stato_id | stato_id |
| PRIMARY KEY | pk_regioni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_descrizione_regione | `CREATE INDEX ix_descrizione_regione ON config.regioni USING btree (descrizione)` |
| ix_regioni_stato_id | `CREATE INDEX ix_regioni_stato_id ON config.regioni USING btree (stato_id)` |
| pk_regioni | `CREATE UNIQUE INDEX pk_regioni ON config.regioni USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_regioni_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
{% include-markdown "it/dbzero/config/manual/toponomastica.md" %}
# 📚 Tabella `toponomastica`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('config.toponomastica_id_seq'::regclass) |
| descrizione | character varying | NO |  |
| stato_id | integer | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_toponomastica_stato_id | stato_id |
| PRIMARY KEY | pk_toponomastica | id |
| UNIQUE | uq_toponomastica_descrizione | descrizione |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| idx_toponomastica_stato_id | `CREATE INDEX idx_toponomastica_stato_id ON config.toponomastica USING btree (stato_id)` |
| pk_toponomastica | `CREATE UNIQUE INDEX pk_toponomastica ON config.toponomastica USING btree (id)` |
| uq_toponomastica_descrizione | `CREATE UNIQUE INDEX uq_toponomastica_descrizione ON config.toponomastica USING btree (descrizione)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_toponomastica_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
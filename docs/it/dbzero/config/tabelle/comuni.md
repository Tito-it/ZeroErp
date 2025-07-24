{% include-markdown "it/dbzero/config/manual/comuni.md" %}
# 📚 Tabella `comuni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('comuni_id_seq'::regclass) |
| descrizione | character varying | NO | ''::character varying |
| provincia_id | integer | YES |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |
| storicizza | boolean | NO | false |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_provincia | provincia_id |
| PRIMARY KEY | pk_comuni | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_comuni_provincia_id | `CREATE INDEX ix_comuni_provincia_id ON config.comuni USING btree (provincia_id)` |
| ix_descrizione_comune | `CREATE INDEX ix_descrizione_comune ON config.comuni USING btree (descrizione)` |
| pk_comuni | `CREATE UNIQUE INDEX pk_comuni ON config.comuni USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_comuni_ins_upd_gen_tx_id | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_comuni_ins_upd_gen_tx_id | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_upd_comuni_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
| trg_z90_comuni_upd_dlt_storico | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('comune_id')` |
| trg_z90_comuni_upd_dlt_storico | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_dlt_storico_generic('comune_id')` |
{% include-markdown "it/dbzero/config/manual/codici_postali.md" %}
# 📚 Tabella `codici_postali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('codici_postali_id_seq'::regclass) |
| codice_postale | character | NO |  |
| comune_id | integer | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_codici_postali_comune_id | comune_id |
| PRIMARY KEY | pk_codici_postali | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_codici_postali_codice | `CREATE INDEX ix_codici_postali_codice ON config.codici_postali USING btree (codice_postale)` |
| ix_codici_postali_comune_id | `CREATE INDEX ix_codici_postali_comune_id ON config.codici_postali USING btree (comune_id)` |
| pk_codici_postali | `CREATE UNIQUE INDEX pk_codici_postali ON config.codici_postali USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_upd_codici_postali_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
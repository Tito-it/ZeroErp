{% include-markdown "it/dbzero/config/manual/regioni.md" %}
# 📚 Tabella `regioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| descrizione | character | NO |  |
| stato_id | integer | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
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
| ix_stato_regione | `CREATE INDEX ix_stato_regione ON config.regioni USING btree (stato_id)` |
| pk_regioni | `CREATE UNIQUE INDEX pk_regioni ON config.regioni USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_regioni_ins_upd_clean_fields | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_regioni_ins_upd_clean_fields()` |
| trg_regioni_ins_upd_clean_fields | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_regioni_ins_upd_clean_fields()` |
| trg_regioni_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/config/manual/regioni.md" %}
# 📚 Tabella `regioni`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| descrizione | character | NO |  |
| stato_id | integer | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
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
| trg_regioni_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_regioni_normalize_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_regioni_normalize()` |
| trg_regioni_normalize_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_regioni_normalize()` |

---
{% include-markdown "signature-core.md" %}

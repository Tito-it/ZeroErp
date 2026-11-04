{% include-markdown "it/dbzero/config/manual/codici_postali.md" %}
# 📚 Tabella `codici_postali`

> 📝 **Descrizione**
>
> Codici di avviamento postale associati ai comuni (normalizzati)

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| comune_id | integer | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_codici_postali_comune_id | comune_id |
| PRIMARY KEY | pk_codici_postali | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_codici_postali_codice | `CREATE INDEX ix_codici_postali_codice ON config.codici_postali USING btree (codice)` |
| ix_config_codici_postali_comune_id | `CREATE INDEX ix_config_codici_postali_comune_id ON config.codici_postali USING btree (comune_id)` |
| pk_codici_postali | `CREATE UNIQUE INDEX pk_codici_postali ON config.codici_postali USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_codici_postali_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_codici_postali_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_codici_postali_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_codici_postali_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

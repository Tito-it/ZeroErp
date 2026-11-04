{% include-markdown "it/dbzero/config/manual/ambiti.md" %}
# 📚 Tabella `ambiti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying(50) | NO |  |
| descrizione | character varying(100) | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_ambiti_descrizione_non_vuota |  |
| PRIMARY KEY | pk_ambiti | id |
| UNIQUE | uq_ambiti_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ambiti_descrizione | `CREATE INDEX ix_ambiti_descrizione ON config.ambiti USING btree (descrizione)` |
| ix_ambiti_extra_country_keys | `CREATE INDEX ix_ambiti_extra_country_keys ON config.ambiti USING btree (((extra_country ->> 'stato_utilizzo'::text)), ((extra_country ->> 'settore'::text)), ((extra_country ->> 'codice_ambito'::text)))` |
| pk_ambiti | `CREATE UNIQUE INDEX pk_ambiti ON config.ambiti USING btree (id)` |
| uq_ambiti_codice | `CREATE UNIQUE INDEX uq_ambiti_codice ON config.ambiti USING btree (codice)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ambiti_a15_codice_maiuscolo_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_ambiti_a15_codice_maiuscolo_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_codice_maiuscolo()` |
| trg_ambiti_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_ambiti_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

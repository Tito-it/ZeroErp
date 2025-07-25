# 📚 Tabella `ambiti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO | nextval('ambiti_id_seq'::regclass) |
| codice | character | NO |  |
| descrizione | character | NO |  |
| data_insert | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_insert | character varying | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | CURRENT_TIMESTAMP |
| user_update | character varying | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
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
| trg_upd_ambiti_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/config/manual/province.md" %}
# 📚 Tabella `province`

> 📝 **Descrizione**
>
> Province con codici ISTAT, regione e collegamento a provincia di riferimento per accise

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| descrizione | character varying(80) | NO |  |
| sigla | character varying(10) | NO |  |
| regione_id | integer | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_province_descrizione_non_vuota |  |
| CHECK | chk_province_sigla_forma |  |
| FOREIGN KEY | fk_province_regione_id | regione_id |
| PRIMARY KEY | pk_province | id |
| UNIQUE | uq_province_sigla | sigla |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_config_province_regione_id | `CREATE INDEX ix_config_province_regione_id ON config.province USING btree (regione_id)` |
| ix_descrizione_provincia | `CREATE INDEX ix_descrizione_provincia ON config.province USING btree (descrizione)` |
| ix_province_stato_utilizzo_jsonb | `CREATE INDEX ix_province_stato_utilizzo_jsonb ON config.province USING btree (((extra_country ->> 'stato_utilizzo'::text)))` |
| pk_province | `CREATE UNIQUE INDEX pk_province ON config.province USING btree (id)` |
| uq_province_sigla | `CREATE UNIQUE INDEX uq_province_sigla ON config.province USING btree (sigla)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_province_a10_guard_sigla_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_province_guard_sigla()` |
| trg_province_a10_guard_sigla_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_province_guard_sigla()` |
| trg_province_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_province_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

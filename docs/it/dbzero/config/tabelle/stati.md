{% include-markdown "it/dbzero/config/manual/stati.md" %}
# 📚 Tabella `stati`

> 📝 **Descrizione**
>
> Stati (ex nazioni), inclusi codici catastali, ISO, telefonici e continente

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| sigla_stato | character varying(10) | YES |  |
| descrizione | character varying(100) | NO |  |
| codice_iso2 | character(2) | YES |  |
| codice_iso3 | character(3) | YES |  |
| codice_telefonico | character varying(10) | YES |  |
| continente | character varying(50) | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| extra_country | jsonb | YES |  |
| catalogo_comuni_completo | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_descrizione_stato | `CREATE INDEX ix_descrizione_stato ON config.stati USING btree (descrizione)` |
| ix_iso2 | `CREATE INDEX ix_iso2 ON config.stati USING btree (codice_iso2)` |
| ix_iso3 | `CREATE INDEX ix_iso3 ON config.stati USING btree (codice_iso3)` |
| ix_sigla_stato | `CREATE INDEX ix_sigla_stato ON config.stati USING btree (sigla_stato)` |
| ix_stato_utilizzo_jsonb | `CREATE INDEX ix_stato_utilizzo_jsonb ON config.stati USING btree (((extra_country ->> 'stato_utilizzo'::text)))` |
| pk_stati | `CREATE UNIQUE INDEX pk_stati ON config.stati USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_stati_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

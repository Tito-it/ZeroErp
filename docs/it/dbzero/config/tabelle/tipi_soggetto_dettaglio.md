{% include-markdown "it/dbzero/config/manual/tipi_soggetto_dettaglio.md" %}
# 📚 Tabella `tipi_soggetto_dettaglio`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('config.tipi_soggetto_dettaglio_id_seq'::regclass) |
| tipo_soggetto_id | character varying | NO |  |
| stato_iso2 | character varying | NO |  |
| cod_int_tipo_soggetto | character varying | NO |  |
| descrizione_locale | character varying | YES |  |
| formato_cf | character varying | YES |  |
| formato_piva | character varying | YES |  |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | YES |  |
| data_update | timestamp with time zone | YES |  |
| stato_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_tipi_soggetto_dettaglio_stato_id | stato_id |
| FOREIGN KEY | fk_tipi_soggetto_dettaglio_tipi_soggetto_id | tipo_soggetto_id |
| PRIMARY KEY | pk_tipi_soggetto_dettaglio | id |
| UNIQUE | uq_tipi_soggetto_dettaglio_cod_int_tipo_soggetto | cod_int_tipo_soggetto |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_soggetto_dettaglio_stato_id | `CREATE INDEX ix_tipi_soggetto_dettaglio_stato_id ON config.tipi_soggetto_dettaglio USING btree (stato_id)` |
| ix_tipi_soggetto_dettaglio_tipo_soggetto_id | `CREATE INDEX ix_tipi_soggetto_dettaglio_tipo_soggetto_id ON config.tipi_soggetto_dettaglio USING btree (tipo_soggetto_id)` |
| pk_tipi_soggetto_dettaglio | `CREATE UNIQUE INDEX pk_tipi_soggetto_dettaglio ON config.tipi_soggetto_dettaglio USING btree (id)` |
| uq_tipi_soggetto_dettaglio_cod_int_tipo_soggetto | `CREATE UNIQUE INDEX uq_tipi_soggetto_dettaglio_cod_int_tipo_soggetto ON config.tipi_soggetto_dettaglio USING btree (cod_int_tipo_soggetto)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_sync_stato_iso2 | BEFORE | INSERT | `EXECUTE FUNCTION config.trgfn_sync_stato_iso2()` |
| trg_sync_stato_iso2 | BEFORE | UPDATE | `EXECUTE FUNCTION config.trgfn_sync_stato_iso2()` |
| trg_tipi_soggetto_dettaglio_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('cod_int_tipo_soggetto', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_overrides_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
---
{% include-markdown "signature-core.md" %}

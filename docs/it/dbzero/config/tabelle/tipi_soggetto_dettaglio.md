{% include-markdown "it/dbzero/config/manual/tipi_soggetto_dettaglio.md" %}
# 📚 Tabella `tipi_soggetto_dettaglio`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('config.tipi_soggetto_dettaglio_id_seq'::regclass) |
| id_tipo_soggetto | character varying | NO |  |
| stato_iso | character varying | NO |  |
| cod_int_tipo_soggetto | character varying | NO |  |
| descrizione_locale | character varying | YES |  |
| formato_cf | character varying | YES |  |
| formato_piva | character varying | YES |  |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | YES |  |
| data_update | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | tipi_soggetto_dettaglio_pkey | id |
| UNIQUE | tipi_soggetto_dettaglio_cod_int_tipo_soggetto_key | cod_int_tipo_soggetto |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| tipi_soggetto_dettaglio_cod_int_tipo_soggetto_key | `CREATE UNIQUE INDEX tipi_soggetto_dettaglio_cod_int_tipo_soggetto_key ON config.tipi_soggetto_dettaglio USING btree (cod_int_tipo_soggetto)` |
| tipi_soggetto_dettaglio_pkey | `CREATE UNIQUE INDEX tipi_soggetto_dettaglio_pkey ON config.tipi_soggetto_dettaglio USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_soggetto_dettaglio_upd_lock_codiceinterno | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_lock_columns('cod_int_tipo_soggetto', 'CODICE_NON_MODIFICABILE')` |
| trg_upd_overrides_audit_data_user | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_upd_audit_data_user_generic()` |
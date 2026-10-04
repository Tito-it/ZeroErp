{% include-markdown "it/dbzero/storico/manual/tipi_soggetto_dettaglio_tipi_indirizzo.md" %}
# 📚 Tabella `tipi_soggetto_dettaglio_tipi_indirizzo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.tipi_soggetto_dettaglio_tipi_indirizzo_id_seq'::regclass) |
| tipi_soggetto_dettaglio_tipi_indirizzo_id | bigint | NO |  |
| change_type | character(1) | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |
| origine_schema | text | NO |  |
| scope_emittente_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_tipi_soggetto_dettaglio_tipi_indirizzo | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_soggetto_dettaglio_tipi_indirizzo_scope_ef | `CREATE INDEX ix_tipi_soggetto_dettaglio_tipi_indirizzo_scope_ef ON storico.tipi_soggetto_dettaglio_tipi_indirizzo USING btree (scope_emittente_fiscale_id)` |
| ix_tipi_soggetto_dettaglio_tipi_indirizzo_tipi_soggetto_dettagl | `CREATE INDEX ix_tipi_soggetto_dettaglio_tipi_indirizzo_tipi_soggetto_dettagl ON storico.tipi_soggetto_dettaglio_tipi_indirizzo USING btree (tipi_soggetto_dettaglio_tipi_indirizzo_id)` |
| pk_storico_tipi_soggetto_dettaglio_tipi_indirizzo | `CREATE UNIQUE INDEX pk_storico_tipi_soggetto_dettaglio_tipi_indirizzo ON storico.tipi_soggetto_dettaglio_tipi_indirizzo USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_tipi_soggetto_dettaglio_tipi_indirizzo_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_tipi_soggetto_dettaglio_tipi_indirizzo_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

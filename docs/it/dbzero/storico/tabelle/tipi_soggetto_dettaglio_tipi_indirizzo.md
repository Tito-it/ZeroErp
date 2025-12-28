# 📚 Tabella `tipi_soggetto_dettaglio_tipi_indirizzo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.tipi_soggetto_dettaglio_tipi_indirizzo_id_seq'::regclass) |
| tipi_soggetto_dettaglio_tipi_indirizzo_id | bigint | NO |  |
| change_type | character | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_tipi_soggetto_dettaglio_tipi_indirizzo | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_soggetto_dettaglio_tipi_indirizzo_tipi_soggetto_dettagl | `CREATE INDEX ix_tipi_soggetto_dettaglio_tipi_indirizzo_tipi_soggetto_dettagl ON storico.tipi_soggetto_dettaglio_tipi_indirizzo USING btree (tipi_soggetto_dettaglio_tipi_indirizzo_id)` |
| pk_storico_tipi_soggetto_dettaglio_tipi_indirizzo | `CREATE UNIQUE INDEX pk_storico_tipi_soggetto_dettaglio_tipi_indirizzo ON storico.tipi_soggetto_dettaglio_tipi_indirizzo USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/config/manual/tipi_soggetto_dettaglio_tipi_indirizzo.md" %}
# 📚 Tabella `tipi_soggetto_dettaglio_tipi_indirizzo`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| tipo_soggetto_dettaglio_id | bigint | NO |  |
| tipo_indirizzo_id | integer | NO |  |
| obbligatorio | boolean | NO | false |
| valido_dal | date | YES |  |
| valido_al | date | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| user_insert | text | NO | CURRENT_USER |
| user_update | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | NO | now() |
| storicizza | boolean | NO | false |
| fallback_tipo_indirizzo_id | integer | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tsd_tipi_indirizzo_fallback_not_self |  |
| CHECK | chk_tsd_tipi_indirizzo_validita |  |
| FOREIGN KEY | fk_tsd_tipi_indirizzo_fallback_tipo | fallback_tipo_indirizzo_id |
| FOREIGN KEY | fk_tsd_tipi_indirizzo_tipo_indirizzo | tipo_indirizzo_id |
| FOREIGN KEY | fk_tsd_tipi_indirizzo_tipo_soggetto_dettaglio | tipo_soggetto_dettaglio_id |
| PRIMARY KEY | pk_tipi_soggetto_dettaglio_tipi_indirizzo | id |
| UNIQUE | uq_tipi_soggetto_dettaglio_tipi_indirizzo_tipo_soggetto_tipo | tipo_soggetto_dettaglio_id, tipo_indirizzo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tsd_tipi_indirizzo_tipo_indirizzo | `CREATE INDEX ix_tsd_tipi_indirizzo_tipo_indirizzo ON config.tipi_soggetto_dettaglio_tipi_indirizzo USING btree (tipo_indirizzo_id)` |
| ix_tsd_tipi_indirizzo_tipo_soggetto_dettaglio | `CREATE INDEX ix_tsd_tipi_indirizzo_tipo_soggetto_dettaglio ON config.tipi_soggetto_dettaglio_tipi_indirizzo USING btree (tipo_soggetto_dettaglio_id)` |
| pk_tipi_soggetto_dettaglio_tipi_indirizzo | `CREATE UNIQUE INDEX pk_tipi_soggetto_dettaglio_tipi_indirizzo ON config.tipi_soggetto_dettaglio_tipi_indirizzo USING btree (id)` |
| uq_tipi_soggetto_dettaglio_tipi_indirizzo_tipo_soggetto_tipo | `CREATE UNIQUE INDEX uq_tipi_soggetto_dettaglio_tipi_indirizzo_tipo_soggetto_tipo ON config.tipi_soggetto_dettaglio_tipi_indirizzo USING btree (tipo_soggetto_dettaglio_id, tipo_indirizzo_id)` |

---
{% include-markdown "signature-core.md" %}

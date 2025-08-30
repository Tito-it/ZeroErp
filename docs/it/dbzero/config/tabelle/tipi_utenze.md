# 📚 Tabella `tipi_utenze`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | NO |  |
| iva_id | integer | YES |  |
| utility_id | integer | YES |  |
| tipo_pdr_std | character | NO | '0'::bpchar |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_tipi_utenze_tipo_pdr_std |  |
| FOREIGN KEY | fk_tipi_utenze_iva | iva_id |
| FOREIGN KEY | fk_tipi_utenze_utility | utility_id |
| PRIMARY KEY | pk_tipi_utenze | id |
| UNIQUE | uq_tipi_utenze_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_tipi_utenze_descrizione | `CREATE INDEX ix_tipi_utenze_descrizione ON config.tipi_utenze USING btree (descrizione)` |
| ix_tipi_utenze_iva_id | `CREATE INDEX ix_tipi_utenze_iva_id ON config.tipi_utenze USING btree (iva_id)` |
| ix_tipi_utenze_utility_id | `CREATE INDEX ix_tipi_utenze_utility_id ON config.tipi_utenze USING btree (utility_id)` |
| pk_tipi_utenze | `CREATE UNIQUE INDEX pk_tipi_utenze ON config.tipi_utenze USING btree (id)` |
| uq_tipi_utenze_codice | `CREATE UNIQUE INDEX uq_tipi_utenze_codice ON config.tipi_utenze USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}

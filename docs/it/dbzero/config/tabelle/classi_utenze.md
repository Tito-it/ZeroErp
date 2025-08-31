# 📚 Tabella `classi_utenze`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | NO |  |
| descrizione_breve | character varying | NO |  |
| tipo_utenza_id | integer | YES |  |
| categoria_accisa_id | integer | YES |  |
| pot_contratto_min_ee | numeric | NO |  |
| pot_contratto_max_ee | numeric | NO |  |
| tipi_tariffa_ee_id | integer | YES |  |
| tipo_pod | character varying | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_classi_utenze_tipo_pod |  |
| FOREIGN KEY | fk_classi_utenze_categoria_accisa | categoria_accisa_id |
| FOREIGN KEY | fk_classi_utenze_tipi_tariffa_ee | tipi_tariffa_ee_id |
| FOREIGN KEY | fk_classi_utenze_tipi_utenze | tipo_utenza_id |
| PRIMARY KEY | pk_classi_utenze | id |
| UNIQUE | uq_classi_utenze_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_classi_utenze_categoria_accisa_id | `CREATE INDEX ix_classi_utenze_categoria_accisa_id ON config.classi_utenze USING btree (categoria_accisa_id)` |
| ix_classi_utenze_descrizione | `CREATE INDEX ix_classi_utenze_descrizione ON config.classi_utenze USING btree (descrizione)` |
| ix_classi_utenze_tipi_tariffa_ee_id | `CREATE INDEX ix_classi_utenze_tipi_tariffa_ee_id ON config.classi_utenze USING btree (tipi_tariffa_ee_id)` |
| ix_classi_utenze_tipo_utenza_id | `CREATE INDEX ix_classi_utenze_tipo_utenza_id ON config.classi_utenze USING btree (tipo_utenza_id)` |
| pk_classi_utenze | `CREATE UNIQUE INDEX pk_classi_utenze ON config.classi_utenze USING btree (id)` |
| uq_classi_utenze_codice | `CREATE UNIQUE INDEX uq_classi_utenze_codice ON config.classi_utenze USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/config/manual/stati_sdi.md" %}
# 📚 Tabella `stati_sdi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| codice_interno | character varying | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_sdi | id |
| UNIQUE | uq_stati_sdi_codice | codice |
| UNIQUE | uq_stati_sdi_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_sdi_attivo | `CREATE INDEX ix_stati_sdi_attivo ON config.stati_sdi USING btree (attivo)` |
| pk_stati_sdi | `CREATE UNIQUE INDEX pk_stati_sdi ON config.stati_sdi USING btree (id)` |
| uq_stati_sdi_codice | `CREATE UNIQUE INDEX uq_stati_sdi_codice ON config.stati_sdi USING btree (codice)` |
| uq_stati_sdi_codice_interno | `CREATE UNIQUE INDEX uq_stati_sdi_codice_interno ON config.stati_sdi USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}

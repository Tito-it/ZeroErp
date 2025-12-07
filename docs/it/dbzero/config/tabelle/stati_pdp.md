{% include-markdown "it/dbzero/config/manual/stati_pdp.md" %}
# 📚 Tabella `stati_pdp`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| ordine | integer | NO | 10 |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_stati_pdp | id |
| UNIQUE | uq_stati_pdp_codice | codice |
| UNIQUE | uq_stati_pdp_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_pdp_attivo_ordine | `CREATE INDEX ix_stati_pdp_attivo_ordine ON config.stati_pdp USING btree (attivo, ordine)` |
| pk_stati_pdp | `CREATE UNIQUE INDEX pk_stati_pdp ON config.stati_pdp USING btree (id)` |
| uq_stati_pdp_codice | `CREATE UNIQUE INDEX uq_stati_pdp_codice ON config.stati_pdp USING btree (codice)` |
| uq_stati_pdp_codice_interno | `CREATE UNIQUE INDEX uq_stati_pdp_codice_interno ON config.stati_pdp USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}

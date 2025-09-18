# 📚 Tabella `modalita_addebito_trasporto`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice_interno | character varying | NO |  |
| codice | character varying | NO |  |
| descrizione | character varying | YES |  |
| attivo | boolean | NO | true |
| ordine | smallint | YES |  |
| meta | jsonb | NO | '{}'::jsonb |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_modalita_addebito_trasporto | id |
| UNIQUE | uq_modalita_addebito_trasporto_codice | codice |
| UNIQUE | uq_modalita_addebito_trasporto_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_modalita_addebito_trasporto | `CREATE UNIQUE INDEX pk_modalita_addebito_trasporto ON config.modalita_addebito_trasporto USING btree (id)` |
| uq_modalita_addebito_trasporto_codice | `CREATE UNIQUE INDEX uq_modalita_addebito_trasporto_codice ON config.modalita_addebito_trasporto USING btree (codice)` |
| uq_modalita_addebito_trasporto_codice_interno | `CREATE UNIQUE INDEX uq_modalita_addebito_trasporto_codice_interno ON config.modalita_addebito_trasporto USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}

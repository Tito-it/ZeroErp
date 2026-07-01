{% include-markdown "it/dbzero/config/manual/esiti_flussi_pratiche.md" %}
# 📚 Tabella `esiti_flussi_pratiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | text | NO |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_esiti_flussi_pratiche | id |
| UNIQUE | uq_esiti_flussi_pratiche_codice | codice |
| UNIQUE | uq_esiti_flussi_pratiche_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_esiti_flussi_pratiche | `CREATE UNIQUE INDEX pk_esiti_flussi_pratiche ON config.esiti_flussi_pratiche USING btree (id)` |
| uq_esiti_flussi_pratiche_codice | `CREATE UNIQUE INDEX uq_esiti_flussi_pratiche_codice ON config.esiti_flussi_pratiche USING btree (codice)` |
| uq_esiti_flussi_pratiche_codice_interno | `CREATE UNIQUE INDEX uq_esiti_flussi_pratiche_codice_interno ON config.esiti_flussi_pratiche USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}

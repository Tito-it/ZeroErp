{% include-markdown "it/dbzero/pratiche/manual/tipi_prestazione.md" %}
# 📚 Tabella `tipi_prestazione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | text | NO |  |
| categoria | character varying | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| pre_attivazione | boolean | NO | true |
| post_attivazione | boolean | NO | true |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_pratiche_tipi_prestazione | id |
| UNIQUE | uq_pratiche_tipi_prestazione_codice | codice |
| UNIQUE | uq_pratiche_tipi_prestazione_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_pratiche_tipi_prestazione | `CREATE UNIQUE INDEX pk_pratiche_tipi_prestazione ON pratiche.tipi_prestazione USING btree (id)` |
| uq_pratiche_tipi_prestazione_codice | `CREATE UNIQUE INDEX uq_pratiche_tipi_prestazione_codice ON pratiche.tipi_prestazione USING btree (codice)` |
| uq_pratiche_tipi_prestazione_codice_interno | `CREATE UNIQUE INDEX uq_pratiche_tipi_prestazione_codice_interno ON pratiche.tipi_prestazione USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}

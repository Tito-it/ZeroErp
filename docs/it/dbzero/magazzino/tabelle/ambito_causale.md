# 📚 Tabella `ambito_causale`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | character varying | NO |  |
| codice_interno | character varying | NO |  |
| descrizione | character varying | NO |  |
| ordine | smallint | NO | 0 |
| attivo | boolean | NO | true |
| extra_info | jsonb | YES | '{}'::jsonb |
| tx_id | uuid | YES |  |
| user_insert | text | YES |  |
| user_update | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| data_update | timestamp with time zone | YES |  |
| storicizza | boolean | NO | false |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_mag_ambito_causale | id |
| UNIQUE | uq_mag_ambito_causale_codice | codice |
| UNIQUE | uq_mag_ambito_causale_codice_interno | codice_interno |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_mag_ambito_causale | `CREATE UNIQUE INDEX pk_mag_ambito_causale ON magazzino.ambito_causale USING btree (id)` |
| uq_mag_ambito_causale_codice | `CREATE UNIQUE INDEX uq_mag_ambito_causale_codice ON magazzino.ambito_causale USING btree (codice)` |
| uq_mag_ambito_causale_codice_interno | `CREATE UNIQUE INDEX uq_mag_ambito_causale_codice_interno ON magazzino.ambito_causale USING btree (codice_interno)` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/vendite/manual/area_geografica_fatturazione.md" %}
# 📚 Tabella `area_geografica_fatturazione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| codice | text | NO |  |
| descrizione | text | YES |  |
| attivo | boolean | NO | true |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_area_geografica_fatturazione | id |
| UNIQUE | uq_area_geografica_fatturazione_codice | codice |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_area_geografica_fatturazione | `CREATE UNIQUE INDEX pk_area_geografica_fatturazione ON vendite.area_geografica_fatturazione USING btree (id)` |
| uq_area_geografica_fatturazione_codice | `CREATE UNIQUE INDEX uq_area_geografica_fatturazione_codice ON vendite.area_geografica_fatturazione USING btree (codice)` |

---
{% include-markdown "signature-core.md" %}

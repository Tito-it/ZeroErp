{% include-markdown "it/dbzero/vendite/manual/offerte_commerciali_utilities.md" %}
# 📚 Tabella `offerte_commerciali_utilities`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| offerta_id | bigint | NO |  |
| istanza_utility_id | bigint | NO |  |
| utility_id | integer | NO |  |
| istanza_dati_precontrattuali_id | bigint | YES |  |
| classe_utenza_id | integer | YES |  |
| tipo_utenza_id | integer | YES |  |
| param_1_num | numeric | YES |  |
| param_2_txt | character varying | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| tx_id | uuid | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | YES | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_offerte_utilities_classe_utenza | classe_utenza_id |
| FOREIGN KEY | fk_offerte_utilities_istanza_dati_precontrattuali | istanza_dati_precontrattuali_id |
| FOREIGN KEY | fk_offerte_utilities_istanza_utility | istanza_utility_id |
| FOREIGN KEY | fk_offerte_utilities_offerta | offerta_id |
| FOREIGN KEY | fk_offerte_utilities_tipo_utenza | tipo_utenza_id |
| FOREIGN KEY | fk_offerte_utilities_utility | utility_id |
| PRIMARY KEY | pk_offerte_commerciali_utilities | id |
| UNIQUE | uq_offerte_commerciali_utilities_offerta_id | offerta_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_offerte_commerciali_utilities | `CREATE UNIQUE INDEX pk_offerte_commerciali_utilities ON vendite.offerte_commerciali_utilities USING btree (id)` |
| uq_offerte_commerciali_utilities_offerta_id | `CREATE UNIQUE INDEX uq_offerte_commerciali_utilities_offerta_id ON vendite.offerte_commerciali_utilities USING btree (offerta_id)` |

---
{% include-markdown "signature-core.md" %}

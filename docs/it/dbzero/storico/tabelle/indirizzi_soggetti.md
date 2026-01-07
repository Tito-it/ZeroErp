# 📚 Tabella `indirizzi_soggetti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.indirizzi_soggetti_id_seq'::regclass) |
| indirizzi_soggetti_id | bigint | NO |  |
| change_type | character | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_indirizzi_soggetti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_indirizzi_soggetti_indirizzi_soggetti_id_fk | `CREATE INDEX ix_indirizzi_soggetti_indirizzi_soggetti_id_fk ON storico.indirizzi_soggetti USING btree (indirizzi_soggetti_id)` |
| pk_storico_indirizzi_soggetti | `CREATE UNIQUE INDEX pk_storico_indirizzi_soggetti ON storico.indirizzi_soggetti USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

# 📚 Tabella `commesse_sorgenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.commesse_sorgenti_id_seq'::regclass) |
| commesse_sorgenti_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_commesse_sorgenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_commesse_sorgenti_commesse_sorgenti_id_fk | `CREATE INDEX ix_commesse_sorgenti_commesse_sorgenti_id_fk ON storico.commesse_sorgenti USING btree (commesse_sorgenti_id)` |
| pk_storico_commesse_sorgenti | `CREATE UNIQUE INDEX pk_storico_commesse_sorgenti ON storico.commesse_sorgenti USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

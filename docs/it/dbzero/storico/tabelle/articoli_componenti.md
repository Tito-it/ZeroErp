# 📚 Tabella `articoli_componenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.articoli_componenti_id_seq'::regclass) |
| articoli_componenti_id | uuid | NO |  |
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
| PRIMARY KEY | pk_storico_articoli_componenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_componenti_articoli_componenti_id_fk | `CREATE INDEX ix_articoli_componenti_articoli_componenti_id_fk ON storico.articoli_componenti USING btree (articoli_componenti_id)` |
| pk_storico_articoli_componenti | `CREATE UNIQUE INDEX pk_storico_articoli_componenti ON storico.articoli_componenti USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

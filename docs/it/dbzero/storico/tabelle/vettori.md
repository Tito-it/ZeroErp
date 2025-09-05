# 📚 Tabella `vettori`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.vettori_id_seq'::regclass) |
| vettori_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_vettori | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vettori_vettori_id_fk | `CREATE INDEX ix_vettori_vettori_id_fk ON storico.vettori USING btree (vettori_id)` |
| pk_storico_vettori | `CREATE UNIQUE INDEX pk_storico_vettori ON storico.vettori USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

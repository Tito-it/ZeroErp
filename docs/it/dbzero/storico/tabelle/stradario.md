{% include-markdown "it/dbzero/storico/manual/stradario.md" %}
# 📚 Tabella `stradario`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.stradario_id_seq1'::regclass) |
| stradario_id | integer | NO |  |
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
| PRIMARY KEY | pk_storico_stradario | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stradario_stradario_id_fk | `CREATE INDEX ix_stradario_stradario_id_fk ON storico.stradario USING btree (stradario_id)` |
| pk_storico_stradario | `CREATE UNIQUE INDEX pk_storico_stradario ON storico.stradario USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

# 📚 Tabella `fatture_indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.fatture_indirizzi_id_seq'::regclass) |
| fatture_indirizzi_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_fatture_indirizzi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_indirizzi_fatture_indirizzi_id_fk | `CREATE INDEX ix_fatture_indirizzi_fatture_indirizzi_id_fk ON storico.fatture_indirizzi USING btree (fatture_indirizzi_id)` |
| pk_storico_fatture_indirizzi | `CREATE UNIQUE INDEX pk_storico_fatture_indirizzi ON storico.fatture_indirizzi USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

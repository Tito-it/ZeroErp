{% include-markdown "it/dbzero/storico/manual/indirizzi.md" %}
# 📚 Tabella `indirizzi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | integer | NO |  |
| valid_from | timestamp with time zone | NO | CURRENT_DATE |
| valid_to | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | YES | now() |
| user_insert | character varying | YES | CURRENT_USER |
| indirizzo_id | integer | YES |  |
| snapshot | jsonb | NO |  |
| tipo_operazione | smallint | NO |  |
| tx_id | uuid | YES |  |
| change_type | character | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_indirizzi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_indirizzi | `CREATE UNIQUE INDEX pk_indirizzi ON storico.indirizzi USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

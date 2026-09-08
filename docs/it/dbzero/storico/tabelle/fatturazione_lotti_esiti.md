# 📚 Tabella `fatturazione_lotti_esiti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.fatturazione_lotti_esiti_id_seq'::regclass) |
| fatturazione_lotti_esiti_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_fatturazione_lotti_esiti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatturazione_lotti_esiti_fatturazione_lotti_esiti_id_fk | `CREATE INDEX ix_fatturazione_lotti_esiti_fatturazione_lotti_esiti_id_fk ON storico.fatturazione_lotti_esiti USING btree (fatturazione_lotti_esiti_id)` |
| pk_storico_fatturazione_lotti_esiti | `CREATE UNIQUE INDEX pk_storico_fatturazione_lotti_esiti ON storico.fatturazione_lotti_esiti USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

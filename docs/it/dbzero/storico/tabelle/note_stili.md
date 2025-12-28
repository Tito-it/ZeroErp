# 📚 Tabella `note_stili`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.note_stili_id_seq'::regclass) |
| note_stili_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_note_stili | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_note_stili_note_stili_id_fk | `CREATE INDEX ix_note_stili_note_stili_id_fk ON storico.note_stili USING btree (note_stili_id)` |
| pk_storico_note_stili | `CREATE UNIQUE INDEX pk_storico_note_stili ON storico.note_stili USING btree (id)` |

---
{% include-markdown "signature-core.md" %}

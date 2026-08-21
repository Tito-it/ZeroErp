{% include-markdown "it/dbzero/storico/manual/note_flussi.md" %}
# 📚 Tabella `note_flussi`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.note_flussi_id_seq'::regclass) |
| note_flussi_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_note_flussi | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_note_flussi_note_flussi_id_fk | `CREATE INDEX ix_note_flussi_note_flussi_id_fk ON storico.note_flussi USING btree (note_flussi_id)` |
| pk_storico_note_flussi | `CREATE UNIQUE INDEX pk_storico_note_flussi ON storico.note_flussi USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_flussi_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_note_flussi_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

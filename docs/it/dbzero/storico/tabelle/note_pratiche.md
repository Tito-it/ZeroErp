# 📚 Tabella `note_pratiche`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.note_pratiche_id_seq'::regclass) |
| note_pratiche_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_note_pratiche | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_note_pratiche_note_pratiche_id_fk | `CREATE INDEX ix_note_pratiche_note_pratiche_id_fk ON storico.note_pratiche USING btree (note_pratiche_id)` |
| pk_storico_note_pratiche | `CREATE UNIQUE INDEX pk_storico_note_pratiche ON storico.note_pratiche USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_pratiche_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_note_pratiche_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

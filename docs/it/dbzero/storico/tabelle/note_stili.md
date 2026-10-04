{% include-markdown "it/dbzero/storico/manual/note_stili.md" %}
# 📚 Tabella `note_stili`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.note_stili_id_seq'::regclass) |
| note_stili_id | bigint | NO |  |
| change_type | character(1) | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |
| origine_schema | text | NO |  |
| scope_emittente_fiscale_id | bigint | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_note_stili | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_note_stili_note_stili_id_fk | `CREATE INDEX ix_note_stili_note_stili_id_fk ON storico.note_stili USING btree (note_stili_id)` |
| ix_note_stili_scope_ef | `CREATE INDEX ix_note_stili_scope_ef ON storico.note_stili USING btree (scope_emittente_fiscale_id)` |
| pk_storico_note_stili | `CREATE UNIQUE INDEX pk_storico_note_stili ON storico.note_stili USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_note_stili_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_note_stili_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

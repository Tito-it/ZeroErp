{% include-markdown "it/dbzero/storico/manual/resi_righe_riconsegne.md" %}
# 📚 Tabella `resi_righe_riconsegne`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.resi_righe_riconsegne_id_seq'::regclass) |
| resi_righe_riconsegne_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_resi_righe_riconsegne | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resi_righe_riconsegne_resi_righe_riconsegne_id_fk | `CREATE INDEX ix_resi_righe_riconsegne_resi_righe_riconsegne_id_fk ON storico.resi_righe_riconsegne USING btree (resi_righe_riconsegne_id)` |
| pk_storico_resi_righe_riconsegne | `CREATE UNIQUE INDEX pk_storico_resi_righe_riconsegne ON storico.resi_righe_riconsegne USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_righe_riconsegne_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_riconsegne_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

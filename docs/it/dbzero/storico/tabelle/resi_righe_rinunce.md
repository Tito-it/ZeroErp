# 📚 Tabella `resi_righe_rinunce`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.resi_righe_rinunce_id_seq'::regclass) |
| resi_righe_rinunce_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_resi_righe_rinunce | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resi_righe_rinunce_resi_righe_rinunce_id_fk | `CREATE INDEX ix_resi_righe_rinunce_resi_righe_rinunce_id_fk ON storico.resi_righe_rinunce USING btree (resi_righe_rinunce_id)` |
| pk_storico_resi_righe_rinunce | `CREATE UNIQUE INDEX pk_storico_resi_righe_rinunce ON storico.resi_righe_rinunce USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_righe_rinunce_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_rinunce_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

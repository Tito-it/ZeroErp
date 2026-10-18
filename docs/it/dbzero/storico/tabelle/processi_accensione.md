# 📚 Tabella `processi_accensione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.processi_accensione_id_seq'::regclass) |
| processi_accensione_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_processi_accensione | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_processi_accensione_processi_accensione_id_fk | `CREATE INDEX ix_processi_accensione_processi_accensione_id_fk ON storico.processi_accensione USING btree (processi_accensione_id)` |
| ix_processi_accensione_scope_ef | `CREATE INDEX ix_processi_accensione_scope_ef ON storico.processi_accensione USING btree (scope_emittente_fiscale_id)` |
| pk_storico_processi_accensione | `CREATE UNIQUE INDEX pk_storico_processi_accensione ON storico.processi_accensione USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_processi_accensione_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_processi_accensione_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

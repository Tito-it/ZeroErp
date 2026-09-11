{% include-markdown "it/dbzero/storico/manual/bank_branches.md" %}
# 📚 Tabella `bank_branches`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.bank_branches_id_seq'::regclass) |
| bank_branches_id | bigint | NO |  |
| change_type | character | YES | 'A'::bpchar |
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
| PRIMARY KEY | pk_storico_bank_branches | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_bank_branches_bank_branches_id_fk | `CREATE INDEX ix_bank_branches_bank_branches_id_fk ON storico.bank_branches USING btree (bank_branches_id)` |
| ix_bank_branches_scope_ef | `CREATE INDEX ix_bank_branches_scope_ef ON storico.bank_branches USING btree (scope_emittente_fiscale_id)` |
| pk_storico_bank_branches | `CREATE UNIQUE INDEX pk_storico_bank_branches ON storico.bank_branches USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_bank_branches_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_bank_branches_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

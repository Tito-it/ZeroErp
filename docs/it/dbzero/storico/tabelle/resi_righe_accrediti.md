{% include-markdown "it/dbzero/storico/manual/resi_righe_accrediti.md" %}
# 📚 Tabella `resi_righe_accrediti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.resi_righe_accrediti_id_seq'::regclass) |
| resi_righe_accrediti_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_resi_righe_accrediti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_resi_righe_accrediti_resi_righe_accrediti_id_fk | `CREATE INDEX ix_resi_righe_accrediti_resi_righe_accrediti_id_fk ON storico.resi_righe_accrediti USING btree (resi_righe_accrediti_id)` |
| ix_resi_righe_accrediti_scope_ef | `CREATE INDEX ix_resi_righe_accrediti_scope_ef ON storico.resi_righe_accrediti USING btree (scope_emittente_fiscale_id)` |
| pk_storico_resi_righe_accrediti | `CREATE UNIQUE INDEX pk_storico_resi_righe_accrediti ON storico.resi_righe_accrediti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resi_righe_accrediti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_resi_righe_accrediti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

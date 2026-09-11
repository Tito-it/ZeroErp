{% include-markdown "it/dbzero/storico/manual/emittenti_fiscali.md" %}
# 📚 Tabella `emittenti_fiscali`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.emittenti_fiscali_id_seq'::regclass) |
| emittenti_fiscali_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_emittenti_fiscali | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_emittenti_fiscali_emittenti_fiscali_id_fk | `CREATE INDEX ix_emittenti_fiscali_emittenti_fiscali_id_fk ON storico.emittenti_fiscali USING btree (emittenti_fiscali_id)` |
| ix_emittenti_fiscali_scope_ef | `CREATE INDEX ix_emittenti_fiscali_scope_ef ON storico.emittenti_fiscali USING btree (scope_emittente_fiscale_id)` |
| pk_storico_emittenti_fiscali | `CREATE UNIQUE INDEX pk_storico_emittenti_fiscali ON storico.emittenti_fiscali USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_emittenti_fiscali_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_emittenti_fiscali_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/storico/manual/regole_generazione.md" %}
# 📚 Tabella `regole_generazione`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.regole_generazione_id_seq'::regclass) |
| regole_generazione_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_regole_generazione | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_regole_generazione_regole_generazione_id_fk | `CREATE INDEX ix_regole_generazione_regole_generazione_id_fk ON storico.regole_generazione USING btree (regole_generazione_id)` |
| ix_regole_generazione_scope_ef | `CREATE INDEX ix_regole_generazione_scope_ef ON storico.regole_generazione USING btree (scope_emittente_fiscale_id)` |
| pk_storico_regole_generazione | `CREATE UNIQUE INDEX pk_storico_regole_generazione ON storico.regole_generazione USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_regole_generazione_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_regole_generazione_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

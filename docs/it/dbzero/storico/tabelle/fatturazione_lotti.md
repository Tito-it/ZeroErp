{% include-markdown "it/dbzero/storico/manual/fatturazione_lotti.md" %}
# 📚 Tabella `fatturazione_lotti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.fatturazione_lotti_id_seq'::regclass) |
| fatturazione_lotti_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_fatturazione_lotti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatturazione_lotti_fatturazione_lotti_id_fk | `CREATE INDEX ix_fatturazione_lotti_fatturazione_lotti_id_fk ON storico.fatturazione_lotti USING btree (fatturazione_lotti_id)` |
| ix_fatturazione_lotti_scope_ef | `CREATE INDEX ix_fatturazione_lotti_scope_ef ON storico.fatturazione_lotti USING btree (scope_emittente_fiscale_id)` |
| pk_storico_fatturazione_lotti | `CREATE UNIQUE INDEX pk_storico_fatturazione_lotti ON storico.fatturazione_lotti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_lotti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fatturazione_lotti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

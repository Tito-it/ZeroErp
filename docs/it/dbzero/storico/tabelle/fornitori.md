{% include-markdown "it/dbzero/storico/manual/fornitori.md" %}
# 📚 Tabella `fornitori`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.fornitori_id_seq'::regclass) |
| fornitori_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_fornitori | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fornitori_fornitori_id_fk | `CREATE INDEX ix_fornitori_fornitori_id_fk ON storico.fornitori USING btree (fornitori_id)` |
| ix_fornitori_scope_ef | `CREATE INDEX ix_fornitori_scope_ef ON storico.fornitori USING btree (scope_emittente_fiscale_id)` |
| pk_storico_fornitori | `CREATE UNIQUE INDEX pk_storico_fornitori ON storico.fornitori USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fornitori_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_fornitori_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

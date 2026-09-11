{% include-markdown "it/dbzero/storico/manual/ordini.md" %}
# 📚 Tabella `ordini`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.ordini_id_seq'::regclass) |
| ordini_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_ordini | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ordini_ordini_id_fk | `CREATE INDEX ix_ordini_ordini_id_fk ON storico.ordini USING btree (ordini_id)` |
| ix_ordini_scope_ef | `CREATE INDEX ix_ordini_scope_ef ON storico.ordini USING btree (scope_emittente_fiscale_id)` |
| pk_storico_ordini | `CREATE UNIQUE INDEX pk_storico_ordini ON storico.ordini USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ordini_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ordini_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

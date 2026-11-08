# 📚 Tabella `ricevute`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.ricevute_id_seq'::regclass) |
| ricevute_id | uuid | NO |  |
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
| PRIMARY KEY | pk_storico_ricevute | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ricevute_ricevute_id_fk | `CREATE INDEX ix_ricevute_ricevute_id_fk ON storico.ricevute USING btree (ricevute_id)` |
| ix_ricevute_scope_ef | `CREATE INDEX ix_ricevute_scope_ef ON storico.ricevute USING btree (scope_emittente_fiscale_id)` |
| pk_storico_ricevute | `CREATE UNIQUE INDEX pk_storico_ricevute ON storico.ricevute USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ricevute_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ricevute_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

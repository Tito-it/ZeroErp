{% include-markdown "it/dbzero/storico/manual/articoli.md" %}
# 📚 Tabella `articoli`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.articoli_id_seq'::regclass) |
| articoli_id | uuid | NO |  |
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
| PRIMARY KEY | pk_storico_articoli | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_articoli_articoli_id_fk | `CREATE INDEX ix_articoli_articoli_id_fk ON storico.articoli USING btree (articoli_id)` |
| ix_articoli_scope_ef | `CREATE INDEX ix_articoli_scope_ef ON storico.articoli USING btree (scope_emittente_fiscale_id)` |
| pk_storico_articoli | `CREATE UNIQUE INDEX pk_storico_articoli ON storico.articoli USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_articoli_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_articoli_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

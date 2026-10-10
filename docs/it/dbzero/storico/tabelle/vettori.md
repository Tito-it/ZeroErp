{% include-markdown "it/dbzero/storico/manual/vettori.md" %}
# 📚 Tabella `vettori`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.vettori_id_seq'::regclass) |
| vettori_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_vettori | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_vettori_scope_ef | `CREATE INDEX ix_vettori_scope_ef ON storico.vettori USING btree (scope_emittente_fiscale_id)` |
| ix_vettori_vettori_id_fk | `CREATE INDEX ix_vettori_vettori_id_fk ON storico.vettori USING btree (vettori_id)` |
| pk_storico_vettori | `CREATE UNIQUE INDEX pk_storico_vettori ON storico.vettori USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_vettori_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_vettori_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

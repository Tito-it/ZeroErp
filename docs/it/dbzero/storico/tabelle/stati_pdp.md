{% include-markdown "it/dbzero/storico/manual/stati_pdp.md" %}
# 📚 Tabella `stati_pdp`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.stati_pdp_id_seq'::regclass) |
| stati_pdp_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_stati_pdp | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_stati_pdp_scope_ef | `CREATE INDEX ix_stati_pdp_scope_ef ON storico.stati_pdp USING btree (scope_emittente_fiscale_id)` |
| ix_stati_pdp_stati_pdp_id_fk | `CREATE INDEX ix_stati_pdp_stati_pdp_id_fk ON storico.stati_pdp USING btree (stati_pdp_id)` |
| pk_storico_stati_pdp | `CREATE UNIQUE INDEX pk_storico_stati_pdp ON storico.stati_pdp USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_stati_pdp_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_stati_pdp_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

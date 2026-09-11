{% include-markdown "it/dbzero/storico/manual/ambito_causale.md" %}
# 📚 Tabella `ambito_causale`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.ambito_causale_id_seq'::regclass) |
| ambito_causale_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_ambito_causale | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_ambito_causale_ambito_causale_id_fk | `CREATE INDEX ix_ambito_causale_ambito_causale_id_fk ON storico.ambito_causale USING btree (ambito_causale_id)` |
| ix_ambito_causale_scope_ef | `CREATE INDEX ix_ambito_causale_scope_ef ON storico.ambito_causale USING btree (scope_emittente_fiscale_id)` |
| pk_storico_ambito_causale | `CREATE UNIQUE INDEX pk_storico_ambito_causale ON storico.ambito_causale USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_ambito_causale_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_ambito_causale_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

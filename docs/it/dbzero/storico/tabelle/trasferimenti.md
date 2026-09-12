{% include-markdown "it/dbzero/storico/manual/trasferimenti.md" %}
# 📚 Tabella `trasferimenti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.trasferimenti_id_seq'::regclass) |
| trasferimenti_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_trasferimenti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_trasferimenti_scope_ef | `CREATE INDEX ix_trasferimenti_scope_ef ON storico.trasferimenti USING btree (scope_emittente_fiscale_id)` |
| ix_trasferimenti_trasferimenti_id_fk | `CREATE INDEX ix_trasferimenti_trasferimenti_id_fk ON storico.trasferimenti USING btree (trasferimenti_id)` |
| pk_storico_trasferimenti | `CREATE UNIQUE INDEX pk_storico_trasferimenti ON storico.trasferimenti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_trasferimenti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_trasferimenti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/storico/manual/user_override_oggetti.md" %}
# 📚 Tabella `user_override_oggetti`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.user_override_oggetti_id_seq'::regclass) |
| user_override_oggetti_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_user_override_oggetti | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_user_override_oggetti_scope_ef | `CREATE INDEX ix_user_override_oggetti_scope_ef ON storico.user_override_oggetti USING btree (scope_emittente_fiscale_id)` |
| ix_user_override_oggetti_user_override_oggetti_id_fk | `CREATE INDEX ix_user_override_oggetti_user_override_oggetti_id_fk ON storico.user_override_oggetti USING btree (user_override_oggetti_id)` |
| pk_storico_user_override_oggetti | `CREATE UNIQUE INDEX pk_storico_user_override_oggetti ON storico.user_override_oggetti USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_user_override_oggetti_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_user_override_oggetti_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

# 📚 Tabella `profili_accesso_bindings`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.profili_accesso_bindings_id_seq'::regclass) |
| profili_accesso_bindings_id | bigint | NO |  |
| change_type | character | YES | 'A'::bpchar |
| tipo_operazione | smallint | YES |  |
| snapshot | jsonb | YES |  |
| user_insert | text | YES | CURRENT_USER |
| data_insert | timestamp with time zone | YES | now() |
| tx_id | uuid | YES |  |
| valid_from | timestamp with time zone | YES | now() |
| valid_to | timestamp with time zone | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | pk_storico_profili_accesso_bindings | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_profili_accesso_bindings_profili_accesso_bindings_id_fk | `CREATE INDEX ix_profili_accesso_bindings_profili_accesso_bindings_id_fk ON storico.profili_accesso_bindings USING btree (profili_accesso_bindings_id)` |
| pk_storico_profili_accesso_bindings | `CREATE UNIQUE INDEX pk_storico_profili_accesso_bindings ON storico.profili_accesso_bindings USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_profili_accesso_bindings_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_profili_accesso_bindings_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

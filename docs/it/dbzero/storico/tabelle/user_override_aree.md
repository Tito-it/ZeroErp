# 📚 Tabella `user_override_aree`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.user_override_aree_id_seq'::regclass) |
| user_override_aree_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_user_override_aree | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_user_override_aree_user_override_aree_id_fk | `CREATE INDEX ix_user_override_aree_user_override_aree_id_fk ON storico.user_override_aree USING btree (user_override_aree_id)` |
| pk_storico_user_override_aree | `CREATE UNIQUE INDEX pk_storico_user_override_aree ON storico.user_override_aree USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_user_override_aree_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_user_override_aree_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

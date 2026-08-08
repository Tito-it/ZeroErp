# 📚 Tabella `identita_scope_bindings`

> 📝 **Descrizione**
>
> Storico di config.identita_scope_bindings.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO | nextval('storico.identita_scope_bindings_id_seq'::regclass) |
| identita_scope_bindings_id | bigint | NO |  |
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
| PRIMARY KEY | pk_storico_identita_scope_bindings | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_identita_scope_bindings_identita_scope_bindings_id_fk | `CREATE INDEX ix_identita_scope_bindings_identita_scope_bindings_id_fk ON storico.identita_scope_bindings USING btree (identita_scope_bindings_id)` |
| pk_storico_identita_scope_bindings | `CREATE UNIQUE INDEX pk_storico_identita_scope_bindings ON storico.identita_scope_bindings USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_identita_scope_bindings_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_identita_scope_bindings_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

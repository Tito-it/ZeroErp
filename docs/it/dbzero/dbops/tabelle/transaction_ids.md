{% include-markdown "it/dbzero/dbops/manual/transaction_ids.md" %}
# 📚 Tabella `transaction_ids`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | uuid | NO | uuidv7() |
| user_insert | text | NO | CURRENT_USER |
| data_insert | timestamp with time zone | NO | now() |
| user_update | text | YES |  |
| data_update | timestamp with time zone | YES |  |
| generating_function | text | YES |  |
| session_info | jsonb | NO | '{}'::jsonb |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| PRIMARY KEY | transaction_ids_pkey | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| transaction_ids_pkey | `CREATE UNIQUE INDEX transaction_ids_pkey ON dbops.transaction_ids USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_transaction_ids_upd_audit_data_user_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_transaction_ids_upd_dlt_prevent_modification_generic | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_prevent_modification_generic()` |
| trg_transaction_ids_upd_dlt_prevent_modification_generic | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_prevent_modification_generic()` |

---
{% include-markdown "signature-core.md" %}

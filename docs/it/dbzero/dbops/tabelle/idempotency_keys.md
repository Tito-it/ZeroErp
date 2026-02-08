{% include-markdown "it/dbzero/dbops/manual/idempotency_keys.md" %}
# 📚 Tabella `idempotency_keys`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| idempotency_key | text | NO |  |
| request_id | uuid | YES |  |
| tx_id | uuid | YES |  |
| status | text | NO |  |
| response_payload | jsonb | YES |  |
| cleanup_at | timestamp with time zone | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_idempotency_keys_status |  |
| CHECK | chk_idempotency_keys_txid_completed |  |
| PRIMARY KEY | pk_idempotency_keys | idempotency_key |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_idempotency_keys_cleanup_at | `CREATE INDEX ix_idempotency_keys_cleanup_at ON dbops.idempotency_keys USING btree (cleanup_at)` |
| pk_idempotency_keys | `CREATE UNIQUE INDEX pk_idempotency_keys ON dbops.idempotency_keys USING btree (idempotency_key)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_idempotency_keys_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_idempotency_keys_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_idempotency_keys_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/vendite/manual/fatturazione_lotti_log.md" %}
# 📚 Tabella `fatturazione_lotti_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_id | bigint | NO |  |
| data_ora | timestamp with time zone | NO | now() |
| messaggio | text | NO |  |
| status | character | NO | 'W'::bpchar |
| disabilitato | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatturazione_lotti_log_status |  |
| FOREIGN KEY | fk_fatturazione_lotti_log_lotto | lotto_id |
| PRIMARY KEY | pk_fatturazione_lotti_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_fatturazione_lotti_log | `CREATE UNIQUE INDEX pk_fatturazione_lotti_log ON vendite.fatturazione_lotti_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatturazione_lotti_log_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

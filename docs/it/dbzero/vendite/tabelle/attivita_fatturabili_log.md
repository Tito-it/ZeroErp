{% include-markdown "it/dbzero/vendite/manual/attivita_fatturabili_log.md" %}
# 📚 Tabella `attivita_fatturabili_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| lotto_attivita_id | bigint | YES |  |
| attivita_consumi_id | bigint | YES |  |
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
| CHECK | chk_attivita_fatturabili_log_status |  |
| FOREIGN KEY | fk_attivita_fatturabili_log_attivita_consumi | attivita_consumi_id |
| FOREIGN KEY | fk_attivita_fatturabili_log_attivita_lotto | lotto_attivita_id |
| PRIMARY KEY | pk_attivita_fatturabili_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_attivita_fatturabili_log | `CREATE UNIQUE INDEX pk_attivita_fatturabili_log ON vendite.attivita_fatturabili_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_attivita_fatturabili_log_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

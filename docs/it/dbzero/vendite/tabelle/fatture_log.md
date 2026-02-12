{% include-markdown "it/dbzero/vendite/manual/fatture_log.md" %}
# 📚 Tabella `fatture_log`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| fattura_id | bigint | NO |  |
| data_ora | timestamp with time zone | NO | now() |
| messaggio | text | NO |  |
| status | character | NO | 'W'::bpchar |
| disabilitato | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_fatture_log_status |  |
| FOREIGN KEY | fk_fatture_log_fattura | fattura_id |
| PRIMARY KEY | pk_fatture_log | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| ix_fatture_log_fattura_id | `CREATE INDEX ix_fatture_log_fattura_id ON vendite.fatture_log USING btree (fattura_id)` |
| pk_fatture_log | `CREATE UNIQUE INDEX pk_fatture_log ON vendite.fatture_log USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_fatture_log_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

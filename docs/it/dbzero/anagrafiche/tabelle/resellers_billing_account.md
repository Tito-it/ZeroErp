{% include-markdown "it/dbzero/anagrafiche/manual/resellers_billing_account.md" %}
# 📚 Tabella `resellers_billing_account`

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| billing_account_id | bigint | NO |  |
| reseller_soggetto_ruolo_id | bigint | NO |  |
| valido_dal | date | NO | CURRENT_DATE |
| valido_al | date | YES |  |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| validita | daterange | NO |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_resellers_ba_validita |  |
| FOREIGN KEY | fk_resellers_billing_account_ba | billing_account_id |
| FOREIGN KEY | fk_resellers_billing_account_reseller | reseller_soggetto_ruolo_id |
| PRIMARY KEY | pk_resellers_billing_account | id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_resellers_billing_account | `CREATE UNIQUE INDEX pk_resellers_billing_account ON anagrafiche.resellers_billing_account USING btree (id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_resellers_billing_account_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_resellers_billing_account_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account.md" %}
# 📚 Tabella `emittenti_fiscali_billing_account`

> 📝 **Descrizione**
>
> Associazione billing_account -&gt; emittente fiscale (ruolo). Prevede un default globale.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| billing_account_id | bigint | YES |  |
| emittente_soggetto_ruolo_id | bigint | NO |  |
| is_default | boolean | NO | false |
| meta | jsonb | NO | '{}'::jsonb |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_emittenti_fiscali_ba_default |  |
| FOREIGN KEY | fk_emittenti_fiscali_billing_account_ba | billing_account_id |
| FOREIGN KEY | fk_emittenti_fiscali_billing_account_emittente | emittente_soggetto_ruolo_id |
| PRIMARY KEY | pk_emittenti_fiscali_billing_account | id |
| UNIQUE | uq_emittenti_fiscali_ba | billing_account_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_emittenti_fiscali_billing_account | `CREATE UNIQUE INDEX pk_emittenti_fiscali_billing_account ON anagrafiche.emittenti_fiscali_billing_account USING btree (id)` |
| uq_emittenti_fiscali_ba | `CREATE UNIQUE INDEX uq_emittenti_fiscali_ba ON anagrafiche.emittenti_fiscali_billing_account USING btree (billing_account_id)` |
| uq_emittenti_fiscali_ba_default | `CREATE UNIQUE INDEX uq_emittenti_fiscali_ba_default ON anagrafiche.emittenti_fiscali_billing_account USING btree (is_default) WHERE (is_default = true)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_emittenti_fiscali_ba_a10_default_guard_ins_upd_dlt | AFTER | INSERT | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_guard()` |
| trg_emittenti_fiscali_ba_a10_default_guard_ins_upd_dlt | AFTER | DELETE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_guard()` |
| trg_emittenti_fiscali_ba_a10_default_guard_ins_upd_dlt | AFTER | UPDATE | `EXECUTE FUNCTION anagrafiche.trgfn_emittenti_fiscali_default_guard()` |
| trg_emittenti_fiscali_billing_account_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_emittenti_fiscali_billing_account_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |

---
{% include-markdown "signature-core.md" %}

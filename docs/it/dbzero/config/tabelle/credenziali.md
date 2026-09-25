{% include-markdown "it/dbzero/config/manual/credenziali.md" %}
# 📚 Tabella `credenziali`

> 📝 **Descrizione**
>
> Stato della CREDENZIALE (1:1 con django.auth_user): la password e' una e vale per tutte le porte, e qui sta cio' che le appartiene. La riga nasce alla prima scrittura; la sua ASSENZA vale «nessun tentativo, non bloccata, nessun obbligo di cambio password». Nessuno la legge o scrive fuori dal DB: lo fanno le funzioni di script (fn_check_blocco_login, fn_registra_tentativo_login, fn_azzera_tentativi_credenziale, fn_blocca_credenziale, fn_sblocca_credenziale, fn_get/fn_imposta_deve_cambiare_password). All'app solo SELECT. Niente storico (cambierebbe a ogni password sbagliata), niente RLS (nessuno scope, letta prima del login). Brief: brief-db-blocco-login-per-credenziale.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| deve_cambiare_password | boolean | NO | false |
| fallimenti_consecutivi | integer | NO | 0 |
| ultimo_fallimento_at | timestamp with time zone | YES |  |
| bloccata_at | timestamp with time zone | YES |  |
| bloccata_da | integer | YES |  |
| motivo_blocco | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_credenziali_blocco |  |
| CHECK | chk_credenziali_fallimenti |  |
| FOREIGN KEY | fk_config_credenziali_auth_user | auth_user_id |
| FOREIGN KEY | fk_config_credenziali_bloccata_da_auth_user | bloccata_da |
| PRIMARY KEY | pk_credenziali | id |
| UNIQUE | uq_credenziali_auth_user | auth_user_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_credenziali | `CREATE UNIQUE INDEX pk_credenziali ON config.credenziali USING btree (id)` |
| uq_credenziali_auth_user | `CREATE UNIQUE INDEX uq_credenziali_auth_user ON config.credenziali USING btree (auth_user_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_credenziali_a10_guard_ultimo_super_admin_ins_upd | AFTER | INSERT | `EXECUTE FUNCTION config.trgfn_credenziali_guard_ultimo_super_admin()` |
| trg_credenziali_a10_guard_ultimo_super_admin_ins_upd | AFTER | UPDATE | `EXECUTE FUNCTION config.trgfn_credenziali_guard_ultimo_super_admin()` |

---
{% include-markdown "signature-core.md" %}

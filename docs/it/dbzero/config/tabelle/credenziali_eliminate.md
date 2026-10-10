{% include-markdown "it/dbzero/config/manual/credenziali_eliminate.md" %}
# 📚 Tabella `credenziali_eliminate`

> 📝 **Descrizione**
>
> La traccia delle credenziali eliminate dall'amministratore (script.fn_elimina_credenziale): la riga di django.auth_user sparisce, chi l'ha eliminata e cosa era restano qui. Append-only: la scrive solo il verbo, SECURITY DEFINER del proprietario; all'app il solo SELECT (linee-guida-sql §11.8: loop ci_apply 20260205-41, provision_db_roles.sql, forward 90_end/20261006-15). ⛔ Nessuna FK: auth_user_id nomina una riga che non esiste piu', e eliminata_da e' un SUPER_ADMIN (che ha una veste e non si elimina); una FK verso django.auth_user lo renderebbe storia per script.fn_check_credenziale_eliminabile, e su un'installazione nuova le FK del ponte django non nascono. Nessun cleanup_at: la traccia non scade. Brief: brief-db-elimina-credenziale-senza-veste §4.2 (sede decisa da Tid il 2026-10-06).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| auth_user_id | integer | NO |  |
| username | text | NO |  |
| email | text | NO |  |
| eliminata_at | timestamp with time zone | NO | now() |
| eliminata_da | integer | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_credenziali_eliminate_auth_user_positivo |  |
| CHECK | chk_credenziali_eliminate_eliminata_da_positivo |  |
| PRIMARY KEY | pk_credenziali_eliminate | id |
| UNIQUE | uq_credenziali_eliminate_auth_user | auth_user_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_credenziali_eliminate | `CREATE UNIQUE INDEX pk_credenziali_eliminate ON config.credenziali_eliminate USING btree (id)` |
| uq_credenziali_eliminate_auth_user | `CREATE UNIQUE INDEX uq_credenziali_eliminate_auth_user ON config.credenziali_eliminate USING btree (auth_user_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_credenziali_eliminate_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_credenziali_eliminate_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_credenziali_eliminate_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_credenziali_eliminate_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

{% include-markdown "it/dbzero/dbops/manual/processi_identita.md" %}
# 📚 Tabella `processi_identita`

> 📝 **Descrizione**
>
> Legame processo -&gt; utente tecnico (django.auth_user.id). Un processo ha un utente per emittente, non uno in tutto: config.user_emittenti_fiscali e' uno-a-uno sull'utente (uq_user_emittenti_fiscali_auth_user), e solo il super admin e' multi-emittente. Il vincolo qui e' quindi UNIQUE(auth_user_id) (uq_processi_identita_auth_user): un utente tecnico serve un processo solo, un processo puo' averne piu' d'uno. L'emittente non si ripete in questa tabella: sta in config.user_emittenti_fiscali, e duplicarlo sarebbe una seconda sorgente di verita'. Meta' di macchina del registro: il suo seed va marcato context: dati_macchina.

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| processo_id | integer | NO |  |
| auth_user_id | integer | NO |  |
| attivo | boolean | NO | true |
| note | text | YES |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| FOREIGN KEY | fk_processi_identita_processi | processo_id |
| PRIMARY KEY | pk_processi_identita | id |
| UNIQUE | uq_processi_identita_auth_user | auth_user_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_processi_identita | `CREATE UNIQUE INDEX pk_processi_identita ON dbops.processi_identita USING btree (id)` |
| uq_processi_identita_auth_user | `CREATE UNIQUE INDEX uq_processi_identita_auth_user ON dbops.processi_identita USING btree (auth_user_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_processi_identita_audit_data_user_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_processi_identita_audit_data_user_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_processi_identita_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_processi_identita_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

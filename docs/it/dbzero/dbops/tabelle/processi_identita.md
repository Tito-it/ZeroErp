# 📚 Tabella `processi_identita`

> 📝 **Descrizione**
>
> Legame processo -&gt; utente tecnico (django.auth_user.id), UNO per processo (decisione D-6). Meta' di MACCHINA del registro: valorizza una FK verso django, quindi il suo seed va marcato context: dati_macchina e su un database ricostruito da zero la tabella resta vuota. Serve ai soli processi di classe DOMINIO: per gli altri l'attore e' il codice del processo (D-8). Brief: brief-db-processi-automatici-identita-e-perimetro §2.4.

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
| UNIQUE | uq_processi_identita_processo | processo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_processi_identita | `CREATE UNIQUE INDEX pk_processi_identita ON dbops.processi_identita USING btree (id)` |
| uq_processi_identita_processo | `CREATE UNIQUE INDEX uq_processi_identita_processo ON dbops.processi_identita USING btree (processo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_processi_identita_audit_data_user_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_processi_identita_audit_data_user_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_processi_identita_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_processi_identita_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |

---
{% include-markdown "signature-core.md" %}

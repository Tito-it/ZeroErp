{% include-markdown "it/dbzero/dbops/manual/processi_accensione.md" %}
# 📚 Tabella `processi_accensione`

> 📝 **Descrizione**
>
> La scelta a mano di questa installazione sulla sveglia di un processo: acceso, spento o tornato al default, col motivo. Scavalca il default per ambiente di dbops.processi (acceso_in_sviluppo, acceso_in_produzione). La riga dice l'ULTIMO gesto (chi, quando, perche'): acceso NULL = segue il default; assenza della riga = nessuno l'ha mai toccata. La storia dei gesti e' in storico.processi_accensione (storicizza, automazioni di ci_apply); chi e' l'utente lo scrive l'audit generato (app.jwt_user). Dato di MACCHINA (come dbops.processi_identita): nessun seed, la scrive l'operatore col verbo dbops.fn_imposta_accensione_processo. Un non spegnibile non si spegne e un processo senza sveglia (CODA, ritirato) non ha righe: dbops.trgfn_processi_accensione_guard. Lo stato effettivo lo dice dbops.fn_processo_acceso_dichiarato (e maintenance.fn_sveglia_accesa per le sveglie). Brief: brief-db-processi-accensione-per-ambiente (A-2, S-1).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| processo_id | integer | NO |  |
| acceso | boolean | YES |  |
| motivo | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |
| storicizza | boolean | NO | true |
| tx_id | uuid | YES |  |

## 🔒 Vincoli
| Tipo | Nome | Colonne |
|------|------|---------|
| CHECK | chk_processi_accensione_motivo |  |
| FOREIGN KEY | fk_processi_accensione_processi | processo_id |
| PRIMARY KEY | pk_processi_accensione | id |
| UNIQUE | uq_processi_accensione_processo | processo_id |

## 📑 Indici
| Nome | Definizione |
|------|-------------|
| pk_processi_accensione | `CREATE UNIQUE INDEX pk_processi_accensione ON dbops.processi_accensione USING btree (id)` |
| uq_processi_accensione_processo | `CREATE UNIQUE INDEX uq_processi_accensione_processo ON dbops.processi_accensione USING btree (processo_id)` |

## 🚨 Trigger
| Nome | Timing | Evento | Azione |
|------|--------|--------|--------|
| trg_processi_accensione_a10_guard_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_processi_accensione_guard()` |
| trg_processi_accensione_a10_guard_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_processi_accensione_guard()` |
| trg_processi_accensione_audit_data_user_upd | BEFORE | INSERT | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_processi_accensione_audit_data_user_upd | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_audit_data_user_generic()` |
| trg_processi_accensione_gen_tx_id_ins_upd | BEFORE | UPDATE | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_processi_accensione_gen_tx_id_ins_upd | BEFORE | INSERT | `EXECUTE FUNCTION dbops.trgfn_tx_id_managed()` |
| trg_processi_accensione_z90_storico_upd_dlt | BEFORE | DELETE | `EXECUTE FUNCTION script.trgfn_storico_generic('processi_accensione_id')` |
| trg_processi_accensione_z90_storico_upd_dlt | BEFORE | UPDATE | `EXECUTE FUNCTION script.trgfn_storico_generic('processi_accensione_id')` |

---
{% include-markdown "signature-core.md" %}

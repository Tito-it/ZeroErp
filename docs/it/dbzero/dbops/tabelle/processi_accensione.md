{% include-markdown "it/dbzero/dbops/manual/processi_accensione.md" %}
# 📚 Tabella `processi_accensione`

> 📝 **Descrizione**
>
> La scelta a mano di questa installazione sulla sveglia di un processo: acceso o spento, col motivo. Scavalca il default per ambiente di dbops.processi (acceso_in_sviluppo, acceso_in_produzione); assenza della riga = vale il default. Dato di MACCHINA (come dbops.processi_identita): nessun seed, la scrive l'operatore col verbo dbops.fn_imposta_accensione_processo. Un non spegnibile non si spegne e un processo senza sveglia (CODA, ritirato) non ha righe: dbops.trgfn_processi_accensione_guard. Lo stato effettivo lo dice dbops.fn_processo_acceso_dichiarato (e maintenance.fn_sveglia_accesa per le sveglie). Brief: brief-db-processi-accensione-per-ambiente (A-2).

## 🗂️ Campi principali
| Colonna | Tipo | Nullable | Default |
|---------|------|----------|---------|
| id | bigint | NO |  |
| processo_id | integer | NO |  |
| acceso | boolean | NO |  |
| motivo | text | NO |  |
| data_insert | timestamp with time zone | NO | now() |
| user_insert | text | NO | CURRENT_USER |
| data_update | timestamp with time zone | NO | now() |
| user_update | text | NO | CURRENT_USER |

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

---
{% include-markdown "signature-core.md" %}

# ⏰ Job pgAgent

> 📝 **Descrizione**
>
> I lavori a orario che pgAgent esegue in questo database: se sono accesi, quando partono (ora del server del database), che cosa chiama ogni step e quale processo di `dbops.processi` registrano. Pagina generata dalle tabelle di `pgagent`; l'ultima e la prossima corsa non ci sono apposta (cambiano a ogni giro): lo stato vivo e' in `dbops.vw_processi_programmazione`.

| Job | Acceso | Quando | Processo |
| --- | --- | --- | --- |
| `analyze_statistiche` | si | alle 02:30, ogni giorno | `analyze_statistiche` |
| `apply_storicizza_weekly` | si | alle 07:00, di sabato | `apply_storicizza_weekly` |
| `automations_apply_fk_indexes_policy` | si | alle 23:00, di domenica | `apply_fk_index_policy` |
| `automations_attivo` | si | alle 21:00, ogni giorno | `automations_attivo` |
| `automations_audit_update` | si | alle 21:00, ogni giorno | `automations_audit_update` |
| `automations_cleanup_weekly` | si | alle 23:00, di domenica | `automations_cleanup` |
| `automations_delete_block` | si | alle 21:10, ogni giorno | `automations_delete_block` |
| `automations_lock_columns` | si | alle 21:10, ogni giorno | `automations_lock_columns` |
| `automations_overlap` | si | alle 21:00, ogni giorno | `automations_overlap` |
| `automations_storico` | si | alle 21:00, ogni giorno | `automations_storico` |
| `automations_storico_provision` | si | alle 21:00, ogni giorno | `automations_storico_provision` |
| `automations_tx_id` | si | alle 21:00, ogni giorno | `automations_tx_id` |
| `chiusura_scadenze_daily` | si | ogni ora, al minuto 05 | `chiusura_scadenze_daily` |
| `guardiano_digest` | si | ogni ora, al minuto 20 | `guardiano_digest` |
| `sync_auth_user_expired_daily` | si | ogni ora, al minuto 10 | `sync_auth_user_expired_daily` |
| `sync_storico_set_storicizza` | si | alle 07:05, di sabato | `sync_storico_set_storicizza` |

## `analyze_statistiche`

Statistiche del planner: ogni notte ANALYZE del database e autoverifica (maintenance.fn_analyze_statistiche). Una tabella rimasta senza statistiche fa fallire il job, nominata nel giornale.

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `analyze` | si | SQL | zeroerp | [`CALL maintenance.proc_analyze_statistiche_job();`](funzioni/proc_analyze_statistiche_job.md) |

## `apply_storicizza_weekly`

Setta DEFAULT=true su colonne "storicizza" ogni sabato ore 07:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_apply_storicizza` | si | SQL | zeroerp | [`call maintenance.proc_apply_storicizza_defaults_job();`](funzioni/proc_apply_storicizza_defaults_job.md) |

## `automations_apply_fk_indexes_policy`

Applica policy indici FK ogni domenica ore 23:00 (populate=true)

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_apply_fk_index_policy` | si | SQL | zeroerp | [`CALL maintenance.proc_apply_fk_index_policy_job(true);`](funzioni/proc_apply_fk_index_policy_job.md) |

## `automations_attivo`

Esegue dbops.fn_run_automations_attivo (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_attivo` | si | SQL | zeroerp | [`CALL maintenance.proc_automations_attivo_job();`](funzioni/proc_automations_attivo_job.md) |

## `automations_audit_update`

Esegue dbops.fn_run_automations_audit_update (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_audit_update` | si | SQL | zeroerp | [`CALL maintenance.proc_automations_audit_update_job();`](funzioni/proc_automations_audit_update_job.md) |

## `automations_cleanup_weekly`

Esegue cleanup automazioni (dbops) ogni domenica ore 23:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_cleanup` | si | SQL | zeroerp | [`CALL maintenance.proc_automations_cleanup_job();`](funzioni/proc_automations_cleanup_job.md) |

## `automations_delete_block`

Applica il blocco di cancellazione alle tabelle dichiarate in dbops.automation_delete_block

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_delete_block` | si | SQL | zeroerp | [`CALL maintenance.proc_automations_delete_block_job();`](funzioni/proc_automations_delete_block_job.md) |

## `automations_lock_columns`

Applica il lucchetto alle colonne dichiarate in dbops.automation_lock_columns

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_lock_columns` | si | SQL | zeroerp | [`CALL maintenance.proc_automations_lock_columns_job();`](funzioni/proc_automations_lock_columns_job.md) |

## `automations_overlap`

Esegue dbops.fn_apply_automazione_overlap (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_overlap` | si | SQL | zeroerp | [`CALL maintenance.proc_automations_overlap_job();`](funzioni/proc_automations_overlap_job.md) |

## `automations_storico`

Esegue dbops.fn_run_automations_storico (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_storico` | si | SQL | zeroerp | [`CALL maintenance.proc_automations_storico_job();`](funzioni/proc_automations_storico_job.md) |

## `automations_storico_provision`

Provision tabelle storico (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_storico_provision` | si | SQL | zeroerp | [`CALL maintenance.proc_automations_storico_provision_job();`](funzioni/proc_automations_storico_provision_job.md) |

## `automations_tx_id`

Esegue dbops.fn_run_automations_tx_id (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_tx_id` | si | SQL | zeroerp | [`CALL maintenance.proc_automations_tx_id_job();`](funzioni/proc_automations_tx_id_job.md) |

## `chiusura_scadenze_daily`

Sveglia la chiusura scadenze: accoda un lavoro per azienda, con l'identita' tecnica nello scope. NON chiude piu' le scadenze qui — lo fa il drenatore, dentro la RLS.

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `accoda_chiusura_scadenze` | si | SQL | zeroerp | [`CALL maintenance.proc_accoda_chiusura_scadenze_job();`](funzioni/proc_accoda_chiusura_scadenze_job.md) |

## `guardiano_digest`

Chi guarda il guardiano: ogni ora legge lo stato di digest_presidi dal panorama e, se e' MUTO, accoda un lavoro NOTIFICA_DIGEST_MUTO (uno al giorno) che il drenatore esegue spedendo col destinatario del backend. Vive in pgAgent perche' non muore con systemd.

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `guarda_il_digest` | si | SQL | zeroerp | [`CALL maintenance.proc_guardiano_digest_job();`](funzioni/proc_guardiano_digest_job.md) |

## `sync_auth_user_expired_daily`

Disattiva auth_user per risorse umane con finestra temporale scaduta (giornaliero ore 06:00)

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_sync_auth_user_expired` | si | SQL | zeroerp | [`CALL maintenance.proc_sync_auth_user_expired_job();`](funzioni/proc_sync_auth_user_expired_job.md) |

## `sync_storico_set_storicizza`

Setta DEFAULT=true su colonne "storicizza" ogni sabato ore 07:05

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_apply_storicizza` | si | SQL | zeroerp | [`call maintenance.proc_sync_storico_set_storicizza_job();`](funzioni/proc_sync_storico_set_storicizza_job.md) |

---
{% include-markdown "signature-core.md" %}

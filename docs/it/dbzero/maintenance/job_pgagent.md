# ⏰ Job pgAgent

> 📝 **Descrizione**
>
> I lavori a orario che pgAgent esegue in questo database: se sono accesi, quando partono (ora del server del database), che cosa chiama ogni step e quale processo di `dbops.processi` registrano. Pagina generata dalle tabelle di `pgagent`; l'ultima e la prossima corsa non ci sono apposta (cambiano a ogni giro): lo stato vivo e' in `dbops.vw_processi_programmazione`.

| Job | Acceso | Quando | Processo |
| --- | --- | --- | --- |
| `analyze_statistiche` | si | alle 02:30, ogni giorno | `analyze_statistiche` |
| `apply_storicizza_weekly` | si | alle 07:05, di sabato | `apply_storicizza_weekly` |
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
| `sync_storico_set_storicizza` | si | alle 07:00, di sabato | `sync_storico_set_storicizza` |

## `analyze_statistiche`

Statistiche del planner: ogni notte ANALYZE del database e autoverifica (maintenance.fn_analyze_statistiche). Una tabella rimasta senza statistiche fa fallire il job, nominata nel giornale.

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `analyze` | si | SQL | zeroerp | vedi sotto |

Step `analyze`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('analyze_statistiche') THEN
        CALL maintenance.proc_analyze_statistiche_job();
    END IF;
END
$sveglia$;
```

## `apply_storicizza_weekly`

Mette DEFAULT true sulle colonne storicizza delle tabelle di config.storico_set_storicizza: ogni sabato alle 07:05, dopo sync_storico_set_storicizza.

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_proc_apply_storicizza` | si | SQL | zeroerp | vedi sotto |

Step `run_proc_apply_storicizza`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('apply_storicizza_weekly') THEN
        call maintenance.proc_apply_storicizza_defaults_job();
    END IF;
END
$sveglia$;
```

## `automations_apply_fk_indexes_policy`

Applica policy indici FK ogni domenica ore 23:00 (populate=true)

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_apply_fk_index_policy` | si | SQL | zeroerp | vedi sotto |

Step `run_apply_fk_index_policy`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('apply_fk_index_policy') THEN
        CALL maintenance.proc_apply_fk_index_policy_job(true);
    END IF;
END
$sveglia$;
```

## `automations_attivo`

Esegue dbops.fn_run_automations_attivo (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_attivo` | si | SQL | zeroerp | vedi sotto |

Step `run_automations_attivo`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('automations_attivo') THEN
        CALL maintenance.proc_automations_attivo_job();
    END IF;
END
$sveglia$;
```

## `automations_audit_update`

Esegue dbops.fn_run_automations_audit_update (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_audit_update` | si | SQL | zeroerp | vedi sotto |

Step `run_automations_audit_update`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('automations_audit_update') THEN
        CALL maintenance.proc_automations_audit_update_job();
    END IF;
END
$sveglia$;
```

## `automations_cleanup_weekly`

Esegue cleanup automazioni (dbops) ogni domenica ore 23:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_cleanup` | si | SQL | zeroerp | vedi sotto |

Step `run_automations_cleanup`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('automations_cleanup') THEN
        CALL maintenance.proc_automations_cleanup_job();
    END IF;
END
$sveglia$;
```

## `automations_delete_block`

Applica il blocco di cancellazione alle tabelle dichiarate in dbops.automation_delete_block

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_delete_block` | si | SQL | zeroerp | vedi sotto |

Step `run_automations_delete_block`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('automations_delete_block') THEN
        CALL maintenance.proc_automations_delete_block_job();
    END IF;
END
$sveglia$;
```

## `automations_lock_columns`

Applica il lucchetto alle colonne dichiarate in dbops.automation_lock_columns

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_lock_columns` | si | SQL | zeroerp | vedi sotto |

Step `run_automations_lock_columns`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('automations_lock_columns') THEN
        CALL maintenance.proc_automations_lock_columns_job();
    END IF;
END
$sveglia$;
```

## `automations_overlap`

Esegue dbops.fn_apply_automazione_overlap (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_overlap` | si | SQL | zeroerp | vedi sotto |

Step `run_automations_overlap`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('automations_overlap') THEN
        CALL maintenance.proc_automations_overlap_job();
    END IF;
END
$sveglia$;
```

## `automations_storico`

Esegue dbops.fn_run_automations_storico (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_storico` | si | SQL | zeroerp | vedi sotto |

Step `run_automations_storico`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('automations_storico') THEN
        CALL maintenance.proc_automations_storico_job();
    END IF;
END
$sveglia$;
```

## `automations_storico_provision`

Provision tabelle storico (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_storico_provision` | si | SQL | zeroerp | vedi sotto |

Step `run_automations_storico_provision`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('automations_storico_provision') THEN
        CALL maintenance.proc_automations_storico_provision_job();
    END IF;
END
$sveglia$;
```

## `automations_tx_id`

Esegue dbops.fn_run_automations_tx_id (SCHEDULED) ogni giorno alle 21:00

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_automations_tx_id` | si | SQL | zeroerp | vedi sotto |

Step `run_automations_tx_id`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('automations_tx_id') THEN
        CALL maintenance.proc_automations_tx_id_job();
    END IF;
END
$sveglia$;
```

## `chiusura_scadenze_daily`

Sveglia la chiusura scadenze: accoda un lavoro per azienda, con l'identita' tecnica nello scope. NON chiude piu' le scadenze qui — lo fa il drenatore, dentro la RLS.

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `accoda_chiusura_scadenze` | si | SQL | zeroerp | vedi sotto |

Step `accoda_chiusura_scadenze`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('chiusura_scadenze_daily') THEN
        CALL maintenance.proc_accoda_chiusura_scadenze_job();
    END IF;
END
$sveglia$;
```

## `guardiano_digest`

Chi guarda il guardiano: ogni ora legge lo stato di digest_presidi dal panorama e, se e' MUTO, accoda un lavoro NOTIFICA_DIGEST_MUTO (uno al giorno) che il drenatore esegue spedendo col destinatario del backend. Vive in pgAgent perche' non muore con systemd.

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `guarda_il_digest` | si | SQL | zeroerp | vedi sotto |

Step `guarda_il_digest`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('guardiano_digest') THEN
        CALL maintenance.proc_guardiano_digest_job();
    END IF;
END
$sveglia$;
```

## `sync_auth_user_expired_daily`

Disattiva gli auth_user delle risorse umane con la finestra temporale scaduta: ogni ora al minuto 10, una volta per giorno aziendale.

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_sync_auth_user_expired` | si | SQL | zeroerp | vedi sotto |

Step `run_sync_auth_user_expired`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('sync_auth_user_expired_daily') THEN
        CALL maintenance.proc_sync_auth_user_expired_job();
    END IF;
END
$sveglia$;
```

## `sync_storico_set_storicizza`

Allinea config.storico_set_storicizza alla sua derivazione (aggiunge le tabelle con la colonna storicizza, pota le righe senza bersaglio): ogni sabato alle 07:00, prima di apply_storicizza_weekly.

| Step | Acceso | Tipo | Database | Chiama |
| --- | --- | --- | --- | --- |
| `run_sync_storico_set_storicizza` | si | SQL | zeroerp | vedi sotto |

Step `run_sync_storico_set_storicizza`:

```sql
DO $sveglia$
BEGIN
    -- Cancello della sveglia (85_pgagent/20261016-30): da spento
    -- il lavoro non parte e il giornale non scrive niente.
    IF maintenance.fn_sveglia_accesa('sync_storico_set_storicizza') THEN
        call maintenance.proc_sync_storico_set_storicizza_job();
    END IF;
END
$sveglia$;
```

---
{% include-markdown "signature-core.md" %}

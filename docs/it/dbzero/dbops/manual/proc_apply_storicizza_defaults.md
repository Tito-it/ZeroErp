## 📘 Documentazione Concettuale – Procedura `dbops.apply_storicizza_defaults()`

> 🔁 **Collegamenti utili**
>
> Approfondimenti tabelle: 
>
> * [`config.storico_set_storicizza`](/dbzero/config/tabelle/storico_set_storicizza)
>
> Scheduler:
> * [Processi pgAgent](/postgresql/pgAgent)

---

### 🎯 Scopo Principale

La procedura `dbops.apply_storicizza_defaults()` ha il compito di **impostare il valore di default `true` per la colonna `storicizza`** in tutte le tabelle elencate nella tabella di configurazione `config.storico_set_storicizza`. È utilizzata per **garantire che le nuove righe inserite siano automaticamente storicizzate**, ove previsto.

---

### ⚙️ Dettaglio Funzionale

Per ogni record della tabella `config.storico_set_storicizza`, la procedura:

1. Estrae il nome completo della tabella nel formato `schema.tabella`.
2. Divide il nome nelle due parti `schema` e `tabella`.
3. Esegue dinamicamente un comando SQL `ALTER TABLE` per settare `DEFAULT true` sulla colonna `storicizza`.


---

### 🕒 Esecuzione Programmata (pgAgent)

La procedura è **eseguita automaticamente ogni sabato alle ore 07:00** tramite un job pgAgent denominato `apply_storicizza_defaults_weekly`.

#### 🧩 Dettagli del job pgAgent

* **Classe job**: `Routine Maintenance`
* **Nome job**: `apply_storicizza_defaults_weekly`
* **Descrizione**: Setta `DEFAULT=true` su colonne `storicizza` ogni sabato alle 07:00
* **Step**: esegue `SELECT dbops.apply_storicizza_defaults();`
* **Schedule**: ogni **sabato** alle **07:00** (solo al minuto 0)

#### 🧾 Codice job

```plpgsql
DO $$
DECLARE
  v_jobid   INTEGER;
  v_classid INTEGER;
BEGIN
  SELECT jclid INTO v_classid
    FROM pgagent.pga_jobclass
   WHERE jclname = 'Routine Maintenance'
   LIMIT 1;

  IF v_classid IS NULL THEN
    RAISE EXCEPTION 'Job class "Routine Maintenance" non trovata';
  END IF;

  DELETE FROM pgagent.pga_job WHERE jobname = 'apply_storicizza_defaults_weekly';

  INSERT INTO pgagent.pga_job(
    jobjclid, jobname, jobdesc, jobenabled
  ) VALUES (
    v_classid,
    'apply_storicizza_defaults_weekly',
    'Setta DEFAULT=true su colonne storicizza ogni sabato ore 07:00',
    TRUE
  ) RETURNING jobid INTO v_jobid;

  DELETE FROM pgagent.pga_schedule WHERE jscjobid = v_jobid;

  INSERT INTO pgagent.pga_schedule(
    jscjobid, jscname, jscenabled,
    jscminutes, jschours, jscweekdays,
    jscmonthdays, jscmonths, jscstart
  ) VALUES (
    v_jobid,
    'sat_07',
    TRUE,
    (SELECT array_agg((i = 0)::boolean) FROM generate_series(0,59) AS g(i)),
    (SELECT array_agg((i = 7)::boolean) FROM generate_series(0,23) AS g(i)),
    ARRAY[FALSE, FALSE, FALSE, FALSE, FALSE, FALSE, TRUE]::boolean[],
    array_fill(TRUE, ARRAY[32])::boolean[],
    array_fill(TRUE, ARRAY[12])::boolean[],
    now()
  );

  INSERT INTO pgagent.pga_jobstep(
    jstjobid, jstname, jstenabled, jstkind,
    jstcode, jstdbname, jstonerror
  ) VALUES (
    v_jobid,
    'run_apply_storicizza',
    TRUE,
    's',
    $$
      SELECT dbops.apply_storicizza_defaults();
    $$,
    current_database(),
    FALSE
  );
END
$$;
```

---

### 🔐 Sicurezza & Best Practice

* È buona norma testare la procedura manualmente prima di attivare il job.
* Verificare che la colonna `storicizza` esista in tutte le tabelle dichiarate.
* Utilizzare la tabella `config.storico_set_storicizza` come unico punto di controllo per le tabelle storicizzate.

---

{% include-markdown "signature-core.md" %}

## 📘 Documentazione Concettuale – Procedura `maintenance.proc_analyze_statistiche_job`

> 👀 **Vedi anche**
>
Approfondimento funzioni:
>
[`maintenance.fn_analyze_statistiche`](/dbzero/maintenance/manual/fn_analyze_statistiche)
> [`maintenance.fn_run_and_log`](/dbzero/maintenance/manual/fn_run_and_log)
>
Approfondimento tabelle:
>
[`dbops.processi`](/dbzero/dbops/manual/processi)

---
### 🎯 Scopo Principale
(latest review 14-10-2026)

Il wrapper del job pgAgent **`analyze_statistiche`**: esegue
[`fn_analyze_statistiche()`](/dbzero/maintenance/manual/fn_analyze_statistiche)
**passando dal giornale** (`fn_run_and_log`), sotto il codice del processo.

```sql
PROCEDURE maintenance.proc_analyze_statistiche_job()
```

Lo chiamano due strade, con la stessa procedura:

| Dove | Chi la chiama | Quando |
| --- | --- | --- |
| dbdev, installazioni | il job pgAgent `analyze_statistiche` (`85_pgagent/20261014-53`) | ogni notte alle 02:30 |
| CI e scratch | la convergenza dei job strutturali (`90_end/ci_apply/20260926-10`) | per ultima, dopo il caricamento e prima dei pgTAP |

⭐ **Il giornale è ciò che rende visibile un fallimento.** Se l'autoverifica
solleva `E_STATISTICHE_MANCANTI`, `fn_run_and_log` scrive la riga rossa **fuori
transazione** in `maintenance.job_run_log`, con le tabelle nominate nel
messaggio. Da lì la vedono il panorama dei processi e il digest.

⚠️ `p_jobname` è il **codice del processo** (`analyze_statistiche`), uguale al
jobname pgAgent: è così che il giornale risale all'attore e che la convergenza
in CI riconosce la riga di quel giro.

⚠️ Nessun `COMMIT`: in CI gira dentro la transazione del changeSet.

### Il diritto del ruolo

Il ruolo che esegue deve poter analizzare **tutte** le tabelle del perimetro:
superuser, proprietario, oppure `pg_maintain`. È provisioning, mai un changeSet
(linee-guida-sql §11.6):

* **CI** — Liquibase `ci_apply` gira come `zeroerp`, mentre le tabelle di
  Liquibase e `internal.project_metadata` le crea il provision-pre come
  `postgres`: `GRANT pg_maintain TO zeroerp` nel passo di bootstrap di
  `ci.yaml`, `ci-validate.yaml` e `scripts/ci-local.sh`;
* **dbdev** — la procedura è `SECURITY DEFINER` (come tutte le
  `maintenance.proc_*_job`, `20261014-55`): chiunque la chiami, gira come il
  **proprietario** del database, che possiede tutte le tabelle del perimetro.
  Se non fosse così, la riga rossa del giornale nomina le tabelle.

Brief: `brief-db-statistiche-tabelle-job-notturno` (D15).

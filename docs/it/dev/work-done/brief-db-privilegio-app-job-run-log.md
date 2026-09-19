# Brief DB — `zeroerp_app` legge `maintenance.job_run_log`: il privilegio ha bisogno di una sede

> **Destinatari:** team DB (`dev/db-tid`). Nessuna modifica lato backend (§6).
>
> **Tipo:** brief di correzione — quarta occorrenza della regola di
> [linee-guida-sql §11.9](../../linee-guida-sql.md) (*un privilegio che esiste
> su una sola macchina è un ricordo, non una configurazione*), dopo `USAGE` su
> `maintenance` (2026-09-09), lo schema `django` (2026-09-13) e i registri
> append-only (2026-09-11).
>
> **Stato:** ✅ **CHIUSO e archiviato in `work-done/` il 2026-09-19 (sera)**.
> Letto dalle sorgenti, non supposto. §3.1 fatto: blocco `maintenance` in
> fondo a `scripts/sql/provision_db_roles.sql` (`USAGE` + solo `SELECT` su
> `job_run_log` e `vw_job_run_da_guardare`, `to_regclass`), e i due commenti
> corretti; in più — oltre il brief, e con la ragione scritta nel file —
> il changeSet gemello `90_end/20260919-08` per i database già provisionati
> (`EXECUTED` su dbdev alle 16:46, `databasechangelog`). §3.2 fatto:
> `db/pgtap/maintenance/test-app-postura-job-run-log-v1.sql` (plan 10: postura
> con `has_*_privilege`, la porta DEFINER, `lives_ok`/`throws_ok 42501` come
> app). Tutto in `5d8331f94` (17:09, con `linee-guida-sql` §11.9 «quarta
> volta» e il manuale di `job_run_log`), mergiato fino a `main` (PR #1623).
> **§6 verificato** sulla corsa `35451924195` (`Tito-dev`, verde): «Django
> tests» `Ran 5076 tests … OK (skipped=46)`, **zero** `permission denied for
> table job_run_log` nel log del container; il pgTAP nuovo verde su DB da
> zero; e `maintenance/test-job-run-registrazione.sql` — l'`ERRORE_FIXTURE`
> in `baseline-rossi-ci.tsv` con la causa mai letta — dichiarato **RIENTRATO**
> dalla CI, tolto con `scripts/pgtap-baseline-ci-rientrati.sh` (363 → 362).
>
> ⚠️ **Tre code, che l'archiviazione non chiude:**
> **§3.3** `maintenance.test_pgagent_log` ha ancora `zeroerp_app=r` su dbdev,
> a mano, senza lettore; il presidio non lo pinna né sì né no — resta la
> decisione (`REVOKE` a mano su dev + riga nel pgTAP, o un lettore che non ho
> trovato). **§3.4** `check_db_role_access.sql` esclude ancora `maintenance`
> per intero: non è stato verificato. **§5** è **aperto e cresce**: nella
> corsa verde `35451924195` le righe `permission denied for schema dbops` di
> `zeroerp_log` sono **16 114** (erano 861 nella corsa rossa del mattino —
> fatto datato, non motivo: da quando i test girano come app attraversano più
> DB). Portato in `PROJECT_CONTEXT.md` «Aperto» perché non resti sepolto qui.
> Sotto, il testo com'era — «CI rossa, nessun changeSet» — che al mattino
> diceva il vero.
>
> **Origine:** Tid, 2026-09-19 — *«problema CI GitHub»*, con il traceback di
> `test_processi_vuole_identita`.

---

## 1. Il difetto, sul modello

Il **backend legge `maintenance.job_run_log` direttamente**, come ruolo
applicativo, in cinque punti — e lo fa da mesi, non da oggi:

| Sede | Cosa legge |
| --- | --- |
| [maintenance_repository.py](../../../../backend/apps/core/db/maintenance_repository.py) `list_job_runs`, `list_job_summary` | l'elenco e il riepilogo dei giri (lo scopo dichiarato del file è *«accesso in lettura a maintenance.job_run_log»*) |
| [processi_repository.py](../../../../backend/apps/core/db/processi_repository.py) `list_processi`, `list_run_processo` | ultimo run / ultimo esito / conteggio per processo (lista `amm.processi`), e le corse di un processo |
| [amm_software/api/views.py](../../../../backend/apps/amm_software/api/views.py) `ProcessiRunView` | le corse recenti di un processo |
| [vendite/api/views.py](../../../../backend/apps/vendite/api/views.py) `ApiFatturazioneEsiti` | gli esiti dei giri per corsia |

È un fatto del **contratto del software**: la consultazione dei giri è una
funzione dell'amministrazione, e la fa l'app con una `SELECT`. La **scrittura**
invece non passa mai dall'app: `script.fn_job_run_start` / `fn_job_run_end`
sono `SECURITY DEFINER`, e il canale fuori transazione scrive come
`zeroerp_log` (`INSERT`, `90_end/20260905-38`).

⛔ **Il privilegio che rende possibile quella lettura non ha nessuna sede.**
Sul database di sviluppo c'è — `maintenance.job_run_log` →
`zeroerp_app=r/titodb` — ma **dato a mano**: nessun changeSet lo concede,
`scripts/sql/provision_db_roles.sql` non lo concede, e lo schema `maintenance`
è **fuori dalla whitelist** `_app_schemas` per decisione (riceve il solo
`USAGE`). Anzi, il provisioning afferma il **contrario** del contratto qui
sopra, due volte:

> *«Escluso intenzionalmente: maintenance (pgAgent: l'app non ne legge né
> scrive le tabelle)»* — e più sotto — *«il ruolo applicativo non legge né
> scrive le tabelle dei job, quindi non riceve nessun privilegio su tabelle,
> sequenze o funzioni di quello schema»*.

Il commento descrive una postura che il software non ha mai avuto: **legge sì,
scrive no**. La vista sorella `maintenance.vw_job_run_da_guardare` ha invece
la sua sede (GRANT nel changeSet che la crea, `20_code/maintenance/20260905-39`)
— quindi la forma «l'app legge in `maintenance`» è già ammessa e dichiarata
per un oggetto, e non per l'altro.

Verificato sul DB di sviluppo il 2026-09-19 (struttura, non popolazione): gli
**unici tre** oggetti fuori whitelist con un'ACL per `zeroerp_app` sono
`maintenance.job_run_log` (r, senza sede), `maintenance.vw_job_run_da_guardare`
(r, con sede) e `maintenance.test_pgagent_log` (r, senza sede **e senza nessun
lettore** nel backend). Le viste `dbops.vw_processi_programmazione` e
`dbops.vw_run_senza_attore` attraversano `job_run_log` con i privilegi del
proprietario (nessuna è `security_invoker`): non sono coinvolte.

## 2. Perché esce oggi, e perché non è un difetto dei test

Dal 2026-09-19 (`9c11a485b`, `ci-validate.yaml`) il passo «Django tests» **si
connette come `zeroerp_app`**, non più come l'owner `zeroerp` — la stessa
scelta del runner pgTAP, per esercitare la RLS. Da quel momento ogni test che
tocca il DB provvisto vede i privilegi **veri** del ruolo applicativo, cioè
quelli che una installazione nuova concede. Prima, l'owner saltava tutto.

I 16 errori sono le letture reali della tabella:

| Test | Errori |
| --- | --- |
| `apps.core.tests.db.test_lista_proiezione_campo_sorgente` — lista `amm.processi` (proiezione + 12 ordinamenti dichiarati) | 13 |
| `apps.core.tests.db.test_job_liveness_due_chiavi` | 2 |
| `apps.core.tests.db.test_processi_vuole_identita` | 1 |

Tutti `permission denied for table job_run_log`, sotto `list_processi` o
`list_job_runs`. ⭐ **I test sono il presidio che ha funzionato**: in sviluppo
sono verdi perché il privilegio a mano c'è, e sono rossi sull'unica macchina
che non copia la risposta da dev. Non vanno toccati, marcati né skippati.

## 3. Cosa si chiede

Un privilegio **mirato** — `SELECT`, e solo `SELECT`, su `maintenance.job_run_log`
per il ruolo applicativo — in una sede che una installazione nuova attraversa.

### 3.1 `scripts/sql/provision_db_roles.sql` — la sede

Accanto al blocco «ECCEZIONE: `USAGE` su `maintenance`», in fondo allo script:
`GRANT SELECT ON maintenance.job_run_log TO <app_role>`, nella stessa forma
(idempotente, additivo, saltato se la tabella manca — `to_regclass`, come
fanno già i `REVOKE` mirati poco sopra).

⭐ **È la sede giusta, e non ne serve una seconda**: in `ci-validate.yaml` il
passo «Privilegi del ruolo applicativo» gira **dopo entrambi i migratori** e
prima dei test Django; `scripts/ci-local.sh` lo rilancia sullo scratch (punto
3 della sua preparazione). Su dev il privilegio c'è già; rilanciare il
provisioning lo rende **dichiarato** invece che ricordato. Un changeSet
`90_end` in più sarebbe un doppione della stessa riga in due posti.

`maintenance` **resta fuori** dalla whitelist: nessun `INSERT`/`UPDATE`/`DELETE`
sulle tabelle, nessun `USAGE` sulle sequenze, nessun `EXECUTE` su
`maintenance.fn_*` / `proc_*` — la scrittura passa dai `DEFINER` di `script` e
da `zeroerp_log`, e deve continuare a passare di lì.

E il **commento va corretto**, nei due punti citati in §1: la postura è *«legge
il giornale dei giri, non lo scrive; non tocca il resto dello schema»*. Un
commento che afferma il contrario del contratto è la ragione per cui questo
grant è rimasto a mano per mesi senza che nessuno lo cercasse.

### 3.2 Il presidio pgTAP

Un test di postura con `has_table_privilege`, sullo stampo di
`db/pgtap/dbops/test-registri-append-only-postura-v1.sql` e di
`test-app-postura-schema-django-v1.sql`:

| Oggetto | `zeroerp_app` |
| --- | --- |
| `maintenance.job_run_log` | `SELECT` **true**; `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE` **false** |
| `maintenance.test_pgagent_log` | `SELECT` **false** (vedi 3.3) |
| schema `maintenance` | `USAGE` true, `CREATE` false |

Più il **comportamento**: come app, `SELECT count(*) FROM maintenance.job_run_log`
deve rispondere (`lives_ok`), e un `INSERT` diretto deve essere respinto
(`throws_ok` con SQLSTATE `42501`).

### 3.3 `maintenance.test_pgagent_log` — decisione, non richiesta

Su dev ha `zeroerp_app=r`, dato a mano, e **nessun lettore** nel backend né
nei pgTAP. Un privilegio senza lettore non ha una sede da cui essere
dichiarato: la proposta è **non concederlo** (il provisioning non lo nomina) e
pinnare `SELECT = false` nel presidio, il che comporta un `REVOKE` a mano su
dev — è un'azione del team DB, e per questo sta qui come decisione aperta e
non come riga del §3.1. Se invece un lettore c'è e non l'ho trovato, va
trattato come `job_run_log`.

### 3.4 `scripts/sql/check_db_role_access.sql`

Esclude `maintenance` per intero (`NOT IN ('information_schema', 'maintenance')`).
Da verificare che la diagnostica sappia mostrare l'eccezione mirata senza
segnalarla come anomalia; se serve, il caso si dichiara lì con la stessa
forma dell'eccezione `USAGE`.

## 4. Cosa NON si chiede

- ⛔ **Non** mettere `maintenance` in `_app_schemas`: aprirebbe scrittura ed
  `EXECUTE` su tutto lo schema per chiudere una `SELECT` su una tabella.
- ⛔ **Non** spostare le letture del backend dietro una funzione `DEFINER` o
  una vista: sono liste amministrative paginate e filtrate, e il modello
  «l'app legge il giornale» è già quello dichiarato per la vista sorella.
- ⛔ **Non** toccare i test rossi: sono il presidio (§2).

## 5. Seconda cosa vista nella stessa corsa — fatto datato, cantiere a parte

Nel log del container Postgres della corsa `35436621558` (passo «Stop
containers»), **861 righe** `permission denied for schema dbops` (24 + 837),
tutte con il seguito:

```text
dbops.fn_get_or_create_session_tx_id: errore durante la chiamata dblink a
dbops.fn_generate_tx_id: permission denied for schema dbops; uso la
sentinella uuid_nil e non pubblico la GUC di sessione.
```

È `zeroerp_log`, l'utente del DSN dblink, che in CI **non ha `USAGE` su
`dbops`**. La sede del privilegio esiste —
`scripts/sql/provision_dblink_log_channel.sql` (USAGE su `dbops`, INSERT su
`error_log`, la sequenza) — ma la CI **non la esegue**: il changeSet che la
incarna (`90_end/20260205-42`) è `context: disabled`, e il bootstrap di
`ci-validate.yaml` crea il ruolo e imposta il DSN senza concedergli niente su
`dbops`. `90_end/20260905-38` gli dà `maintenance`, non `dbops`. Su dev il
privilegio c'è (`dbops` → `zeroerp_log=U/titodb`): stessa forma di §1.

**Effetto**: in CI ogni test Django che attraversa il DB lavora con `tx_id =
uuid_nil`. Non fa fallire nulla — il ripiego è progettato apposta — ma ogni
asserzione sul `tx_id` reale è verde per sottrazione o skippata, e l'audit
non correla niente. È un cantiere separato (tocca il workflow, che è condiviso
BE/DB): la via più corta è un passo in CI che lancia
`provision_dblink_log_channel.sql` dopo il bootstrap, oppure un changeSet
`90_end` gemello di `20260905-38` per `dbops`. Decisione a Tid.

## 6. Lato backend

Niente da fare. A DB atterrato: rilanciare la CI sulla PR #1620 e verificare
che i 16 errori scompaiano e che il log del container non contenga più
`permission denied for table job_run_log`.

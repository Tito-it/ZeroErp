# Brief DB — Una corsa saltata non è una corsa riuscita

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09, durante la revisione di L4 di
> [brief-be-db-fe-un-solo-fuso-aziendale](../work-done/brief-be-db-fe-un-solo-fuso-aziendale.md) (T-9).
> **A chi:** team DB (`dev/db-tid`); ricadute BE in §6.
> **Decisione di Tid (2026-10-09):** aprire il brief.
> **Stato:** ✅ **lato DB chiuso** (2026-10-10, §8.5): changeSet `20261010-20` … `-25`
> **applicati** da Tid, pgTAP di `maintenance/` **senza rossi** (compreso il nuovo
> `test-job-run-saltata-v1`). Resta il BE (§8.6). **Rivisto** dalla sessione DB
> (`dev/db-tid`) il 2026-10-09: decisioni di Tid e lavoro DB nel §8, che prevale sui §3–§5
> dove dissente.

## 1. Il fatto

`script.fn_job_run_start`, quando il lock della corsia è occupato, scrive su
`maintenance.job_run_log` una riga **già chiusa** con `ok = TRUE` e
`message = 'skip: another run in progress'` (corpo nella doc auto-generata,
`script/funzioni/fn_job_run_start.md`).

Quella riga non ha fatto il lavoro, ma per il modello è indistinguibile da una corsa riuscita:
l'unica differenza è il **testo** di `message`. Nessuna colonna, nessun CHECK, nessun valore di
`ok` la separa.

## 2. Perché è un difetto del modello (non dei dati)

Ogni lettore che chiede «il lavoro è stato fatto?» o «qual è l'ultima corsa?» conta la skip
come una corsa riuscita. Il caso nasce dalla struttura (lock occupato = riga `ok = TRUE`), non
da una popolazione.

### 2.1 Le sveglie calendariali saltano un periodo intero, senza errore (BE, T-9)

`e_dovuto` (l'`ExecCondition=` dei timer) chiede a `MaintenanceRepository.corsa_riuscita_dal`
se la corsia ha una corsa `ok` dall'inizio del periodo aziendale. Scenario:

1. alle 07:00 scatta il digest giornaliero mentre una corsa avviata da «Esegui ora» tiene il
   lock → riga skip, `ok = TRUE`;
2. la corsa a mano fallisce (`ok = FALSE`);
3. alle 08:00, 09:00, … `e_dovuto` trova la skip delle 07:00 e risponde «già fatto».

Il digest del giorno non parte più. Sulla fatturazione differita il periodo è il **mese**.

### 2.2 Una corsa appesa sparisce dal presidio

Una corsa col processo vivo ma bloccato tiene il lock di sessione. Ogni sveglia successiva
scrive una skip `ok = TRUE`, più recente della corsa appesa:

* `maintenance.vw_job_run_da_guardare` prende **l'ultima** riga per `jobname`
  (`DISTINCT ON … ORDER BY started_at DESC`): l'ultima è la skip, e il ramo «presa e mai
  chiusa: il job è morto senza dire niente» non scatta più;
* `dbops.vw_processi_programmazione` conta la skip come `ultima_corsa` e come `ultimo_esito`:
  il processo risulta **OK** entro la tolleranza, mentre il lavoro è fermo.

Cioè il caso che quei presidi esistono per vedere viene coperto proprio dalla sveglia che lo
dovrebbe far emergere.

## 3. Che cosa si chiede

Un **marcatore strutturale** della corsa saltata, scritto da `fn_job_run_start` sul ramo
del lock occupato, e i lettori del DB che lo rispettano.

**Proposta (A), raccomandata:** colonna `saltata boolean NOT NULL DEFAULT false` su
`maintenance.job_run_log`, `TRUE` sulla sola riga di skip. CHECK di coerenza: una riga
saltata è chiusa (`NOT saltata OR ended_at IS NOT NULL`).

Che cosa resta di `ok` sulla riga saltata va deciso insieme (§5): la proposta è lasciarlo
`TRUE`, perché un salto per sovrapposizione **non è un guasto** e non deve accendere
`vw_job_run_da_guardare` come un fallimento. La distinzione la porta `saltata`, non `ok`.

**Alternativa (B):** `ok = NULL` sulla riga di skip, senza colonna nuova. Scartata nella
proposta: `ok IS NULL` oggi significa «corsa senza esito» (aperta, o chiusa senza esito:
`_helpers.corsa_conclusa` lo dichiara ammesso). Caricarlo di un secondo significato fa
indovinare a ogni lettore quale dei due vale.

⛔ Non basta filtrare `message <> 'skip: …'` nei lettori: è un testo libero, e un filtro sul
testo è la seconda sede della stessa regola.

## 4. I lettori da allineare (lato DB)

Dalla doc auto-generata, 2026-10-09 (`job_run_log` nelle viste e nelle funzioni):

| Oggetto | Che cosa deve escludere `saltata` |
| --- | --- |
| `maintenance.vw_job_run_da_guardare` | la CTE `ultima`: l'ultima corsa **vera** per `jobname` |
| `dbops.vw_processi_programmazione` | `ultima_corsa`, `ultima_corsa_pgagent`, `ultimo_esito` |
| `dbops.vw_run_senza_attore` | da valutare: la skip porta l'attore (rev 2026-09-04), quindi oggi non è un rilievo; verificare che `ultimo_ok` non la scelga |
| `maintenance.fn_run_and_log`, `maintenance.fn_job_run_log_failure` | da verificare: scrivono, non leggono l'ultima corsa |

⚠️ Il censimento dei lettori è del team DB, sul corpo vero: la tabella sopra è un punto di
partenza, non l'elenco chiuso.

## 5. Decisioni da prendere (team DB, poi Tid)

1. (A) o (B) di §3.
2. Con (A): `ok` sulla riga saltata resta `TRUE`?
3. La skip conta come **segno di vita** per la liveness (`vw_processi_programmazione` con
   `segno_di_vita = GIORNALE`)? Proposta: **no**. Il timer che si sveglia è vivo, ma il lavoro
   no, e il segno di vita è un contratto del processo, non della sveglia.

## 6. Ricadute BE (dopo l'applicazione)

* `MaintenanceRepository.corsa_riuscita_dal`: `AND NOT saltata`, con un test sul DB vero che
  **costruisce** la riga di skip (lock preso da una seconda connessione) e prova che il periodo
  resta dovuto (`tests/db/test_corsa_riuscita_dal_db`).
* `MaintenanceRepository.job_liveness` / `list_job_summary` e
  `ProcessiRepository`: da verificare con la stessa domanda, «l'ultima corsa vera».
* `JobRunHandle.acquired` resta com'è: è il BE a sapere di aver saltato, ma la riga la scrive
  il DB.

## 7. pgTAP

* lock occupato → riga con `saltata = TRUE`, chiusa;
* corsa normale → `saltata = FALSE`;
* `vw_job_run_da_guardare`: una corsa aperta da più di un'ora **seguita da** una skip resta
  «presa e mai chiusa»;
* `vw_processi_programmazione`: una sola skip nella finestra di tolleranza non rende OK un
  processo senza corse vere.

## 8. Revisione DB e decisioni (2026-10-09)

Analisi della sessione DB sul corpo vero (doc auto-generata, 2026-10-09), decisioni di Tid lo
stesso giorno. Dove dissente dai §3–§5, vale questo paragrafo.

### 8.1 Che cosa la revisione ha trovato

* **Gli scrittori della skip sono due, non uno.** Anche `maintenance.fn_run_and_log` ha un ramo
  sul lock occupato, e scrive una riga con `ok = TRUE` e **`ended_at` NULL**: «riuscita e mai
  chiusa». Il §4 la dava come «scrive, non legge».
* **`script.fn_job_run_end` chiude qualunque riga** e ne riscrive `ok`: chiamata su una riga
  saltata, la trasformerebbe in una corsa vera e cancellerebbe il marcatore.
* **`vw_processi_programmazione`: le tre colonne fanno tre domande diverse.**
  `ultima_corsa_pgagent` alimenta `GIRA_E_NON_REGISTRA` («pgAgent scatta e il giornale lo
  registra?»): la skip **è** una registrazione. `ultima_corsa` alimenta `TIMER_FERMO`: la skip
  prova che il timer va. Solo `ultimo_esito` parla del lavoro.
* **`vw_run_senza_attore`** non ha una colonna `ultimo_ok`: chiede solo se l'ultima corsa ha un
  attore, e la skip ce l'ha. Non si tocca.

### 8.2 Decisioni (Tid, 2026-10-09)

| # | Decisione |
| --- | --- |
| D1 | Proposta (A): colonna `saltata boolean NOT NULL DEFAULT false` su `maintenance.job_run_log`. |
| D2 | Sulla riga saltata **`ok` è NULL**, non `TRUE` (rettifica del §5.2). Il motivo sul modello: una skip non ha un esito del lavoro, e con `NULL` la domanda «è riuscita?» (`ok IS TRUE`) la scarta da sola, senza un `AND NOT saltata` da ricordare in ogni lettore presente e futuro. `saltata` toglie al `NULL` il doppio significato che il §3 temeva. CHECK di riga: `NOT saltata OR (ended_at IS NOT NULL AND ok IS NULL)`. |
| D3 | La skip **conta** come segno di vita della sveglia (rettifica del §5.3): la corsa appesa la mostra `vw_job_run_da_guardare`, non un `TIMER_FERMO` falso. Nessuno stato `APPESO` nuovo, per ora. |
| D4 | **Nessuna bonifica** delle skip già scritte: restano `saltata = false` col loro testo. Siamo in sviluppo. |

### 8.3 Lavoro DB

1. `maintenance.job_run_log`: colonna `saltata` (D1), CHECK del D2, COMMENT.
2. `script.fn_job_run_start`, ramo lock occupato: `saltata = TRUE`, `ok` NULL, `ended_at`
   valorizzato. Il `message` resta come testo per chi legge, non è più il marcatore.
3. `maintenance.fn_run_and_log`, ramo lock occupato: idem, con `ended_at` (oggi manca).
4. `script.fn_job_run_end`: rifiuta una riga saltata (codice nuovo di classe `TECNICO`: chiudere
   una corsa mai presa è un chiamante rotto; nome da registrare nei due registri, ok Tid).
5. `maintenance.vw_job_run_da_guardare`: la CTE `ultima` esclude `saltata`.
6. `dbops.vw_processi_programmazione`: solo `ultimo_esito` esclude `saltata`; `ultima_corsa` e
   `ultima_corsa_pgagent` restano su tutte le righe (D3).
7. Manual di `job_run_log`, delle due viste e delle tre funzioni.

### 8.4 pgTAP (al posto del §7)

* lock occupato da una seconda sessione (dblink) → riga `saltata`, chiusa, `ok` NULL; idem per
  `fn_run_and_log`;
* corsa normale → `saltata = false`;
* il CHECK rifiuta una riga saltata con `ok` valorizzato o aperta;
* `fn_job_run_end` su una riga saltata → rifiuto;
* `vw_job_run_da_guardare`: corsa aperta da più di un'ora **seguita da** una skip → resta
  «presa e mai chiusa»;
* `vw_processi_programmazione`: una skip nella tolleranza tiene `OK` il timer (niente
  `TIMER_FERMO`), e `ultimo_esito` è quello della corsa vera.

### 8.5 Stato del lavoro DB (2026-10-10)

| # | Cartella | Cosa |
| --- | --- | --- |
| `-20` | `00_schema/maintenance` | `job_run_log.saltata boolean NOT NULL DEFAULT false`; CHECK `chk_job_run_log_saltata` (`NOT saltata OR (ended_at IS NOT NULL AND ok IS NULL)`); COMMENT |
| `-21` | `20_code/script` | `fn_job_run_start`: la skip nasce `saltata`, chiusa, `ok` NULL |
| `-22` | `20_code/maintenance` | `fn_run_and_log`: idem, e ora con `ended_at` (prima mancava); firma ancorata con `%TYPE` |
| `-23` | `20_code/script` | `fn_job_run_end`: rifiuta una riga saltata, `E_JOB_RUN_SALTATA_NON_CHIUDIBILE` (TECNICO) |
| `-24` | `20_code/maintenance` | `vw_job_run_da_guardare`: la CTE `ultima` esclude le saltate |
| `-25` | `20_code/dbops` | `vw_processi_programmazione`: solo `ultimo_esito` esclude le saltate; COMMENT sulle tre colonne del giornale |

`80_data`: una riga in `codici_errore.csv` e `messaggi_errore.csv` (id 1244).

Corpi presi dall'ultimo YAML di ogni oggetto, verificati identici al vivo (`prosrc` su
`zeroerp_ci`); il corpo della vista dei processi è estratto dal `20261009-34` da uno script che
dichiara l'unica sostituzione. Firme, `SECURITY`, `search_path` e ACL invariati.

**pgTAP nuovo:** `maintenance/test-job-run-saltata-v1.sql` (11 asserzioni, runner owner):
colonna e CHECK, corse vere che restano vere, il rifiuto di `fn_job_run_end`, la corsa appesa
seguita da una skip, `ultimo_esito` sulla corsa vera, la skip che tiene OK il timer (D3), e i
**due rami skip veri**, col lock tenuto da una seconda sessione via dblink (dove dblink non si
apre, cioè su dev, vanno in `skip()` col motivo). Il ramo skip, che
`test-job-run-attore.sql` dichiarava «non collaudabile qui», ora ha un test.

#### La prova (2026-10-10), e cosa non copre

Su `zeroerp_ci`, come `zeroerp`, **SQL estratto dagli YAML** in ordine di numero, `sqlCheck`
delle preCondition valutate prima (verdi), `80_data` simulato con le righe vere del CSV, vincoli
differiti come Liquibase, tutto in `BEGIN … ROLLBACK`. Scratch verificato intatto dopo.

| Prova | Esito |
| --- | --- |
| pgTAP nuovo | 11/11 (seconda sessione dblink aperta: i rami skip veri sono girati) |
| **mutazioni** (oggetto rimesso alla versione di prima) | `fn_job_run_start` → rosso il 10; `fn_run_and_log` → l'11; `fn_job_run_end` → il 6; vista di presidio → il 7; vista processi → l'8; skip esclusa anche dal segno di vita → il 9 (`MUTO/TIMER_FERMO`) |
| firme, `SECURITY`, `search_path`, ACL, una funzione per nome | identici al vivo |
| viste: `pg_get_viewdef` prima/dopo | cambia solo il filtro `NOT saltata` |
| `plpgsql_check` sulle tre funzioni | 0 errori |
| 18 pgTAP esistenti prima/dopo (giornale, processi, guardiano, postura, e i presidi trasversali: riferimenti morti, catalogo messaggi, rubinetto, stati-check, codici-motivo, storico-scope) | stessi ok in tutti |
| guardrail statici (runOnChange, preCondition/seed, DDL su trigger, GRANT batch, v1, letterali, timestamp, preambolo pgTAP) | verdi |

⚠️ Due cose da dire:
* `test-app-postura-job-run-log-v1` ha **1 rosso prima e dopo** (il 9): gira come owner, che
  ha il privilegio che il test vuole negato all'app. Atteso fuori dal runner.
* `test-vw-job-run-da-guardare` ha dato **5 ok alla prima corsa «prima»** e 6/6 in quattro
  corse successive, senza i changeSet: un'oscillazione non riprodotta, non un effetto di questo
  lavoro (il «dopo» è sempre 6/6). Nessuna riga lasciata nel giornale dello scratch.

**Non coperto:** il loader vero dei due CSV (simulato con `INSERT`); la RLS e il runner come
applicazione; dbdev; il canale di log dblink (nella prova la riga di `error_log` non si scrive,
perché il codice nuovo non è committato). L'apply e la corsa del runner sono di Tid.

✅ **Apply e corsa del runner (Tid, 2026-10-10):** migrazione applicata, pgTAP di `maintenance/`
senza rossi. Una corsa lanciata prima dell'apply aveva dato 11/11 rossi su
`test-job-run-saltata-v1` («la colonna saltata non esiste»): era il database non ancora migrato.

### 8.6 Ricadute BE (al posto del §6)

* `error_policies_generated.py` va **rigenerato** per `E_JOB_RUN_SALTATA_NON_CHIUDIBILE`.
* `MaintenanceRepository.corsa_riuscita_dal` **non cambia**: legge `AND ok`, e una skip ha
  `ok` NULL (D2). Il test sul DB vero che costruisce la skip (§6) resta utile.
* I lettori che **mostrano** le corse (`list_job_runs`, `job_liveness`, `list_job_summary`,
  `ProcessiRepository`): una skip ora ha `ok` NULL, come una corsa **aperta**. Per non
  mostrarla «in corso» si legge `saltata` (o `ended_at`). Le skip scritte prima del
  2026-10-10 restano `ok = true`, `saltata = false` (D4).
* `JobRunHandle`: invariato. Su `acquired = false` non chiama `fn_job_run_end`, e dal `-23`
  il DB lo rifiuterebbe comunque.

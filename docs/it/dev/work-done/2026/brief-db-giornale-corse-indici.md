# Brief DB — Il giornale delle corse senza indici di lettura

## ⏭️ Chi riparte — aggiornato al 2026-11-22

**Riparte: nessuno.** Brief **chiuso** il 2026-11-22 e archiviato in `work-done/2026/`. La domanda
sui lettori per solo `jobname` (§11.3) l'ha decisa Tid la sera stessa, strada (a), e il giro BE
l'ha chiusa (§11.5): nessun residuo resta aperto.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione BE | Il caso, le chiavi di lettura del backend | §1-§2 | — |
| 2 | ✅ team DB | La verifica critica della richiesta | §6 | 1 |
| 3 | ✅ team DB | Giro 1: quattro indici, due viste riscritte, la prova, la doc `manual/` | §6.2-§6.4, §6.7 | 2 |
| 4 | ✅ Tid | Applicare `20261122-20` … `-22`; lanciare `test-job-run-log-per-chiave-v1` e i pgTAP del §6.7; rigenerare la doc auto-generata | §6.7 | 3 |
| 5 | ✅ sessione BE | L7 e le altre due sedi per chiave (`cte_corse` riscritta); `run_totali` ritirato; L4 per processo; `api_tracciamento.md`; il censimento della ritenzione (§7.4). Tutto il 2026-11-22 (§6.8) | §6.6, §6.8, §7.4 | 4 |
| 5-bis | ✅ team DB | La risposta alle richieste del §6.8 e del §7.4: il processo obbligatorio, l'indice delle corsie, l'insieme tenuto dalla potatura, `potatura_esclusione` | §8 | 5 |
| 5-ter | ✅ Tid | D-R2, D-R3, D-R4 (le righe storiche si **cancellano**); il via al giro 2a | §8.6 | 5-bis |
| 6 | ✅ team DB | Giro 2a scritto e provato: il processo obbligatorio, l'indice delle corsie, la vista dei superuser senza il ramo storico, i pgTAP e la doc | §8.7 | 5-ter |
| 6-bis | ✅ Tid | Il `DELETE` a mano su dbdev; applicare `20261122-23` … `-25`; i pgTAP del §8.7 verdi (2026-11-22) | §8.7 | 6 |
| 6-ter | ✅ Tid | La doc auto-generata di `maintenance` rigenerata dopo il 2a | §8.7 | 6-bis |
| 6-quater | ✅ sessione BE | Le richieste del §8.7 (2026-11-22, §9.1): il ramo storico di `list_job_summary`, il censimento del `23514`, il NULL di `processo_codice` nei lettori | §8.7 | 6-bis |
| 7 | ✅ team DB | Giro 2b scritto e provato: `potatura_esclusione`, la funzione di potatura, il job, il processo nel seed, il pgTAP, la doc | §8.8 | 6-bis, il via di Tid (2026-11-22) |
| 7-bis | ✅ Tid | I due ritocchi del §8.8 confermati; `20261122-29` … `-32` applicati su scratch e dbdev; la fase post del provisioning sullo scratch; i pgTAP verdi (2026-11-22) | §8.8 | 7 |
| 7-ter | ✅ Tid | La doc auto-generata di `dbops` e `maintenance` rigenerata. L'`EXECUTE` di `zeroerp_job` sulla procedura dato su dbdev con un `GRANT` a mano (2026-11-22, catalogo: `zeroerp_job=X/zeroerp_owner`). La fase post non l'aveva dato: con ogni probabilità era girata su un altro database (su dbdev è `zeroerp`) | §8.8 | 7-bis |
| 8 | ✅ sessione BE | Le doc che promettono tutta la storia; con il 6-quater, in un solo `/arrivi-db` (2026-11-22, §9.1) | §7.4, §8.7, §8.8 | 7-bis |
| 9 | ✅ team DB | Giro 3 scritto e provato: la FK `ON DELETE SET NULL` di `coda_lavori.job_run_id`, l'azzeramento del pregresso, la riga della policy degli indici, il pgTAP, la doc (2026-11-22) | §9.2, §10 | 8, la decisione di Tid (2026-11-22) |
| 9-bis | ✅ sessione BE | `api_gestione_code.md` dice che `job_run_id` NULL vuol dire anche «corsa non più nel giornale», con la garanzia ⏳ in attesa del 9. Fatta subito: BE e FE trattano già il NULL, niente aspetta il DB (2026-11-22) | §9.2 | — |
| 9-ter | Tid | ✅ `20261122-33` e il mirror di `fk_index_policy.csv` applicati, `dbops/test-coda-lavori-job-run-id-segue-il-giornale-v1` verde; la doc auto-generata di `dbops` rigenerata, con la FK e l'indice (2026-11-22) | §10.4 | 9 |
| 9-quater | ✅ sessione BE | Tolto il ⏳ della garanzia in `api_gestione_code.md` §4; censiti i lettori di `job_run_id`; la domanda sui lettori per solo `jobname` portata nel registro dei residui (2026-11-22) | §11 | 9-ter |
| 10 | ✅ sessione BE | Brief archiviato in `work-done/2026/`, i rimandi ricollegati (2026-11-22) | §11.4 | 9-quater |
| 10-bis | ✅ sessione BE | Strada (a) di Tid: i tre lettori per solo `jobname` passano alla corsia `(processo_codice, jobname)` (2026-11-22) | §11.5 | la decisione di Tid |
| 10-ter | ✅ revisione BE (`/verifica`) | Il gemello dell'`ORDER BY` sul testo in `list_audit_logs`, il presidio di `_liveness_worker` per processo, il piano provato sul DB vero (2026-11-22) | §11.6 | 10-bis |

**Decisioni di Tid:** ✅ 2026-11-22: le due viste DB che leggono tutto il giornale si riscrivono **in
questo giro** (§6.3). ✅ 2026-11-22: la ritenzione è un debito, e il giornale tiene **12 mesi** (§6.5, §7).
✅ 2026-11-22: D-R1 strada **(a)**, la potatura non tocca mai l'ultima corsa di ogni job e di ogni
processo (§7.2). ✅ 2026-11-22: le corse della fatturazione non si potano; i conteggi non usati si
ritirano (§7.4). ✅ 2026-11-22: D-R2 sì, D-R3 sì, D-R4 le righe storiche si cancellano a mano,
via al giro 2a (§8.6). ✅ 2026-11-22: via al giro 2b. ✅ 2026-11-22: confermati i due ritocchi
del §8.8, la chiave per coppia `(processo, jobname)` e l'ultima fallita e di pgAgent fra le righe
tenute. ✅ 2026-11-22: un `job_run_id` che non porta a nessuna corsa **non si mostra**, e lo
toglie il DB alla fonte, non il BE in lettura (§9.2, strada A). ✅ 2026-11-22: lo strumento è una
**FK `ON DELETE SET NULL`**, non un `UPDATE` nella potatura, e l'azzeramento riscrive `data_update` e
`user_update` come ogni modifica; via al giro 3 (§10). Nessuna decisione aperta.
**Committato** (2026-11-22, `dev/db-tid`): il giro 1 (tre changeSet, un pgTAP, la doc di `maintenance`,
manuale e auto-generata) e questo brief. **Committato** (2026-11-22) anche il §8, questa testata e il giro 2a, applicato
(tre changeSet, quattro pgTAP toccati, la doc `manual/` e cinque guide o pagine, §8.7) e il giro
2b, applicato (quattro changeSet, il CSV dei processi, un pgTAP, due pagine `manual/` nuove e
sei toccate, una guida, §8.8). **Committato** (2026-11-22) anche il giro 3, applicato (un changeSet,
una riga del CSV della policy degli indici, un pgTAP, tre pagine `manual/`, la doc auto-generata di
`coda_lavori` e una guida, §10) e questa testata.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-22. **A chi:** team DB.
> **Origine:** revisione della doc API di `maintenance` ([api_tracciamento.md](../../../backend/core/manual/api_tracciamento.md)),
> che affermava «gli indici DB esistenti coprono i pattern di accesso». Per `dbops.audit_log` è vero, per
> `maintenance.job_run_log` no. Tid, 2026-11-22: brief separato.
> **Brief vicini verificati:** nessun brief aperto in `work-in-progress/` tocca `job_run_log`.

## 1. Il caso

`maintenance.job_run_log` ha **un solo indice**, la chiave primaria `job_run_log_pkey (id)` (doc DB
[job_run_log](/dbzero/maintenance/tabelle/job_run_log), 2026-11-22).

Sul modello:

* è un **giornale append-only senza ritenzione**: una riga per corsa o per passo, di ogni lavoro
  automatico, e nella doc DB nessuno la cancella. Cresce per costruzione;
* chi lo legge lo legge **per chiave** (corsia, processo) e **per recenza** (l'ultima corsa, le corse da
  una data): nessuna lettura del backend vuole la tabella intera.

Senza indici, ogni lettura per chiave è una scansione dell'intero giornale, e il costo cresce con la storia,
non con la domanda. Alcune di queste letture girano **a ogni sveglia** (`e_dovuto`, l'`ExecCondition` dei
timer) e **a ogni lettura dello stato dei worker** (badge code in topbar).

⚠️ C'è anche la FK `fk_job_run_log_processi (processo_codice)` senza indice di supporto, in un progetto che
ha la sua policy degli indici FK (`dbops.apply_fk_index_policy`). Se è un'esclusione voluta va bene, ma
dalla doc non si capisce: lo verifica il team DB.

## 2. Le chiavi di lettura del backend

Tutte da `apps/core/db/maintenance_repository.py` e `apps/core/db/processi_repository.py`. Sono le
**forme** delle query, non dei carichi.

| # | Chi | Filtro | Ordine |
| --- | --- | --- | --- |
| L1 | `list_job_runs` (`GET core/tracciamento/job-runs/`) | facoltativi: `jobname =`, intervallo su `started_at` | `started_at DESC, id DESC`, `LIMIT/OFFSET` |
| L2 | `cte_corse` → `job_liveness(jobnames=…)` (badge code, digest presidi) | `jobname = ANY(…)` | `DISTINCT ON (jobname) … ORDER BY jobname, started_at DESC, id DESC`, due volte: tutte le righe, e le sole `ended_at IS NOT NULL AND NOT saltata` |
| L3 | `cte_corse` → `job_liveness(processo_codice=…)` | `processo_codice =` | come L2 (per jobname, dentro il processo) |
| L4 | `cte_corse` + `GROUP BY jobname` → `list_job_summary` (`job-summary`, pannello esiti fatturazione) | nessuno, oppure `jobname LIKE '<prefisso>%'` e un'espressione sul mese di `started_at` / `meta ->> chiave` | come L2 |
| L5 | `corsa_riuscita_dal` / `corsa_chiusa_dal` (`e_dovuto`, a ogni sveglia) | `jobname = AND started_at >= AND ok` / `ok IS NOT NULL` | — (`EXISTS`) |
| L6 | `list_run_processo` (`GET amm-software/processi/{codice}/run/`) | `processo_codice =` | `started_at DESC, id DESC`, `LIMIT/OFFSET` |
| L7 | `list_processi` (`GET amm-software/processi/`): dal 2026-11-22 `cte_corse(chiave="processo_codice")` più un `count(*) … GROUP BY processo_codice`, non più una `LATERAL` per processo | `processo_codice IS NOT NULL`, **nessun** filtro di processo: il giornale intero, una riga per processo | `DISTINCT ON (processo_codice) … ORDER BY processo_codice, started_at DESC, id DESC`, due volte come L2 |

In sintesi, due chiavi: **`(jobname, started_at DESC, id DESC)`** (L1 con jobname, L2, L4, L5) e
**`(processo_codice, started_at DESC, id DESC)`** (L3, L6, L7), più la recenza pura per L1 senza filtri.
Lato DB leggono lo stesso giornale anche `maintenance.vw_job_run_da_guardare`,
`maintenance.vw_job_run_da_superuser` e `dbops.vw_processi_programmazione`: il team DB li conosce meglio
di questo brief e li mette nel conto.

⚠️ L4 con prefisso usa `jobname LIKE 'x%'`: un btree serve un `LIKE` per prefisso solo in collation `C` o
con `text_pattern_ops`. Lo segnalo, non lo decido.

## 3. La richiesta

1. Dare a `maintenance.job_run_log` gli indici che servono le chiavi del §2, nella forma che il team DB
   ritiene giusta (quali colonne, se parziali su `NOT saltata`, se `INCLUDE`).
2. Verificare con `EXPLAIN` su L2, L3 e L5 che il piano usi gli indici.
   ⚠️ Riformulato nel §6.4: un `EXPLAIN` sulle righe di oggi non prova che la forma sia servita.
3. Chiarire la FK `fk_job_run_log_processi` rispetto alla policy degli indici FK (§1): coperta dal nuovo
   indice su `processo_codice`, oppure esclusa con un motivo scritto.

## 4. Doc

* `docs/it/dbzero/maintenance/tabelle/job_run_log.md` si rigenera; il manuale
  `maintenance/manual/job_run_log.md` dice quali letture servono gli indici.
* [api_tracciamento.md](../../../backend/core/manual/api_tracciamento.md) § Note oggi dice «`job_run_log` ha
  **solo** la chiave primaria»: a indici applicati quella riga va corretta. La corregge la sessione BE al
  ritorno (`/arrivi-db`), così il team DB non tocca `backend/` né la doc BE.

## 5. Ricadute BE/FE

⚠️ Superato dal §6.6: la verifica DB chiede al BE tre ritocchi di lettura. Nessun contratto cambia.

Nessuna: nessuna query cambia, nessun contratto cambia.

## 6. Verifica DB — 2026-11-22

Fatta sul catalogo dello scratch `zeroerp_ruoli` (PG 19), con le linee guida SQL §8 e §13.1.

### 6.1 Che cosa è confermato, che cosa si corregge

* Confermato: `job_run_log` ha la sola chiave primaria e non ha RLS. Lo scrivono quattro verbi
  (`maintenance.fn_run_and_log`, `script.fn_job_run_start`, `script.fn_job_run_end`,
  `maintenance.fn_job_run_log_failure`), sempre per `id`, e nessuno cancella: è append-only per costruzione.
* **§3.3, la FK: non è un'esclusione, è fuori ambito.** La policy degli indici FK governa solo gli schemi di
  `dbops.automation_scope` (§8.7 delle linee guida: il perimetro è per schema), e `maintenance` non c'è.
  Quindi `fk_job_run_log_processi` non compare in `dbops.vw_fk_senza_indice` e non ha bisogno di una riga in
  `fk_index_policy.csv`. La copre per prefisso l'indice su `processo_codice` del §6.2. Lo si scrive nel
  changeSet della tabella, perché la policy non lo governa.

### 6.2 I quattro indici

⚠️ Erano tre nella verifica. Il quarto, parziale, è nato scrivendo la vista dei superuser (§6.3): la
sua chiave `COALESCE(processo_codice, jobname)`, per le righe senza processo, non la serviva nessuno
dei tre.

| Indice | Chi lo usa |
| --- | --- |
| `ix_job_run_log_jobname_started_at (jobname, started_at DESC, id DESC)` | L1 con jobname, L2, L4, L5; in `vw_job_run_da_guardare` la `LATERAL` «ultimo rosso» e i fallimenti per job degli ultimi 7 giorni |
| `ix_job_run_log_processo_codice_started_at (processo_codice, started_at DESC, id DESC)` | L3, L6, L7; la FK; `dbops.vw_processi_programmazione` |
| `ix_job_run_log_started_at (started_at DESC, id DESC)` | L1 senza filtri; la finestra di 7 giorni di `vw_job_run_da_guardare` (CTE `tratti`) |
| `ix_job_run_log_jobname_senza_processo (jobname, started_at DESC, id DESC) WHERE processo_codice IS NULL` | il ramo «senza processo» di `vw_job_run_da_superuser`. Tiene solo righe storiche: `chk_job_run_log_processo_dichiarato` (`NOT VALID`) pretende il processo da ogni corsa nuova |

* **Non parziali:** L2 («tutte le righe») e `vw_job_run_da_superuser` leggono anche le corse saltate. Un
  parziale su `NOT saltata` vorrebbe un indice gemello.
* **Senza `INCLUDE`:** i lettori proiettano molte colonne, quindi non nasce un accesso «solo indice» che valga
  la larghezza in più.
* **Il `LIKE 'x%'` di L4 resta non servito, apposta.** La collation del database è `it_IT.UTF-8`: un btree
  normale non serve un `LIKE` per prefisso, e un indice `text_pattern_ops` non serve l'`ORDER BY jobname`.
  L4 aggrega comunque tutto il giornale (§6.6).

### 6.3 Le due viste DB che leggono tutto il giornale (Tid, 2026-11-22: in questo giro)

Un indice **non** sistema un `DISTINCT ON` senza filtro di chiave. Rende ordinata la scansione, ma il
costo resta proporzionale a tutta la storia. La forma che resta limitata è una `LATERAL … ORDER BY
started_at DESC, id DESC LIMIT 1` per chiave, partendo dall'elenco delle chiavi: una ricerca nell'indice per
chiave, a prescindere dalla storia.

| Vista | Oggi | Nel giro |
| --- | --- | --- |
| `maintenance.vw_job_run_da_guardare`, CTE `ultima` | `DISTINCT ON (jobname)` su tutto il giornale | l'ultima corsa per jobname con la `LATERAL` sull'indice per jobname. ⚠️ L'elenco dei jobname non ha una tabella sua: si legge con una scansione «salta al valore successivo» (CTE ricorsiva sull'indice), oppure da `dbops.processi` più i jobname senza processo. La scelta va fatta scrivendo, sul modello: le righe vecchie possono avere `processo_codice` NULL (`chk_job_run_log_processo_dichiarato` è `NOT VALID`) |
| `maintenance.vw_job_run_da_superuser` | `DISTINCT ON (COALESCE(processo_codice, jobname))`, che nessun indice serve | stessa forma, su chiavi che gli indici del §6.2 servono |

Da guardare nello stesso giro: `dbops.vw_processi_programmazione` ha già la `LATERAL` per processo, ma
calcola `max(started_at)` su **tutte** le corse del processo, con un `OR` fra `processo_codice` e `jobname`.
Il giro valuta se riportarla a un `ORDER BY … LIMIT 1` per ciascuno dei due rami.

**Fatto (2026-11-22):**

* `20261122-21`, `vw_job_run_da_guardare`: l'elenco dei jobname con una CTE ricorsiva che salta da un
  valore al successivo sull'indice per jobname (`min(jobname) WHERE jobname > precedente`), poi per
  ciascuno la `LATERAL … LIMIT 1` col filtro e il join verso `dbops.processi` di prima. È una scelta
  del modello, non delle righe di oggi: l'elenco dei jobname non ha una tabella sua, e partire da
  `dbops.processi` avrebbe perso i jobname senza processo.
* `20261122-22`, `vw_job_run_da_superuser`: la chiave `COALESCE(processo_codice, jobname)` divisa nei
  suoi due rami, ognuno col suo indice e la sua discesa ricorsiva. Per ogni chiave vince la più
  recente fra «l'ultima col processo K» e «l'ultima senza processo col jobname K», con
  `ruolo_sessione IS NOT NULL` dentro ciascun ramo.
* ⚠️ **`vw_processi_programmazione` resta com'è in questo giro.** Legge già per processo, quindi non
  percorre tutto il giornale; ora l'indice serve anche il suo `WHERE`. Quello che resta, `max()` su
  tutte le corse di un processo e `ultima_corsa_pgagent` (che per un processo COMMAND percorre tutte
  le sue corse senza trovarne), cresce con la storia **del processo**: il limite glielo dà la
  ritenzione (§7). Il suo piano si rilegge nel giro 2.

Prima di cambiare le viste si fa il banco del §13.1: stesso risultato nei due versi (`EXCEPT ALL`), più
una mutazione che il confronto deve vedere.

### 6.4 La prova: si prova la forma, non le righe di oggi

Il §3.2 chiedeva un `EXPLAIN` che mostrasse l'uso degli indici. Su un giornale piccolo il planner sceglie,
giustamente, la scansione sequenziale: quell'`EXPLAIN` è una fotografia, non una prova. Si prova che la
forma è servita: `EXPLAIN` come app (§13.1) con `enable_seqscan = off`, su L2, L3, L5 e sulle due viste
riscritte. Il piano deve poter percorrere l'indice per chiave senza un `Sort` su tutto il giornale.

**Fatto (2026-11-22, `prova_changeset.py`, transazione in ROLLBACK).** Prova fatta da owner: il
giornale non ha RLS, quindi il piano dell'app non ha policy che lo cambino (§13.1).

* Con `enable_seqscan = off`, L1, L2, L3, L5, L6 e le due viste usano gli indici: 7 su 7 (0 su 7 senza
  l'estratto).
* Nelle due viste: discesa ricorsiva con `Index Only Scan … Limit` per ogni chiave, `Limit` sulla
  `LATERAL`, `Merge Append` fra i due rami dei superuser.
* ⚠️ Sullo scratch il planner sceglie in qualche punto l'indice per recenza e filtra sul jobname:
  è una scelta di costo, fatta con le statistiche di oggi. Togliendo quell'indice nella transazione,
  la forma è servita dall'indice per chiave (`Index Cond: jobname = …`, `Limit`, nessun `Sort`):
  la forma è giusta, la scelta la farà il planner sui volumi veri.
* Banco di equivalenza fra vecchio e nuovo corpo (`EXCEPT ALL` nei due versi), con una fixture
  costruita: fallita seguita da saltata, verdetto completo con due tratti rossi e una corsa in corso,
  appesa, righe storiche senza processo di un superuser. Con due mutazioni, la saltata non scartata
  e il ramo storico tolto, che il confronto vede: 8 su 8.

### 6.5 ✅ Decisa da Tid (2026-11-22): la ritenzione è un debito, 12 mesi → §7

Il giornale non ha ritenzione, quindi cresce per sempre, e con lui gli indici. Gli indici rendono veloci
le ricerche per chiave, ma non fermano la crescita. Non c'è nessun residuo aperto su questo. Tid decide se è:
(a) una scelta (lo storico delle corse si tiene tutto), da scrivere nel manuale della tabella; oppure
(b) un debito: una potatura delle corse più vecchie di un periodo, da aprire come residuo.

### 6.6 Richieste al BE (al ritorno, `/arrivi-db`)

* **L7, `list_processi`:** con l'indice per `processo_codice`, la forma che resta limitata è la `LATERAL`
  per processo da `dbops.processi`, quella tolta il 2026-11-22. Il `DISTINCT ON` su tutto il giornale cresce
  con la storia anche con l'indice. Il BE valuta se tornare alla `LATERAL` (in `cte_corse`, che è comune: la
  stessa domanda vale per L4).
* **Il `count(*) … GROUP BY processo_codice` di L7** conta tutte le corse di sempre, quindi cresce con la
  storia per definizione, con o senza indice. Se serve davvero, il suo costo dipende dalla decisione del §6.5.
* **L4, `LIKE '<prefisso>%'`:** non servito dagli indici (§6.2). Se il BE vuole il filtro servito, lo
  riscrive come intervallo (`jobname >= 'x' AND jobname < <successore di 'x'>`).
* Al ritorno, la correzione di `api_tracciamento.md` del §4.
* Il censimento del §7.3, **prima** che il giro 2 cominci.

### 6.7 Il giro 1: che cosa c'è ✅ (applicato, verde, committato: 2026-11-22)

| File | Che cosa |
| --- | --- |
| `00_schema/maintenance/20261122-20-create-indici-job-run-log-mctit.yaml` | i quattro indici, con il `COMMENT` di ciascuno |
| `20_code/maintenance/20261122-21-update-vw-job-run-da-guardare-per-chiave-mctit.yaml` | la vista dei job da guardare, per chiave |
| `20_code/maintenance/20261122-22-update-vw-job-run-da-superuser-per-chiave-mctit.yaml` | la vista dei superuser, per chiave |
| `db/pgtap/maintenance/test-job-run-log-per-chiave-v1.sql` | gli indici e le due viste (plan 8) |
| `maintenance/manual/job_run_log.md`, `vw_job_run_da_guardare.md`, `vw_job_run_da_superuser.md` | «Come si legge», test, note di migrazione |

Provati in ROLLBACK sullo scratch, insieme all'estratto: il test nuovo 8 su 8 (4 rossi senza
l'estratto, gli indici che mancano); invariati `test-vw-job-run-da-guardare` (6),
`-verdetto-completo-v1` (17), `-causa-v1` (15), `-corse-distinte-v1` (2),
`test-job-run-ruolo-sessione-v1` (10), `test-job-run-saltata-v1` (11),
`test-app-postura-job-run-log-v1` (10 ok, 1 rosso da owner che c'era già senza l'estratto).

✅ Tid, 2026-11-22: applicato sullo scratch, pgTAP verde, doc auto-generata di `maintenance`
rigenerata (tabella `job_run_log` con i quattro indici, le due viste col corpo nuovo).

### 6.8 Il lato BE ✅ (2026-11-22, `dev/backend-tid`)

Risposta al §6.6. Decisione di Tid: `cte_corse` si rifà **per tutti e tre** i chiamanti, non solo per L7.

| Sede | Prima | Ora |
| --- | --- | --- |
| `maintenance_repository.cte_corse` | `DISTINCT ON (<chiave>)` sul giornale filtrato | il chiamante dichiara le **chiavi** (una relazione dello stesso WITH), e per ciascuna `CROSS JOIN LATERAL … ORDER BY started_at DESC, id DESC LIMIT 1`, `recente` e `conclusa`. Restituisce `(sql, params)` con i valori già ripetuti per le due CTE |
| L7 `ProcessiRepository.list_processi` | `cte_corse` sul giornale intero | chiavi da `dbops.processi`; `run_totali` ritirato (§7.4) |
| `job_liveness` per `jobnames` | `DISTINCT ON` filtrato `jobname = ANY` | chiavi `unnest` dei nomi chiesti |
| `job_liveness` per `processo_codice` | `DISTINCT ON` filtrato sul processo | le corsie del processo con una discesa ricorsiva «salta al jobname successivo» (la forma di `vw_job_run_da_guardare`), poi la `LATERAL` col filtro sul processo |
| L4 `list_job_summary` | `jobname_prefix`, un `jobname LIKE '<prefisso>%'` | `processo_codice`: `processo_codice = %s OR (processo_codice IS NULL AND split_part(jobname, ':', 1) = %s)`; chiavi delle corse: i jobname del riepilogo |

⚠️ **L4 non è diventato un intervallo, apposta.** Sotto `it_IT.UTF-8` `_` e `:` non pesano al primo
livello, quindi `jobname >= 'x' AND jobname < <successore di 'x'>` non è il prefisso: può prendere
nomi che non lo hanno. E nel `LIKE` di prima `_` era un jolly. La chiave vera delle corsie di
fatturazione è il processo, e il suo indice la serve. Il nome resta solo per le righe storiche
senza processo, con un confronto esatto.

**Prova** (`EXPLAIN` come app su dbdev, `enable_seqscan = off`): `job_liveness` nei due modi e
`list_processi` scendono per chiave (`Index Cond: jobname = k.jobname` /
`processo_codice = …`, `Limit`), senza `Sort` sul giornale. Test: 2393 verdi, compresi quelli sul
DB vero (`ZEROERP_TEST_DB_E2E=1`).

**Due richieste al team DB nate qui:**

1. **Le righe storiche senza processo.** Nel riepilogo della fatturazione il ramo
   `processo_codice IS NULL` si legge per intero: il predicato sul nome non è servito da
   `ix_job_run_log_jobname_senza_processo`, che è per `jobname` esatto. Su dbdev sono circa
   101 000 righe, ferme per costruzione (`chk_job_run_log_processo_dichiarato` è `NOT VALID`), quindi
   il costo non cresce. Ma la soluzione sul modello è attribuire il processo alle righe storiche
   (si riconosce dal nome) e validare il `CHECK`. Allora il ramo del BE si toglie, e con lui
   l'indice parziale e il ramo «senza processo» delle viste del giro 1. Il team DB decide se e
   quando. Il BE toglie il ramo dopo.
2. **Le corsie di un processo**, facoltativa. La discesa ricorsiva di `job_liveness` per
   `processo_codice` fa ogni passo su `ix_job_run_log_processo_codice_started_at`, cioè fra tutte le
   corse del processo: cresce con la storia **del processo**, che la ritenzione limita. Un indice
   `(processo_codice, jobname, started_at DESC, id DESC)` la renderebbe una ricerca per corsia. Lo
   segnalo, non lo decido.

Doc BE corrette: `api_tracciamento.md` (le Note sugli indici e sulla lettura per chiave, il filtro
`processo_codice`, la data spostata sopra lo scopo, per cui l'indice della doc BE riprende la
descrizione), `api_amm_software.md` (`run_totali` tolto), il catalogo dei building block
(`cte_corse`, `job_liveness`).

## 7. Giro 2 — La ritenzione: il giornale tiene 12 mesi

Tid, 2026-11-22: il giornale senza ritenzione è un debito; si tengono 12 mesi. **Non è cominciato.**

### 7.1 Il disegno

Una potatura notturna cancella le corse con `started_at` più vecchio di 12 mesi. È un processo come
gli altri: una riga in `dbops.processi` (dal seed), una procedura in `maintenance` eseguita da
`fn_run_and_log`, il job pgAgent, la riga nel giornale della sua corsa. È l'unica porta che cancella:
l'app resta senza `DELETE`.

### 7.2 ✅ D-R1, decisa da Tid (2026-11-22): oltre i 12 mesi resta l'ultima corsa

**Decisione: strada (a).** La potatura cancella le corse più vecchie di 12 mesi **tranne**, per ogni
`jobname` e per ogni `processo_codice`:

* l'ultima corsa in assoluto;
* l'ultima corsa vera (`NOT saltata`);
* l'ultima corsa col ruolo registrato (`ruolo_sessione IS NOT NULL`).

Spesso sono la stessa riga: oltre i 12 mesi restano al più tre righe per chiave. I tre presidi qui
sotto non cambiano. La strada (b), la potatura per sola data con i tre lettori riscritti per
distinguere «mai partito» da «partito più di un anno fa», è scartata.

⚠️ L'ordine di «ultima» è quello dei lettori, `started_at DESC, id DESC`: la potatura usa la stessa
forma per chiave del giro 1 (§6.3), servita dagli indici del §6.2. La chiave di
`vw_job_run_da_superuser` è `COALESCE(processo_codice, jobname)`: le righe storiche senza processo si
proteggono per `jobname`.

Il ragionamento che ha portato alla decisione:

Alcuni lettori ragionano su «l'ultima corsa», e una potatura per sola data gliela toglie:

* `dbops.vw_processi_programmazione` dice **«mai partito»** di un processo COMMAND senza corse nel
  giornale. Un processo che gira una volta all'anno (o spento da più di un anno) diventerebbe «mai
  partito», e il presidio si accenderebbe per un motivo falso;
* `vw_job_run_da_guardare` guarda l'ultima corsa **vera** di ogni job: potata quella, il job sparisce
  dal presidio anche se la sua ultima corsa era fallita;
* `vw_job_run_da_superuser` guarda l'ultima corsa col ruolo registrato.

La proposta, poi decisa: la potatura **non tocca mai l'ultima corsa** di ogni job e di ogni processo, né l'ultima
corsa vera, né l'ultima col ruolo registrato. Oltre i 12 mesi resta così, per ciascuno, solo ciò che
i presidi leggono. L'alternativa, la potatura per sola data, vuole che i tre lettori sappiano
distinguere «mai partito» da «partito più di un anno fa».

### 7.3 ⛔ Garanzia ritirata: «il giornale ha tutta la storia»

Oggi nessuno cancella dal giornale, e il manuale lo dice («un giornale non si cancella»). Chi legge
può contare su una storia completa.

| Lettore DB | Ne dipende? |
| --- | --- |
| `dbops.vw_processi_programmazione` | sì, per «mai partito»: coperto da D-R1 (a) |
| `maintenance.vw_job_run_da_guardare` | sì per l'ultima corsa vera: coperto da D-R1 (a); no per le finestre di 7 giorni |
| `maintenance.vw_job_run_da_superuser` | sì per l'ultima corsa col ruolo: coperto da D-R1 (a) |
| `maintenance.fn_run_and_log`, `script.fn_job_run_start`, `script.fn_job_run_end`, `maintenance.fn_job_run_log_failure` | no: scrivono, e leggono solo la propria riga per `id` |
| `maintenance.proc_sync_storico_set_storicizza` | no: nomina il giornale solo in un commento |

**Richiesta al BE, prima che il giro 2 cominci:** censisci i lettori di `maintenance.job_run_log` che
contano su «il giornale ha tutta la storia». Quelli già noti: il `count(*)` delle corse di L7 (che
diventerebbe «le corse degli ultimi 12 mesi», oltre a ciò che D-R1 tiene), L1 e L6 (le corse più
vecchie spariscono dagli elenchi), `api_tracciamento.md`. L'elenco non è chiuso: va cercato.

### 7.4 Il censimento del BE — 2026-11-22

Sola lettura su `backend/apps` e `frontend/src` (sessione BE, `dev/backend-tid`). I test sono contati a parte.

**Dipendono da «tutta la storia»:**

| Lettore | Forma | Chi lo vede | Dopo la potatura |
| --- | --- | --- | --- |
| `pipeline_service.esiti_fatturazione` → `MaintenanceRepository.list_job_summary(jobname_prefix='run_fatturazione_batch', meta_month_equals=('competenza', mese))` | conteggi e corse per **mese di competenza** (`COALESCE(meta->>'competenza', mese di started_at)`) | **FE**: `FatturazioneEsitiPanel` in `LottiListView`, che naviga per anno e può aprire un mese di anni prima | il filtro è per mese, non per chiave: le righe che D-R1 tiene non lo coprono. Un mese oltre la soglia diventa «Nessun giro di fatturazione», un mese a cavallo conta meno del vero. → **Decisione di Tid qui sotto** |
| `list_job_summary` senza filtri, `GET /api/v1/core/tracciamento/job-summary/` | `total_runs`, `ok_count`, `fail_count`, `saltate_count` per jobname su tutte le righe | solo API, nessun FE | diventano «gli ultimi 12 mesi, più le righe tenute» |
| `list_job_runs` (L1), `GET /api/v1/core/tracciamento/job-runs/` | lista paginata col totale, `date_from` senza limite inferiore | solo API, nessun FE | un `date_from` oltre la soglia trova solo le righe tenute |
| `ProcessiRepository.list_processi` (L7), `run_totali` | `count(*) FILTER (NOT saltata)` per processo, su tutta la storia | solo API e doc: non è una colonna della lista 66, il FE non lo legge | → **ritirato dal BE** (decisione di Tid qui sotto) |
| `ProcessiRepository.list_run_processo` (L6), `GET /api/v1/amm-software/processi/{codice}/run/` | lista paginata col totale, senza limite di data | FE: `ProcessoDrawer` chiede le ultime 50 e non pagina | `count` e `offset` non arrivano più a tutta la storia; a video cambia solo per un processo con meno di 50 corse in 12 mesi |

**Coperti da D-R1 (salvo la riserva qui sotto):** `job_liveness` (lo stato dei worker delle code,
`ApiCodeConteggi` → `CodaWorkerStato`, «mai eseguito»; il battito di `presidi_digest`, «non ha mai
girato»), le corse di `list_processi` (`ultimo_run` «mai girato», `ultima_conclusa`, `ultimo_ok`), e i
presidi (`presidi_repository.stato_presidi`, il digest), che leggono le viste DB senza finestre loro.

**Non dipendono:** `corsa_riuscita_dal` e `corsa_chiusa_dal`, le idempotenze di `e_dovuto`: guardano
dall'inizio del periodo corrente, e i periodi di `deploy/sveglie.json` sono giorno, settimana, mese.
Scrivono soltanto: `job_run.registered_job`, i comandi di fatturazione, stampa, code, smoke, email.

⚠️ *Superato dal §10 (giro 3, 2026-11-22): `job_run_id` ha la FK `ON DELETE SET NULL`, e non resta più orfano.*
**Un riferimento che resta orfano:** `dbops.coda_lavori.job_run_id` non ha FK verso il giornale; il BE
lo espone e `JobDettaglioDrawer` lo mostra. Dopo la potatura punta a una riga che non c'è: niente si
rompe, si perde la traccia. Lo si scrive nel manuale della coda.

**Doc BE che promettono tutta la storia** (le corregge il BE dopo il giro 2):
`api_tracciamento.md` (lo scopo, `job-runs` senza limite di data, i conteggi di `job-summary`),
`api_amm_software.md` (`run_totali`, §6.9 la paginazione delle corse del processo),
`api_fatturazione.md` («assente = totali da sempre»).

#### ⛔ Riserva su D-R1: «l'ultima corsa vera» può essere una riga aperta

D-R1 tiene l'ultima corsa `NOT saltata`. Ma il BE legge «l'ultima **conclusa**»: la CTE `conclusa` di
`maintenance_repository.cte_corse` vuole `ended_at IS NOT NULL AND NOT saltata`. L'ultima corsa non
saltata può essere aperta: in esecuzione, o rimasta appesa da un processo morto. Se l'ultima
conclusa ha più di 12 mesi, la potatura la cancella, e `ultima_conclusa` diventa `null`: «Mai
concluso» in lista, «nessuna corsa conclusa» nel digest, la cella «Esito» vuota.

**Richiesta al team DB:** fra le righe che la potatura tiene per ogni chiave, l'ultima con
`ended_at IS NOT NULL AND NOT saltata`, al posto (o accanto) dell'ultima `NOT saltata`. È la stessa
domanda per i lettori DB: `vw_job_run_da_guardare` scarta la corsa in corso ma non quella appesa.

#### ✅ Decisioni di Tid (2026-11-22) sul censimento

* **Le corse della fatturazione non si potano.** Il pannello esiti deve vedere ogni mese, anche
  oltre la soglia. **Richiesta al team DB:** la potatura esclude le corse dei processi che lo
  dichiarano. Il BE propone che sia una proprietà del processo in `dbops.processi`, e non un elenco di
  jobname nella procedura: un altro processo con lo stesso bisogno la dichiara senza toccare la
  potatura. Oggi la dichiara la fatturazione (`jobname` con prefisso `run_fatturazione_batch`). La
  forma la decide il team DB.
* **I conteggi non usati si ritirano.** `run_totali` di `list_processi` non lo legge nessuno: il BE lo
  ritira (risposta, query `conteggi`, `api_amm_software.md`). I conteggi di `list_job_summary`
  restano: li usa il pannello esiti (`total_runs`, `ok_count`), e con la fatturazione esclusa dalla
  potatura restano veri per lui. Per l'endpoint `job-summary` senza filtri, che nessun FE chiama, la
  doc dirà «gli ultimi 12 mesi».

## 8. La risposta del team DB al §6.8 e al §7.4 — 2026-11-22

Sessione DB (`dev/db-tid`). Prima l'analisi; dopo le decisioni del §8.6, il giro 2a (§8.7).

### 8.1 Le righe storiche senza processo (§6.8, richiesta 1): il processo diventa obbligatorio

⚠️ **Corretto dal §8.6 (D-R4) e dal §8.7.** La proposta qui sotto **attribuiva** il processo alle
righe storiche, e revocava senza dirlo una decisione presa: DB-5 (2026-09-05, `90_end/20260905-16`)
aveva scelto il `CHECK NOT VALID` proprio perché «riempirle sarebbe inventare un attore per corse che
non l'avevano». La regola di attribuzione proposta era anche più larga della derivazione di
`fn_run_and_log`, che vuole il `jobname` uguale al codice. Tid ha scelto di **cancellarle**: non si
inventa niente, e il resto della proposta (il changeSet strutturale, i ritiri) resta.

**Sul modello.** `chk_job_run_log_processo_dichiarato` è `NOT VALID`: vieta la riga senza processo a
ogni corsa nuova, quindi un database costruito da zero (la CI, lo scratch, ogni installazione nuova)
non ne ha. Le righe senza processo sono la storia di una macchina nata prima del `CHECK`. La
ritenzione da sola non le chiude: D-R1 tiene l'ultima corsa per `jobname`, quindi il ramo «senza
processo» resterebbe per sempre in due viste, in un indice e nel BE.

**La regola di attribuzione** è sul nome, ed è quella che il BE usa già nel riepilogo della
fatturazione (§6.8): la radice del `jobname` (`split_part(jobname, ':', 1)`) è il `codice` del
processo, oppure il suo `jobname_pgagent`. Fatto datato (dbdev, 2026-11-22): 14 radici, e ognuna ha
il suo processo in `dbops.processi`.

**La proposta, in due pezzi:**

1. **Il dato si corregge a mano su dbdev**, con un solo `UPDATE` per regola (AGENTS, «bug di dati in
   sviluppo»: un fix per dati sbagliati lascia codice da togliere). Lo SQL lo prepara il team DB.
2. **Il changeSet porta solo la struttura:** `VALIDATE CONSTRAINT`, poi `processo_codice SET NOT
   NULL` (il `CHECK` validato evita a PostgreSQL una seconda scansione) e il `CHECK` ritirato. Su una
   macchina che ha ancora righe senza processo il changeSet si ferma, ed è il comportamento giusto
   (fail-closed).

**Che cosa si ritira nello stesso giro:**

* l'indice `ix_job_run_log_jobname_senza_processo`;
* il ramo «senza processo» di `vw_job_run_da_superuser`, la cui chiave torna `processo_codice`;
* nel BE, dopo il DB: il ramo `processo_codice IS NULL AND split_part(...)` di `list_job_summary`.

`vw_job_run_da_guardare` non cambia: la sua chiave è il `jobname`.

**Garanzia nuova, non ritirata:** «ogni corsa ha il suo processo». Chi legge può smettere di
gestire il NULL. Lo dicono il `COMMENT` della colonna e il manuale.

### 8.2 L'indice per le corsie di un processo (§6.8, richiesta 2): sì

La discesa «salta al jobname successivo» dentro un processo, fatta su
`ix_job_run_log_processo_codice_started_at`, percorre a ogni passo tutte le corse del processo:
`min(jobname) WHERE processo_codice = X AND jobname > precedente` non ha l'ordine di `jobname`
nell'indice. È la forma a dirlo, non i volumi: un processo che corre spesso ha molte corse anche in
12 mesi.

`ix_job_run_log_processo_codice_jobname_started_at (processo_codice, jobname, started_at DESC, id
DESC)` serve i due passi: la discesa (solo indice) e la `LATERAL` per corsia (`processo_codice = X
AND jobname = k ORDER BY started_at DESC, id DESC LIMIT 1`). **Si aggiunge, non sostituisce**:
L6 e `vw_processi_programmazione` ordinano per recenza dentro il processo, attraverso tutte le corsie,
e quell'ordine lo dà solo l'indice `(processo_codice, started_at DESC, id DESC)`.

### 8.3 La riserva su D-R1 (§7.4): l'insieme delle righe tenute, riscritto sui predicati dei lettori

Il BE ha ragione: «l'ultima `NOT saltata`» non è «l'ultima conclusa». C'è anche un terzo lettore, che
la riserva non nomina. La CTE `ultima` di `vw_job_run_da_guardare` vuole l'ultima `NOT saltata`
**escluse** le corse giovani in corso di un processo a verdetto completo. Se quella giovane è la più
recente, la risposta è la corsa prima, che può avere più di 12 mesi ed essere **appesa**: né
«l'ultima `NOT saltata`» né «l'ultima conclusa» la proteggono.

La regola che copre ogni lettore, per ogni `jobname` e ogni `processo_codice`, tiene oltre i 12 mesi:

* l'ultima corsa in assoluto («mai partito», `ultimo_run`);
* l'ultima conclusa vera (`ended_at IS NOT NULL AND NOT saltata`: `ultima_conclusa`, `ultimo_ok`);
* l'ultima col ruolo registrato (`vw_job_run_da_superuser`);
* **ogni corsa aperta** (`ended_at IS NULL`), a qualunque età. Una corsa aperta non è storia chiusa:
  è un fatto pendente, e da appesa è proprio ciò che il presidio mostra. Potarla nasconderebbe
  l'anomalia.

L'«ultima `NOT saltata`» di D-R1 esce dall'elenco perché ci è già dentro: o è aperta, e allora è
tenuta, o è conclusa, e allora è l'ultima conclusa vera. Lo stesso vale per la risposta di
`vw_job_run_da_guardare`: le sole righe più recenti che salta sono corse aperte.

⚠️ Il «scarta la corsa in corso ma non quella appesa» di `vw_job_run_da_guardare` (§7.4) non è un
difetto: l'appesa è uno dei suoi verdetti (colonna `appesa`).

È un ritocco di una decisione di Tid (D-R1, §7.2), quindi **la conferma Tid** (D-R2 qui sotto).

### 8.4 L'esclusione dichiarata dal processo (§7.4)

La forma che segue un modello già in `dbops.processi`, cioè `ci_esclusione` (l'esclusione porta il
suo motivo scritto): **`potatura_esclusione text`**. NULL vuol dire che le corse si potano a 12 mesi.
Un testo vuol dire che non si potano mai, e il testo è il perché. Il valore sta nel CSV del seed dei
processi (`80_data`). Un processo nuovo con lo stesso bisogno lo dichiara lì, senza toccare la
procedura. Un `CHECK` vieta la stringa vuota, come per `ci_esclusione`.

Il pannello esiti legge le corse di `run_fatturazione_batch`. Restano da decidere i due processi
`CODA` della fatturazione, `FATTURAZIONE_GIRO` e `FATTURAZIONE_NUMERA` (D-R3).

### 8.5 Il giro 2, ridisegnato

| Parte | Che cosa |
| --- | --- |
| 2a | il processo obbligatorio (§8.1, dopo l'`UPDATE` a mano su dbdev), l'indice delle corsie (§8.2), `vw_job_run_da_superuser` senza il ramo storico, l'indice parziale ritirato |
| 2b | `potatura_esclusione` in `dbops.processi` e nel CSV (§8.4); la potatura (§7.1) con l'insieme tenuto del §8.3; il processo nel seed; il piano di `vw_processi_programmazione` riletto (§6.3) |
| BE, dopo | il ramo storico di `list_job_summary` ritirato; le doc che promettono tutta la storia (§7.4); il manuale della coda per `job_run_id` orfano |

La 2a viene prima, perché semplifica la 2b: con il processo obbligatorio la potatura protegge per
`jobname` e per `processo_codice`, senza un terzo ramo per le righe storiche.

### 8.6 Decisioni di Tid

✅ Tutte decise da Tid il 2026-11-22.

* ✅ **D-R2, sì:** la potatura tiene l'insieme del §8.3 (l'ultima, l'ultima conclusa vera, l'ultima
  col ruolo, ogni corsa aperta) al posto delle tre righe di D-R1.
* ✅ **D-R3, sì:** anche `FATTURAZIONE_GIRO` e `FATTURAZIONE_NUMERA` dichiarano
  `potatura_esclusione`, insieme a `run_fatturazione_batch`.
* ✅ **D-R4, le righe storiche senza processo si cancellano a mano** su dbdev. Non si attribuiscono:
  è la ragione di DB-5, che resta (§8.1, la correzione in testa).
* ✅ Il via al giro 2a. Il 2b aspetta un via suo.

### 8.7 Il giro 2a ✅ applicato, verde (2026-11-22)

✅ Tid, 2026-11-22: il `DELETE` a mano su dbdev, poi `20261122-23` … `-25` applicati su scratch e
dbdev, i pgTAP verdi. Il primo apply su dbdev, lanciato prima del `DELETE`, si è fermato sulla
`preCondition` del `-25` dopo aver applicato `-23` e `-24`: è il comportamento voluto, e l'apply
successivo è ripartito dal `-25`. Verificato sul catalogo di dbdev: nessuna riga senza processo,
`processo_codice` `NOT NULL`. ⏳ La doc auto-generata di `maintenance` è ancora da rigenerare.

| File | Che cosa |
| --- | --- |
| `00_schema/maintenance/20261122-23-create-ix-job-run-log-corsie-processo-mctit.yaml` | `ix_job_run_log_processo_codice_jobname_started_at`, col `COMMENT` |
| `20_code/maintenance/20261122-24-update-vw-job-run-da-superuser-senza-ramo-storico-mctit.yaml` | `vw_job_run_da_superuser`: la chiave è il processo, una discesa e una `LATERAL` sola |
| `90_end/20261122-25-alter-job-run-log-processo-obbligatorio-mctit.yaml` | `VALIDATE`, `SET NOT NULL`, il `CHECK` ritirato, l'indice parziale ritirato, il `COMMENT` della colonna. In `90_end` perché il `CHECK` nasce lì (§11.14). Una `preCondition` `HALT` ferma il migrate finché restano righe senza processo |
| `db/pgtap/maintenance/test-job-run-log-per-chiave-v1.sql` | riscritto (plan 12): gli indici, il parziale assente, il `NOT NULL`, il `CHECK` assente, il `23502`, le due viste per chiave senza il ramo storico |
| `test-job-run-attore.sql` | il test 8 aspetta `23502` (il `NOT NULL`) al posto di `23514` |
| `test-job-run-registrazione.sql` | il test 7 passa un processo vero: era **verde per il motivo sbagliato**. Senza processo il `23514` poteva venire da tutti e due i `CHECK`, quello dell'origine e quello del processo; ora il `NOT NULL` risponde prima con `23502` |
| `test-vw-job-run-da-guardare-causa-v1.sql`, `-verdetto-completo-v1.sql` | solo i commenti: il caso «senza processo» il modello non lo ammette più |
| `manual/` di `job_run_log`, `vw_job_run_da_superuser`, `vw_job_run_da_guardare`, `fn_run_and_log`, `fn_job_run_log_failure`; le guide `analisi-tracciamento-processi-e-job`, `processi-pgagent-funzionali`, `processi-automatici-classe-e-identita` | il `NOT NULL` al posto del `CHECK`; la query «corse senza attore» della guida è uscita |

**Il passo di Tid, prima dell'apply, su dbdev** (lavora come `zeroerp_owner`):

```sql
BEGIN;
SELECT jobname, count(*), min(started_at), max(started_at)
  FROM maintenance.job_run_log WHERE processo_codice IS NULL GROUP BY jobname ORDER BY 1;
DELETE FROM maintenance.job_run_log WHERE processo_codice IS NULL;
COMMIT;
```

Fatto datato (dbdev, 2026-11-22): 99 775 righe, dal 2026-01-07 al 2026-09-05. Lo scratch non ne
ha, come ogni database costruito da zero. ⚠️ 37 lavori di `dbops.coda_lavori` puntano a quelle righe
con `job_run_id`, che non ha FK: restano orfani, come quelli che lascerà la potatura (§7.4). Niente si
rompe; nessuna vista DB legge `coda_lavori.job_run_id`. ⚠️ *Superato dal §10: li azzera il changeSet
del giro 3, prima della FK.*

**Prova** (`prova_changeset.py`, ROLLBACK sullo scratch, i tre changeSet insieme):

* `test-job-run-log-per-chiave-v1` da 7/12 senza l'estratto a 12/12 con. I 5 rossi senza sono lo
  stato nuovo: l'indice, il parziale assente, il `NOT NULL`, il `CHECK` assente, il `23502`.
* `test-job-run-attore` da 10/11 a 11/11 (il `23502`). `test-job-run-registrazione` 21/21 nei due
  versi dopo la correzione del test 7.
* Invariati: `test-app-postura-job-run-log-v1` (10, con 1 rosso da owner che c'era già),
  `-log-failure-out-of-tx` (7), `-ruolo-sessione-v1` (10), `-saltata-v1` (11), `-sqlstate-e-codice-v1`
  (9), `test-vw-job-run-da-guardare` (6), `-causa-v1` (15), `-corse-distinte-v1` (2),
  `-verdetto-completo-v1` (17); in `dbops` `test-vw-processi-programmazione` (21),
  `-da-guardare` (7), `test-processi-convergenza-ci` (8), `test-presidio-processi-testo-per-causa-v1`
  (18), `test-processi-registro` (16), `test-fn-guardiano-digest` (9), `test-installazione-ambiente-v1`
  (23), `test-security-definer-search-path-v1` (5), `test-comment-al-presente-v1` (8); in `script`
  `test-canale-log-v1` (16). `guardrail_comment_al_presente.py` pulito.
* La forma (§6.4, `enable_seqscan = off`): `vw_job_run_da_superuser` scende sull'indice di processo
  senza `Sort`, la discesa delle corsie usa l'indice nuovo. 4 su 4 con l'estratto, 2 su 4 senza.

⚠️ **Non toccata, apposta:** `vw_job_run_da_guardare`. I suoi `COALESCE` sul processo (il
`LEFT JOIN` verso `dbops.processi`, la causa `PROGRAMMA` di ripiego) non sbagliano nulla col
`NOT NULL`: sono difese che il modello non raggiunge più. Riscrivere la vista solo per toglierle
vorrebbe un banco di equivalenza per nessun cambio di risultato; lo dice il suo manuale.

**Richieste al BE (`/arrivi-db`, dopo l'apply):**

1. Ritirare il ramo `processo_codice IS NULL AND split_part(jobname, ':', 1) = %s` di
   `list_job_summary`: le righe senza processo non esistono più.
2. **Censire i lettori che contano sul `23514` o sul nome `chk_job_run_log_processo_dichiarato`**
   per riconoscere una corsa senza processo: ora la respinge il `NOT NULL`, con `23502` e senza un
   nome di vincolo `CHECK`. Lato DB nessuna funzione intercetta quel codice (censito sul catalogo).
3. Se un lettore gestisce ancora `processo_codice` NULL (in `cte_corse`, in `job_liveness`, nelle
   risposte delle API), può smettere: la colonna è `NOT NULL`. Facoltativo, non rompe niente.
4. La liveness per processo (`job_liveness(processo_codice=…)`) non cambia: la sua discesa trova da
   sola l'indice delle corsie.

### 8.8 Il giro 2b ✅ applicato, verde (2026-11-22)

Via di Tid, 2026-11-22. ✅ Applicato da Tid su scratch e dbdev il 2026-11-22, con i pgTAP verdi.
Verificato sul catalogo dei due database: i quattro changeSet eseguiti, il processo
`pota_giornale_corse` nel seed, `potatura_esclusione` sui tre processi della fatturazione, il job
pgAgent creato. ⚠️ Su dbdev `zeroerp_job` non ha ancora l'`EXECUTE` sulla procedura (sullo scratch
sì): manca la fase post del provisioning, e senza la prima corsa notturna fallisce per permesso
negato. Rilanciata la fase post, il catalogo di dbdev non ha ancora il permesso (la procedura ha il
solo `zeroerp_owner=X`, le sorelle anche `zeroerp_job=X`). ✅ La doc auto-generata di `dbops` e
`maintenance` è rigenerata.

ℹ️ Il primo apply si è fermato su un difetto della sessione `ui`, non di questo giro:
`messaggi_errore.csv`, riga 1265, una virgola senza virgolette. L'apply ha portato anche i changeSet
`ui` ancora non committati (`20261122-26` … `-28`).

| File | Che cosa |
| --- | --- |
| `00_schema/dbops/20261122-29-alter-processi-add-potatura-esclusione-mctit.yaml` | `dbops.processi.potatura_esclusione text`, `chk_processi_potatura_esclusione_non_vuota`, il `COMMENT` (§8.4) |
| `20_code/maintenance/20261122-30-create-fn-pota-giornale-corse-mctit.yaml` | `maintenance.fn_pota_giornale_corse(soglia)`: `STRICT`, `SECURITY INVOKER`, `EXECUTE` tolto a `PUBLIC`; restituisce `{soglia, cancellate}` |
| `20_code/maintenance/20261122-31-create-proc-pota-giornale-corse-job-mctit.yaml` | `maintenance.proc_pota_giornale_corse_job()`, come le sorelle; la soglia di 12 mesi sta qui |
| `85_pgagent/20261122-32-create-pgagent-job-pota-giornale-corse-mctit.yaml` | il job pgAgent, ogni notte alle 03:30 (ora libera), il passo dietro il cancello della sveglia |
| `80_data/sql/dbops/processi.csv` | la colonna in coda; l'esclusione dei tre processi della fatturazione (D-R3); la riga 50, `pota_giornale_corse`: `MANUTENZIONE`, `PGAGENT`, fuori dalla convergenza di CI col motivo, acceso in sviluppo e in produzione, verdetto completo |
| `db/pgtap/maintenance/test-pota-giornale-corse-v1.sql` | nuovo, plan 19 |
| `manual/` nuove: `fn_pota_giornale_corse`, `proc_pota_giornale_corse_job`; toccate: `job_run_log` (la ritenzione), `processi` (la colonna), `coda_lavori` (`job_run_id` orfano), `vw_job_run_da_guardare`, `vw_processi_programmazione`; la guida `analisi-tracciamento-processi-e-job` | |

**Come lavora.** Cancella le corse chiuse con `started_at` prima della soglia, dei processi senza
`potatura_esclusione`. Le corse aperte restano sempre. Per ogni coppia `(processo_codice, jobname)`
restano l'ultima riga di ciascun predicato dei lettori (vedi sotto). Le coppie si leggono con una
discesa ricorsiva sull'indice delle corsie del giro 2a, e ogni predicato è una `LATERAL … LIMIT 1`
sullo stesso indice. La soglia è l'inizio del giorno aziendale di 12 mesi fa, con i BB
`script.fn_giorno_operativo`, `script.fn_mesi_dopo` e `script.fn_inizio_giorno_operativo`.
`now() - interval '12 months'` lo ha fermato il guardrail (`mesi-intervallo`, §11.10): conterebbe
nel fuso della sessione di pgAgent.

**Il framework di cleanup non è la stessa cosa** (regola del 2, verificato).
`dbops.fn_run_automations_cleanup` dà una scadenza alla nascita a ogni riga (`cleanup_at`) e
cancella lo scaduto, schema per schema su `dbops.automation_scope`, dove `maintenance` non c'è.
Qui una riga vecchia resta se è «l'ultima» di qualcosa: la regola dipende dalle righe vicine.

#### ✅ Due ritocchi alle decisioni, confermati da Tid il 2026-11-22 (tengono di più, non di meno)

1. **La chiave è la coppia `(processo, jobname)`**, non «ogni job e ogni processo» presi da soli
   (D-R1). Scrivendo è emerso che il modello non lega un `jobname` a un processo solo: il BE passa
   il processo esplicito, e nessun vincolo lo vieta. Con il solo `jobname` come chiave, l'ultima
   riga del job può essere di un altro processo, e la potatura toglierebbe l'ultima del primo. La
   coppia copre tutti i lettori: quelli per job, quelli per processo e il «processo = K OR jobname
   = K» del panorama. Il test 14 costruisce il caso. La mutazione con la chiave per solo `jobname`
   fa diventare rossi i test 10, 12 e 13.
   ⚠️ Vicolo cieco, scritto perché non si riprovi: una prima stesura teneva per solo `jobname`,
   «perché le righe di un job sono una parte di quelle del suo processo». È falso, per la ragione
   qui sopra.
2. **Due righe in più fra quelle tenute** (D-R2): l'ultima **fallita** (`ok IS FALSE`, l'ultimo
   rosso di `vw_job_run_da_guardare`) e l'ultima **di pgAgent** (`origine = 'PGAGENT'`, la data di
   `GIRA_E_NON_REGISTRA` di `vw_processi_programmazione`). Senza la seconda, un job pgAgent che
   gira una volta all'anno farebbe scattare `GIRA_E_NON_REGISTRA` per un motivo falso. Le ha
   trovate la rilettura dei corpi dei lettori.

#### Garanzia ritirata: il censimento chiuso lato DB (§7.3, completato)

| Lettore DB | Esito |
| --- | --- |
| `vw_processi_programmazione` | coperto: l'ultima corsa, l'ultima di pgAgent e l'ultima non saltata (aperta o conclusa) restano. Il `max()` su tutte le corse del processo, segnalato al §6.3, ha ora il limite della ritenzione. La vista non si riscrive |
| `vw_job_run_da_guardare` | coperto per il verdetto e la causa. ⚠️ Un caso cambia: per una corsa **appesa da più di un anno**, `falliti_ultimi_7_giorni` conta i fallimenti dei sette giorni prima solo fra le righe tenute. Scritto nel manuale della vista |
| `vw_job_run_da_superuser` | coperto: l'ultima col ruolo resta, per coppia e quindi per processo |
| `dbops.coda_lavori.job_run_id` | senza FK, può restare orfano: scritto nel manuale della coda. ⚠️ Superato dal §10: FK `ON DELETE SET NULL` |
| i quattro scrittori | non ne dipendono: leggono solo la propria riga per `id` |

**Prova** (`prova_changeset.py`, ROLLBACK sullo scratch, i quattro changeSet insieme):

* `test-pota-giornale-corse-v1`: 17 su 19. I due rossi sono i test 17 e 18, che leggono il seed:
  la prova non applica i CSV, e diventano verdi con l'apply. Tre mutazioni viste dal test: la chiave
  per solo `jobname` (rossi 10, 12, 13), la corsa aperta non tutelata (rosso 11), l'ultima fallita
  tolta (rosso 9).
* Invariati, insieme all'estratto, i pgTAP di `maintenance` e i presidi di `dbops` su processi,
  pgAgent, installazione, `SECURITY DEFINER`, commenti, postura e riferimenti morti. Fanno
  eccezione due rossi attesi solo nella prova:
  * `test-processi-jobname-wrapper`, test 1: il nome `pota_giornale_corse` arriva col CSV;
  * `test-proc-job-definer-v1`, test 7: l'`EXECUTE` di `zeroerp_job` sulla procedura nuova lo dà
    la fase post del provisioning (`scripts/sql/provision_zeroerp.sql`, il ciclo su
    `maintenance.proc_*_job`). Sui database già vivi va rilanciata dopo l'apply; in CI gira dopo il
    migrate.
* Guardrail puliti: `comment_al_presente`, `forme_changeset`, `run_on_change`, `precondition_seed`,
  `grant_ruolo_batch`, `sql_letterali`, `timestamp_senza_fuso`, `pgtap_preambolo`.

**I passi di Tid:**

1. ✅ Confermare i due ritocchi qui sopra (2026-11-22).
2. ✅ Applicare `20261122-29` … `-32` su scratch e dbdev. Il CSV dei processi rientra da solo: il suo
   caricatore è `runOnChange`.
3. Rilanciare la fase post del provisioning su scratch e dbdev, per l'`EXECUTE` di `zeroerp_job`.
   ✅ scratch; ⏳ **dbdev**: lanciata, ma il permesso non risulta.
4. ✅ Lanciare `test-pota-giornale-corse-v1`, `test-processi-jobname-wrapper`, `test-proc-job-definer-v1`,
   `test-processi-registro`, `test-processi-convergenza-ci`, `test-installazione-ambiente-v1`.
5. ✅ Rigenerare la doc auto-generata di `dbops` e `maintenance`.

Su dbdev la prima corsa notturna non cancella niente: il giornale parte dal 2026-09-04 (fatto
datato, 2026-11-22).

**Richieste al BE (`/arrivi-db`, dopo l'apply):**

1. Le doc che promettono tutta la storia, già censite al §7.4: `api_tracciamento.md` (lo scopo,
   `job-runs` senza limite di data, i conteggi di `job-summary`), `api_amm_software.md` (§6.9, la
   paginazione delle corse del processo), `api_fatturazione.md` («assente = totali da sempre»: per
   la fatturazione resta vero, perché è esclusa dalla potatura).
2. Nessun cambio di contratto: la potatura non tocca API né risposte. Il censimento dei lettori
   applicativi del §7.4 resta valido. Se un lettore conta sull'ultima corsa **fallita** o **di
   pgAgent** di un job, ora c'è sempre (§8.8, ritocco 2).

## 9. La risposta del BE al §8.7 e al §8.8 — 2026-11-22

Sessione BE (`dev/backend-tid`), `/arrivi-db` dopo l'apply dei giri 2a e 2b.

### 9.1 Fatto ✅

| Richiesta | Esito |
| --- | --- |
| §8.7-1, il ramo storico di `list_job_summary` | ritirato: il filtro è `processo_codice = %s`, un parametro solo. Il test del repository vuole tre occorrenze del filtro e nessun `split_part`. **Chiamata reale su dbdev**: il riepilogo della fatturazione torna le sue due corsie; l'`EXPLAIN` del riepilogo per processo è un `Index Only Scan` su `ix_job_run_log_processo_codice_jobname_started_at` |
| §8.7-2, chi conta sul `23514` o sul nome del `CHECK` | **nessun lettore** in `backend/` né in `frontend/`. `registered_job` vuole `processo_codice: str` già nella firma, quindi il BE non manda mai una corsa senza processo. Aggiornato un solo commento di test |
| §8.7-3, il NULL di `processo_codice` nei lettori | niente da togliere: `cte_corse` e `job_liveness` non avevano rami per il NULL. Il filtro per processo nella `LATERAL` di `job_liveness` resta, per la ragione del ritocco 1 del §8.8 (un `jobname` non appartiene a un processo solo): scritto nel commento |
| §8.8, ritocco 1, negli altri lettori (dalla revisione, 2026-11-22) | `corsa_riuscita_dal` / `corsa_chiusa_dal` (`e_dovuto`) cercavano per solo `jobname`: una corsa dello stesso nome di un altro processo chiudeva il periodo, e la sveglia saltava senza errore. Ora la chiave è la coppia, `processo_codice` keyword-only passato da `sveglia.processo_codice`; test 7 di `tests/db/test_corsa_riuscita_dal_db` sul DB vero (rosso col filtro tolto). ⚠️ Restano per solo `jobname`, per contratto e da decidere: `job_liveness(jobnames=…)`, `job-summary` senza filtri, `job-runs?jobname=` |
| §8.8-1, le doc che promettono tutta la storia | `api_tracciamento.md`: una sezione «Ritenzione del giornale», con `job-runs` (`date_from`) e i conteggi di `job-summary` che la richiamano, gli indici e il filtro per processo aggiornati. `api_amm_software.md` §6.9: la paginazione arriva fino alla ritenzione. `api_fatturazione.md`: «da sempre» resta vero, e il perché (`potatura_esclusione`); la sorgente dei giri è per processo, non più per prefisso |

Nessun FE da toccare: nessuna risposta cambia forma.

### 9.2 ⏭️ Richiesta al team DB: la potatura non lascia `coda_lavori.job_run_id` orfano

**Il caso.** `dbops.coda_lavori.job_run_id` non ha FK (lo dice il suo manuale): dopo la potatura
un lavoro vecchio punta a una corsa che non c'è più. Il BE lo espone in due risposte, il dettaglio
del lavoro della coda (`CodaLavoriRepository.get_dettaglio`, mostrato a video da
`JobDettaglioDrawer`, voce «Run worker») e lo stato di un giro di fatturazione
(`VenditeFatturazioneRunStatoData`, in `vendite/api/views.py`). Un numero che non porta a niente, a video, si legge come un
malfunzionamento.

**Decisione di Tid (2026-11-22): non si mostra, e lo toglie il DB alla fonte.** La strada scartata
era il BE che, in lettura, controlla che la corsa esista e manda NULL: andrebbe fatta in ogni lettore
di oggi e di domani, e il dato sbagliato resterebbe nel database.

**Cosa chiede il BE.** Che, nella stessa operazione che pota il giornale, i lavori della coda che
puntano a una corsa cancellata abbiano `job_run_id = NULL`. Il BE e il FE trattano già il NULL
(«—» nel drawer, `allow_null` nello schema dello stato). La forma la decide il team DB; i punti che
il BE ha visto e che la toccano:

* `coda_lavori` ha la row level security e il trigger d'archiviazione
  (`trg_coda_lavori_a10_archiviazione_upd`): la potatura, che corre come `zeroerp_job`, deve poter
  aggiornare anche i lavori archiviati e quelli di ogni azienda;
* i trigger di audit e di `tx_id` scattano sull'`UPDATE`: va deciso se l'azzeramento lascia la sua
  traccia di audit come ogni altra modifica;
* il garbage collection della coda (`cleanup_at`) è un'altra cosa e non lo copre: un lavoro può
  vivere più a lungo della sua corsa.
* **I 37 orfani di oggi su dbdev** (§8.7: i lavori che puntavano alle righe senza processo
  cancellate). Si sistemano a mano su dbdev, come le righe di D-R4, o con la prima potatura se la
  regola è «nessun `job_run_id` senza corsa» e non solo «quelli che cancello adesso».

**Il manuale di `coda_lavori`** oggi dice «un lavoro vecchio può puntare a una corsa che non c'è
più»: dopo il giro diventa «`job_run_id` NULL vuol dire mai preso da un worker, oppure corsa non più
nel giornale». Lato BE lo dice già `api_gestione_code.md` §4 (riga 9-bis della testata), con la
garanzia segnata ⏳ fino a questo giro: dopo l'apply si toglie il ⏳.

## 10. Giro 3: `coda_lavori.job_run_id` segue il giornale ✅ applicato, verde (2026-11-22)

✅ Tid, 2026-11-22: `20261122-33` e la riga di `fk_index_policy.csv` applicati, il pgTAP del §10.4
verde, la doc auto-generata di `dbops` rigenerata.

Team DB (`dev/db-tid`), dopo il §9.2. Decisioni di Tid (2026-11-22): la forma è una **FK**, e
l'azzeramento riscrive `data_update` e `user_update`; via al giro.

### 10.1 La forma: una FK, non un `UPDATE` nella potatura

`fk_coda_lavori_job_run_log`: `coda_lavori.job_run_id` verso `maintenance.job_run_log(id)`,
`ON DELETE SET NULL`. La regola è «nessun `job_run_id` senza corsa», per chiunque cancelli dal
giornale: la potatura, un `DELETE` a mano come quello di D-R4, uno strumento futuro. Un `UPDATE`
dentro `fn_pota_giornale_corse` avrebbe coperto la sola potatura.

⚠️ **Revoca** due decisioni scritte: il «senza FK, apposta» del giro 2b (§8.8, 2026-11-22), che
accettava l'orfano perché il giornale si pota, e il «no FK cross-schema se sconveniente» di
`brief-db-coda-lavori-generica` (2026-07-20). Il giornale ha già una FK verso un altro schema
(`fk_job_run_log_processi`).

### 10.2 Come si comporta l'azione, sui punti del §9.2

| Punto | Esito |
| --- | --- |
| RLS di `coda_lavori` | l'`UPDATE` della FK gira come proprietario della tabella e non subisce la policy, nemmeno con `FORCE`: tocca i lavori di ogni azienda, e `zeroerp_job` non prende permessi sulla coda. Provato dal pgTAP (test 5 e 8) |
| trigger d'archiviazione | `trg_coda_lavori_a10_archiviazione_upd` è `UPDATE OF archiviato, stato, archiviato_il, archiviato_da`: non scatta. Il lavoro archiviato resta archiviato, con data e autore (test 9) |
| audit e `tx_id` | scattano, come su ogni modifica: `data_update` è l'istante della cancellazione, `user_update` il proprietario. Il `tx_id` della riga resta. `coda_lavori` non ha tabella di storico |
| la pulizia della coda | la coda non ha una pulizia: i lavori si archiviano e non si cancellano. Non esiste un `cleanup_at` sulla coda (il §9.2 lo nominava). Un lavoro vive quindi sempre più a lungo della sua corsa |
| lo scrittore | il drenatore timbra la corsa aperta da `script.fn_job_run_start` (`registered_job`), già committata sulla stessa connessione: la FK la trova. Un `job_run_id` inesistente è `23503` (test 4) |
| l'indice | parziale, `ix_coda_lavori_job_run_id … WHERE job_run_id IS NOT NULL` (linee-guida-sql §8.4): riga `CON_INDICE` nel CSV della policy, la crea `apply_fk_index_policy()` in `90_end` |

### 10.3 Il pregresso

Il changeSet azzera i `job_run_id` senza corsa prima di aggiungere la FK, su ogni database: la
regola vale per tutte le righe, non solo per quelle che la potatura cancellerà. Da zero la coda è
vuota e l'`UPDATE` tocca zero righe. Fatto datato (dbdev, 2026-11-22): 37 lavori, quelli delle righe
senza processo cancellate in D-R4 (§8.7). Niente da fare a mano.

### 10.4 Che cosa c'è, e come è provato

| Oggetto | |
| --- | --- |
| `00_schema/dbops/20261122-33-alter-coda-lavori-fk-job-run-log` | l'azzeramento, la FK, il `COMMENT` della FK e della colonna (quello vecchio diceva «no FK cross-schema») |
| `80_data/sql/dbops/fk_index_policy.csv` | la riga `fk_coda_lavori_job_run_log`, `CON_INDICE`, indice parziale |
| `db/pgtap/dbops/test-coda-lavori-job-run-id-segue-il-giornale-v1.sql` | 11 test, runner owner: la FK, la policy e l'indice, lo scrittore, la potatura con la RLS armata (stessa azienda, altra azienda, archiviato, corsa tenuta), un `DELETE` qualunque |
| `manual/` | `coda_lavori` (la colonna e la storia), `fn_pota_giornale_corse` (che cosa resta), `job_run_log` (il vedi anche); la guida `processi-automatici-classe-e-identita` |

**La prova** (`scripts/prova_changeset.py`, 2026-11-22):

* scratch, l'estratto più un changeSet di simulazione nello scratchpad (il mirror della riga della
  policy e `CALL dbops.apply_fk_index_policy()`): pgTAP **senza 4 ok / 7 not ok → con 11 ok / 0 not
  ok**. Senza l'estratto mancano la FK, la policy, l'indice e il rifiuto (1-4), e nessun lavoro perde
  il riferimento (7, 8, 11); i verdi senza (5, 6, 9, 10) non dipendono dalla FK;
* solo l'estratto, senza la simulazione: 1 e 4-11 verdi, 2 e 3 rossi, come atteso prima del
  `80_data` e del `90_end`;
* dbdev, l'estratto da solo: eseguito per intero, con i 37 orfani azzerati e la FK convalidata.

### 10.5 Richiesta al team BE/FE

1. `docs/it/backend/core/manual/api_gestione_code.md` §4: dopo l'apply di `20261122-33` la garanzia
   «`job_run_id` NULL vuol dire anche corsa non più nel giornale» non è più ⏳. Nessun cambio di
   contratto: le risposte avevano già `job_run_id` nullable (`get_dettaglio`,
   `VenditeFatturazioneRunStatoData`).
2. **Censisci i lettori di `coda_lavori.job_run_id` che contano su «il numero porta sempre a una
   corsa»**, oltre ai due già noti (il drawer, lo stato del giro di fatturazione). La garanzia ora è
   più forte di prima; un lettore che faceva un join e trattava il «non trovato» come errore ora non lo
   incontra più.
3. Resta del §9.1 la domanda di contratto sui lettori che cercano per solo `jobname`
   (`job_liveness(jobnames=…)`, `job-summary` senza filtri, `job-runs?jobname=`): del BE, con Tid. Non
   chiede niente al DB.

## 11. La risposta del BE al §10.5 — 2026-11-22

Sessione BE (`dev/backend-tid`), dopo il merge del giro 3 (PR #214).

### 11.1 La garanzia, senza ⏳

`api_gestione_code.md` §4 dice ora che un `job_run_id` non `null` porta sempre a una corsa, e perché:
la FK `fk_coda_lavori_job_run_log` è `ON DELETE SET NULL`, per chiunque cancelli dal giornale. Nessun
contratto cambia: le due risposte avevano già il campo nullable.

### 11.2 I lettori di `coda_lavori.job_run_id`

Censiti in `backend/` e `frontend/src/`. **Nessuno** fa un join verso `maintenance.job_run_log` né
tratta un «corsa non trovata» come errore: tutti passano il numero così com'è.

| Lettore | Che cosa ne fa |
| --- | --- |
| `CodaLavoriRepository.elenca` (lista della coda) | lo porta nella riga; il FE della lista non lo mostra |
| `CodaLavoriRepository.get_dettaglio` → `JobDettaglioDrawer.vue` | «Run worker», `?? '—'` sul `null` |
| `CodaLavoriRepository.get_stato` (polling) → `VenditeFatturazioneRunStatoData` | `IntegerField(allow_null=True)` |
| `mark_done` / `mark_failed` / la riconsegna del drenatore | **scrittore**, non lettore: il filtro di ownership `job_run_id IS NOT DISTINCT FROM %s` confronta il lavoro con la corsa che lo ha preso |

⚠️ Sull'ultima riga, il caso che la FK aprirebbe è una corsa **aperta** cancellata mentre il suo worker
lavora: il lavoro perderebbe il `job_run_id` e il `mark_done` non lo troverebbe più suo. Per la potatura
non succede per costruzione: le corse aperte sono fra le righe tenute (§8.8). Resta possibile solo per un
`DELETE` a mano su una corsa aperta, che è un atto di manutenzione e va fatto a worker fermo. Nessuna
modifica.

### 11.3 La domanda sui lettori per solo `jobname` (§9.1) → residuo, di Tid

Il modello non lega un `jobname` a un processo solo (ritocco 1 del §8.8). Tre lettori cercano ancora
per solo `jobname`, e due processi con una corsia dello stesso nome si confonderebbero, senza errore:

* `job_liveness(jobnames=…)`, dal badge della coda (`gestione_service`, i due drenatori, dove il
  `jobname` è il codice del processo);
* `GET …/tracciamento/job-summary/` senza filtri: una riga per `jobname`;
* `GET …/tracciamento/job-runs/?jobname=`: il filtro, e la riga, non portano `processo_codice`.

È una domanda di contratto del BE, non chiede niente al DB. ⚠️ Decisa da Tid la sera stessa,
strada (a): i tre lettori passano alla coppia (§11.5). La voce del registro dei residui, scritta alla
chiusura, è stata tolta nello stesso giro.

### 11.4 La chiusura

Brief archiviato in `work-done/2026/`. Ricollegati i rimandi di `api_gestione_code.md`,
`api_tracciamento.md` e `work-done/2026/brief-db-lista-processi-esito-con-la-sua-data.md`; i rimandi per
nome (changeSet, pgTAP, pagine `manual/`, commenti del codice) restano validi.

### 11.5 Strada (a): la corsia è la coppia, in ogni lettore ✅ (2026-11-22)

Decisione di Tid (2026-11-22): i tre lettori del §11.3 passano a `(processo_codice, jobname)`. Lato
BE soltanto: ⚠️ il FE **non** consuma né `job-runs` né `job-summary` (nessun chiamante in
`frontend/src`), e la risposta del badge non cambia forma. Il «una colonna e un filtro nel FE»
detto in chat prima della decisione era sbagliato.

| Lettore | Ora |
| --- | --- |
| `cte_corse` (BB) | la chiave è `processo_codice` oppure `corsia`, la coppia; la chiave per solo `jobname` è **ritirata**, e `chiave` è obbligatoria |
| `job_liveness` | `processo_codice` obbligatorio (keyword), `jobnames` restringe dentro il processo; il ramo «per soli nomi» non esiste più |
| badge della coda (`_liveness_worker`) | le due corsie dei drainer come coppie, una lettura per processo con la soglia del suo contratto; la risposta è la stessa |
| `job-summary` | una riga per corsia, con `processo_codice`; `GROUP BY processo_codice, jobname` |
| `job-runs` | ogni riga porta `processo_codice`; filtro `processo_codice=` facoltativo, che con `jobname` fa la corsia. Il nome da solo resta un filtro ammesso: la riga dice di chi è ogni corsa |

**Trovato strada facendo, corretto:** l'`ORDER BY started_at` di `job-runs` si risolveva sulla
colonna di output `started_at::text` e ordinava il testo sotto la collation `it_IT`, non l'istante, e
nessun indice serviva l'ordine (con una sessione in un fuso con l'ora legale sarebbe anche sbagliato
nell'ora che il cambio d'ora ripete; la sessione Django è in UTC). Ora è qualificato, `job_run_log.started_at`. Il `Seq Scan` della stessa query
resta, ed è del totale `COUNT(*) OVER ()` della paginazione, non dell'ordine.

**Prove.** `tests/db/test_job_liveness_per_corsia` (rinominato da `test_job_liveness_due_chiavi`),
test 7: due processi con una corsia dello stesso nome, una aperta e una conclusa, **costruiti** con
`script.fn_job_run_start/_end` e ritirati. Liveness, riepilogo e corse non si mescolano. Verde sul DB
vero; rosso con la `LATERAL` che cerca per solo nome. Test unitari: la forma dell'SQL dei tre
lettori, i parametri nell'ordine dei `%s`, la view che passa la corsia. `EXPLAIN` su dbdev: la
liveness (con e senza `jobnames`) e le `LATERAL` del riepilogo scendono in
`ix_job_run_log_processo_codice_jobname_started_at`.

**Doc:** `api_tracciamento.md` (i due endpoint e la tabella dei metodi), `api_gestione_code.md` (la
liveness per corsia), il catalogo BB backend (`cte_corse`, `job_liveness`, `gestione_service`,
`corsa_conclusa`) e l'indice rigenerato.

### 11.6 La revisione del giro (`/verifica`) ✅ (2026-11-22)

Sessione di revisione sul codice non committato di §11.5. Il diff regge; due difetti stavano **attorno**.

| Trovato | Corretto | Presidio (rosso col codice di prima, provato) |
| --- | --- | --- |
| `DbopsRepository.list_audit_logs` aveva lo stesso `ORDER BY executed_at` sulla colonna di output `executed_at::text`: `EXPLAIN` su dbdev, `Sort Key: ((executed_at)::text)` | `ORDER BY audit_log.executed_at DESC, audit_log.id DESC`; nota in `api_tracciamento.md` § audit-log | `tests/db/test_ordine_sull_istante_db` (nuovo): cattura l'SQL vero dei due repository (`execute_wrapper`) e ne legge il piano; nessuna chiave di ordinamento sul `::text`. Copre anche `list_job_runs`, che finora aveva solo un'asserzione sul testo della query |
| `_liveness_worker` (una lettura per processo, con la sua soglia) senza un test: il mock rispondeva uguale a ogni processo, e il ritorno al mapping per solo nome restava verde | — | `test_coda_lavori_gestione_service` 2-bis: soglie diverse per processo (una dal ripiego), e una corsa col nome del worker della coda lavori **sotto il processo della stampa**, che non deve accenderlo |

Allineati i commenti rimasti alla regola di prima: `pipeline_service` («GROUP BY jobname») e la nota sul
cambio d'ora in `list_job_runs` e in `api_tracciamento.md`. Esito: `apps.core` toccati, `apps.vendite`
(2766) e i test sul DB vero verdi; ruff e `gen_indice_bb.py --check` puliti. Non lanciato lo smoke
`smoke-test-ui-personalizzazioni-liste.sh` (vuole il BE in piedi). Nessuna richiesta al DB.

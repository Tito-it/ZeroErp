# Brief DB — Il giornale delle corse senza indici di lettura

## ⏭️ Chi riparte — aggiornato al 2026-11-22

**Riparte: sessione BE**: le richieste del §6.6 e il censimento dei lettori del giornale (§7.3). Il
giro 1 è applicato e verde (Tid, 2026-11-22). Il giro 2, la ritenzione (§7), parte dopo il censimento,
col via di Tid; D-R1 è decisa (§7.2).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione BE | Il caso, le chiavi di lettura del backend | §1-§2 | — |
| 2 | ✅ team DB | La verifica critica della richiesta | §6 | 1 |
| 3 | ✅ team DB | Giro 1: quattro indici, due viste riscritte, la prova, la doc `manual/` | §6.2-§6.4, §6.7 | 2 |
| 4 | ✅ Tid | Applicare `20261122-20` … `-22`; lanciare `test-job-run-log-per-chiave-v1` e i pgTAP del §6.7; rigenerare la doc auto-generata | §6.7 | 3 |
| 5 | **sessione BE** ⏭️ | L7 riportata alla `LATERAL` per processo; il `count(*)` di L7; il `LIKE` di L4; `api_tracciamento.md`; il censimento della ritenzione (§7.3) | §6.6, §7.3 | 4 |
| 6 | team DB | Giro 2: la ritenzione di 12 mesi | §7 | 5, il via di Tid |

**Decisioni di Tid:** ✅ 2026-11-22: le due viste DB che leggono tutto il giornale si riscrivono **in
questo giro** (§6.3). ✅ 2026-11-22: la ritenzione è un debito, e il giornale tiene **12 mesi** (§6.5, §7).
✅ 2026-11-22: D-R1 strada **(a)**, la potatura non tocca mai l'ultima corsa di ogni job e di ogni
processo (§7.2). Nessuna decisione aperta.
**Committato** (2026-11-22, `dev/db-tid`): il giro 1 (tre changeSet, un pgTAP, la doc di `maintenance`,
manuale e auto-generata) e questo brief. Il giro 2 non ha ancora file.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-22. **A chi:** team DB.
> **Origine:** revisione della doc API di `maintenance` ([api_tracciamento.md](../../backend/core/manual/api_tracciamento.md)),
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
* [api_tracciamento.md](../../backend/core/manual/api_tracciamento.md) § Note oggi dice «`job_run_log` ha
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

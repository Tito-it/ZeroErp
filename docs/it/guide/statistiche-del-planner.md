# Guida — Le statistiche del planner

> **Ultimo aggiornamento**: 3 novembre 2026
>
> **Destinatari**: sviluppatori database e backend, chi gestisce il database, e chi
> misura le prestazioni di una query
>
> **Vedi anche** — funzioni e viste DB:
>
> * [maintenance.fn_analyze_statistiche](/dbzero/maintenance/funzioni/fn_analyze_statistiche) — il lavoro: `ANALYZE` e la prova di esserci riuscito
> * [maintenance.vw_statistiche_mancanti](/dbzero/maintenance/views/vw_statistiche_mancanti) — le tabelle che resterebbero senza statistiche
> * [maintenance.proc_analyze_statistiche_job](/dbzero/maintenance/funzioni/proc_analyze_statistiche_job) — il lavoro notturno, che passa dal giornale
>
> **Vedi anche** — guide correlate:
>
> * [I lavori automatici](/guide/processi-automatici-classe-e-identita) — il registro dei processi e il panorama che li guarda
> * [Processi pgAgent](/guide/processi-pgagent-funzionali) — come si scrive un lavoro a orario
> * [Setup Liquibase](/liquibase-setup-workflow) — i diritti dei ruoli, §2

---

## In una frase

Ogni notte il database rifà la **fotografia** dei propri dati, che il planner usa
per decidere come eseguire ogni query. Se non riesce a farla per tutte le
tabelle, il lavoro **fallisce e lo dice**: non scrive «fatto».

---

## 1. Che cosa sono le statistiche

Prima di eseguire una query, PostgreSQL sceglie **come** eseguirla: quale indice
usare, in che ordine unire le tabelle, se scorrerle tutte. Per scegliere deve
**stimare** quante righe escono da ogni passaggio. Se pensa che ne escano tre fa
una cosa; se pensa che ne escano cinquantamila ne fa un'altra.

Le stime le prende dalle **statistiche** che scrive il comando `ANALYZE`: quante
righe ha una tabella, quali valori compaiono più spesso, come sono distribuite
le date, quanti campi sono vuoti. Sono una **fotografia dei dati**, non una
memoria delle esecuzioni: il planner non impara da una query andata lenta, stima
ogni volta da capo con l'ultima fotografia disponibile.

Senza fotografia il planner usa valori fissi di default, cioè stima alla cieca. A
volte ci prende, a volte sbaglia di cento volte. E quando la fotografia arriva in
un momento qualunque della giornata, il piano di una query **cambia da solo**:
stesso codice, tempi diversi.

⇒ Una volta scattata, la fotografia la usa il planner **da solo**, per ogni
query: non c'è niente da chiamare né da cambiare nel codice. Anche i piani già
tenuti in memoria dalle sessioni vengono ricalcolati sulla fotografia nuova.

---

## 2. Perché l'autovacuum non basta

PostgreSQL ha già un meccanismo automatico, l'**autovacuum**, che rianalizza una
tabella quando cambia abbastanza: 50 righe più il 10% della tabella. Non guarda
che cosa serve al planner, guarda **quanto è cambiata** la tabella. Per questo
lascia scoperti tre casi:

* **le tabelle piccole o ferme** — cataloghi, configurazione — non arrivano mai
  alla soglia, e il planner le stima sempre coi default;
* **le tabelle partizionate**: l'autovacuum analizza le partizioni, mai la madre;
* **un database appena costruito**, come quello della CI, che rinasce a ogni
  corsa: i test partono subito dopo il caricamento, quando non è ancora passato
  nessuno.

Il lavoro notturno copre questi tre casi; l'autovacuum continua a tenere
aggiornate di giorno le tabelle grandi e vive. Insieme fanno sì che nessuna
tabella resti senza fotografia.

---

## 3. Il lavoro notturno

| | |
| --- | --- |
| **Processo** | `analyze_statistiche`, in [dbops.processi](/dbzero/dbops/tabelle/processi), natura `MANUTENZIONE` |
| **Quando** | ogni notte alle 02:30, da pgAgent |
| **Che cosa** | `ANALYZE` di tutto il database, poi la verifica (capitolo 4) |
| **Dove lascia traccia** | [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log), sotto il codice del processo |

Gira alle 02:30 per stare lontano dagli altri lavori: le automazioni alle 21,
la chiusura delle scadenze a mezzanotte, la sincronizzazione degli utenti alle 6.
`ANALYZE` lavora in una **sola transazione** e tiene un lock leggero su ogni
tabella fino alla fine: non blocca letture e scritture, ma blocca le modifiche
di struttura e un altro `ANALYZE`.

### Che cosa analizza

Tutte le tabelle del database, tranne:

* gli schemi di sistema (`pg_catalog`, `information_schema`, `pg_toast`);
* le tabelle temporanee delle altre sessioni;
* gli oggetti che appartengono a un'**estensione** (pgAgent, PostGIS): si
  riconoscono dal catalogo, non da un elenco di nomi;
* una tabella partizionata senza partizioni, che non ha dati da descrivere.

Il **catalogo di sistema** (per esempio `pg_proc`, l'elenco delle funzioni)
viene analizzato se il ruolo che esegue è superuser o proprietario del database,
ma resta fuori dalla verifica: i diritti sui cataloghi non sono nostri da dare.

---

## 4. La verifica: il lavoro dice quando non ci è riuscito

`ANALYZE` **non fallisce** su una tabella che non ha il diritto di analizzare: la
salta con un avviso e va avanti. Senza un controllo, un lavoro che salta metà
delle tabelle scriverebbe «fatto» nel giornale.

Per questo, subito dopo `ANALYZE` e nella stessa transazione, il lavoro legge
[vw_statistiche_mancanti](/dbzero/maintenance/views/vw_statistiche_mancanti). Se
resta anche una sola tabella, **fallisce** con `E_STATISTICHE_MANCANTI` e nomina
le tabelle:

| Motivo | Che cosa vuol dire | Che cosa fare |
| --- | --- | --- |
| `NON_ANALIZZABILE` | il ruolo che esegue non ha il diritto di analizzare la tabella | dargli il diritto (capitolo 5) e rilanciare |
| `MAI_ANALIZZATA` | la tabella è ancora senza statistiche anche dopo `ANALYZE` | guardare la tabella: con il diritto non dovrebbe succedere |

Il fallimento lascia una riga rossa nel giornale, che resta anche se la
transazione viene annullata. Da lì la vede
[vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare), e
quindi il pannello dei presidi e il digest.

⚠️ La verifica sta **dentro** il lavoro e non in un controllo guardato durante il
giorno. Subito dopo `ANALYZE`, una tabella senza statistiche è un errore. In
un'ora qualunque potrebbe essere solo una tabella creata da una migrazione del
pomeriggio, che la notte sistemerà: un allarme che dipende dall'orologio.

---

## 5. Chi esegue, e con quali diritti

Per analizzare una tabella bisogna esserne il proprietario. Il lavoro lo è: pgAgent
si collega come `zeroerp_job` e chiama la procedura del lavoro, che gira come il
**proprietario** del database (`zeroerp_owner`). E siccome il proprietario è uno
solo e possiede tutte le tabelle, nessuna resta fuori. Sulla CI e sul database di
prova il lavoro lo chiama direttamente il proprietario, nel passaggio delle
automazioni.

Restano fuori solo i cataloghi condivisi del server PostgreSQL, che può analizzare
soltanto un amministratore: non sono tabelle del programma, e il controllo non li
conta.

Gli utenti del database e le loro regole: [Provisioning ruoli DB](/dev/backend/provisioning-db-roles).

### In CI e sul database di prova

Sulla CI di GitHub pgAgent non c'è; sul database di prova costruito da
`scripts/ci-local.sh` (`zeroerp_ruoli`) c'è, il job viene creato, ma nessun demone
lo fa partire. In entrambi il lavoro gira lo stesso: il processo dichiara a
catalogo la procedura e la sua posizione (`ci_ordine`, **l'ultima**), e il
passaggio `ci_apply` la chiama dopo tutti gli altri lavori strutturali, prima
dei test. Così anche i test partono con statistiche vere, e un diritto mancante
ferma la build invece di passare in silenzio.

---

## 6. Come si controlla

* **È girato stanotte?** Nel pannello dei processi automatici,
  `analyze_statistiche` è `OK`. Un lavoro nuovo, prima della sua prima corsa,
  risulta `IN_ATTESA` e non è un guasto.
* **È andato bene?** L'ultima riga di `analyze_statistiche` nel giornale è
  riuscita. Se è rossa, il messaggio nomina le tabelle e il motivo.
* **Quali tabelle sono senza statistiche adesso?** Si legge
  `maintenance.vw_statistiche_mancanti` **col ruolo che conta**: la vista
  risponde per chi la interroga, e per l'applicazione ogni tabella è
  `NON_ANALIZZABILE`, com'è giusto.

---

## 7. Che cosa le statistiche non fanno

* **Non imparano dalle esecuzioni.** PostgreSQL non corregge un piano a metà
  query e non ricorda che una query è andata lenta: stima con la fotografia che
  c'è. Se di giorno una tabella cambia molto, fino alla notte vale la fotografia
  vecchia, salvo che arrivi l'autovacuum.
* **Non correggono una query scritta male.** Una sottoquery che si ricalcola per
  ogni riga resta lenta anche con stime perfette. Quello si cura con la **forma**
  della query: calcolare una volta (`MATERIALIZED`), leggere per chiave invece
  che tutto, dichiarare la cardinalità di una funzione, che `ANALYZE` non guarda
  mai (vedi [linee-guida-sql](/linee-guida-sql)).
* **Rendono le misure confrontabili.** Con la fotografia aggiornata, in un
  `EXPLAIN ANALYZE` le righe stimate sono vicine a quelle reali: una differenza
  grossa diventa un'informazione vera, non rumore.

---

## Area tecnica — esempi

Lanciare il lavoro a mano, passando dal giornale come fa la notte:

```sql
CALL maintenance.proc_analyze_statistiche_job();
```

Analizzare solo alcune tabelle, con la stessa verifica (dopo un import grande):

```sql
SELECT maintenance.fn_analyze_statistiche(
    ARRAY['vendite.ddt'::regclass, 'vendite.ddt_righe'::regclass]);
```

Le ultime corse:

```sql
SELECT started_at, ok, message
  FROM maintenance.job_run_log
 WHERE jobname = 'analyze_statistiche'
 ORDER BY started_at DESC
 LIMIT 5;
```

Da quando una tabella non viene analizzata (contatori che si azzerano a un
crash: per «mai» fa fede `pg_class.reltuples < 0`, che la vista usa):

```sql
SELECT schemaname, relname,
       greatest(last_analyze, last_autoanalyze) AS ultima_analisi
  FROM pg_stat_user_tables
 ORDER BY ultima_analisi NULLS FIRST
 LIMIT 20;
```

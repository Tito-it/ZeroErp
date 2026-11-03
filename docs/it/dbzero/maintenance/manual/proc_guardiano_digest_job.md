## 📘 Documentazione Concettuale – Procedura `maintenance.proc_guardiano_digest_job`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui resta la corsa del guardiano
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — i processi `guardiano_digest` e `digest_presidi`
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — dove finisce l'avviso `NOTIFICA_DIGEST_MUTO`
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il panorama da cui il guardiano legge lo stato del digest, e che guarda anche lui
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — dove compare una corsa rossa del guardiano
>
> Approfondimento funzioni:
>
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — esegue il lavoro e scrive la corsa
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
> * [dbops.fn_guardiano_digest](/dbzero/dbops/funzioni/fn_guardiano_digest) — il lavoro: guarda il digest e, se tace, accoda l'avviso

---

### 🎯 Scopo Principale

Il wrapper del job pgAgent `guardiano_digest`: esegue `dbops.fn_guardiano_digest` attraverso il
giornale dei job, così il guardiano del digest dei presidi è a sua volta guardato.

---

### Chi guarda il guardiano

Il digest dei presidi (`digest_presidi`) segnala a una persona tutti i guasti degli altri
processi. Se si ferma lui, nessun messaggio lo dice: un digest morto non manda la mail che
annuncia la propria morte. Il guardiano vive in pgAgent, cioè dentro il database, in un mondo che
non muore insieme ai timer del backend: ogni ora legge dal panorama lo stato del digest e, se è
`MUTO`, accoda un avviso `NOTIFICA_DIGEST_MUTO` al giorno, che il drenatore della coda spedisce.
Le regole stanno nella scheda di
[dbops.fn_guardiano_digest](/dbzero/dbops/funzioni/fn_guardiano_digest).

---

### ⭐ Passare dal giornale rende la guardia reciproca

Il guardiano è a catalogo come processo `PGAGENT`, e questa procedura lo fa passare da
`maintenance.fn_run_and_log`: ogni corsa lascia una riga nel giornale, con il processo
`guardiano_digest` come attore (il codice coincide col nome del job pgAgent). Così il panorama
guarda anche lui, e il digest lo riporta: il digest guarda il guardiano, il guardiano guarda il
digest, e ciascuno dei due vede la morte dell'altro. Senza il giornale il guardiano sarebbe
invisibile a tutti i presidi.

La procedura passa a `fn_run_and_log` il codice del processo, il nome dello step e la chiamata,
senza chiave di lock. Il comportamento della corsa — la riga nel giornale, il verbale del
fallimento scritto fuori transazione, l'errore rilanciato — lo descrive la scheda di
[fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log).

---

### ⚠️ Una corsa rossa vuol dire «ho visto e non ho potuto dirlo»

Il guardiano non torna mai in silenzio quando non può fare il suo lavoro: se il digest non è a
catalogo, o se l'avviso non si può accodare, `dbops.fn_guardiano_digest` solleva un errore, e la
corsa è rossa in `maintenance.vw_job_run_da_guardare`. L'esito di una corsa riuscita — digest
vivo, avviso già mandato oggi, avviso accodato — la funzione lo restituisce come testo, ma
`fn_run_and_log` non lo conserva: nel giornale resta solo che la corsa è riuscita.

---

### Ogni ora, a sveglia accesa

Il job suona ogni ora, al minuto 20. Lo step chiama la procedura solo se
`maintenance.fn_sveglia_accesa('guardiano_digest')` è vero. Il processo non è spegnibile: spento,
nessuno guarderebbe più il digest.

La procedura è `SECURITY DEFINER` con `search_path` fisso, come tutte le `maintenance.proc_*_job`,
e l'EXECUTE è tolto a `PUBLIC`. La convergenza dei job in CI non la chiama: è un processo
operativo.

---

### Test

* `db/pgtap/dbops/test-fn-guardiano-digest.sql` — il guardiano a catalogo come `PGAGENT` col
  nome del job uguale al codice, e il lavoro: digest vivo, digest muto col tipo spento (solleva),
  digest muto col tipo acceso (accoda), una notifica al giorno, digest tolto dal catalogo
  (solleva).
* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — la procedura è `SECURITY DEFINER`, col
  `search_path` fisso, del proprietario dello schema, senza EXECUTE a `PUBLIC` né all'applicazione.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il codice passato come `p_jobname` esiste
  in `dbops.processi`.

---

### Note di migrazione

* 2026-09-11 — nasce col job pgAgent, il processo a catalogo e il tipo di lavoro
  (`brief-db-quattro-processi-senza-presidio` §10.2).
* 2026-10-14 — diventa `SECURITY DEFINER` con le altre procedure dei job
  (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — lo step chiama la procedura solo a sveglia accesa
  (`brief-db-processi-accensione-per-ambiente`).

---

{% include-markdown "signature-core.md" %}

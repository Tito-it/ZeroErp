## 📘 Documentazione Concettuale – Procedura `maintenance.proc_accoda_chiusura_scadenze_job`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale in cui resta la corsa della sveglia
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `chiusura_scadenze_daily`, attore della corsa
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — dove finiscono i lavori, uno per azienda
> * [dbops.automazione_chiusura_scadenze](/dbzero/dbops/tabelle/automazione_chiusura_scadenze) — le tabelle che il lavoro chiude per scadenza
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il panorama che confronta pgAgent col giornale
> * [dbops.vw_processi_roster](/dbzero/dbops/views/vw_processi_roster) — le aziende e le identità tecniche per cui si accoda
>
> Approfondimento funzioni:
>
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — esegue il lavoro e scrive la corsa
> * [maintenance.fn_sveglia_accesa](/dbzero/maintenance/funzioni/fn_sveglia_accesa) — il cancello dello step pgAgent
> * [dbops.fn_accoda_chiusura_scadenze](/dbzero/dbops/funzioni/fn_accoda_chiusura_scadenze) — il lavoro: accoda una chiusura per azienda
> * [dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze) — la chiusura vera, che esegue il drenatore

---

### 🎯 Scopo Principale

Il wrapper del job pgAgent `chiusura_scadenze_daily`: sveglia la chiusura per scadenza degli
stati gestionali chiamando `dbops.fn_accoda_chiusura_scadenze` attraverso il giornale dei job.

---

### pgAgent sveglia, la coda lavora

La chiusura per scadenza è un processo di dominio: tocca i dati delle aziende. Per questo non
gira dentro pgAgent, dove non avrebbe un'identità e un errore non arriverebbe a nessuno. pgAgent
la **sveglia**: `dbops.fn_accoda_chiusura_scadenze` mette in `dbops.coda_lavori` un lavoro
`CHIUSURA_SCADENZE` per ogni azienda, con l'identità tecnica di quell'azienda e il suo perimetro.
Il lavoro vero — `dbops.fn_apply_chiusura_scadenze` — lo esegue il drenatore della coda, minuti
dopo, dentro la RLS.

Questa procedura non decide niente: passa a `maintenance.fn_run_and_log` il codice del processo,
il nome dello step e la chiamata. Il resto — la riga nel giornale, il verbale del fallimento
scritto fuori transazione, l'errore rilanciato — lo descrive la scheda di
[fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log). Non passa una chiave di lock: la
protezione dalle sveglie doppie sta nella chiave idempotente dei lavori, non qui.

---

### ⭐ Senza il giornale la sveglia è invisibile

Il wrapper esiste perché per un periodo lo step del job chiamava la funzione direttamente. I
lavori venivano accodati, ma della sveglia non restava nessuna corsa: per il panorama dei processi
il job girava senza registrare, e nessun test poteva accorgersene, perché tutti guardavano la coda.
Passando dal giornale, la corsa ha un attore (il processo `chiusura_scadenze_daily`, che il giornale
trova dal codice passato come `p_jobname`) e un esito.

---

### Una sveglia ogni ora, un lavoro per giorno aziendale

Il job suona **ogni ora**, al minuto 5, anche se il nome dice «daily». Il giorno di una scadenza è
quello dell'azienda, non dell'orologio del server: con la sveglia oraria la prima corsa dopo la
mezzanotte dell'azienda accoda il lavoro, e le altre del giorno trovano il lavoro già fatto e
non accodano niente. La regola sta in `dbops.fn_accoda_chiusura_scadenze`.

Lo step chiama la procedura solo se `maintenance.fn_sveglia_accesa('chiusura_scadenze_daily')` è
vero. Il processo non è spegnibile: spento, gli stati per scadenza resterebbero aperti senza che
nessuno se ne accorga.

---

### ⚠️ Il riepilogo della sveglia non arriva nel giornale

`dbops.fn_accoda_chiusura_scadenze` non si ferma all'errore di un'azienda: lo conta e passa alla
successiva, e restituisce un riepilogo con accodati, falliti e saltati. `fn_run_and_log` però
esegue la chiamata senza conservarne il risultato: la corsa è registrata come riuscita anche
quando per un'azienda l'accodamento è fallito. Chi vuole sapere quali aziende sono rimaste
scoperte guarda la coda e `dbops.vw_emittenti_non_serviti`, non il giornale.

---

### Gira come il proprietario, e non in CI

La procedura è `SECURITY DEFINER` con `search_path` fisso, come tutte le `maintenance.proc_*_job`:
chiunque la chiami — pgAgent, una persona — la esegue con i diritti del proprietario. L'EXECUTE è
tolto a `PUBLIC`.

La convergenza dei job in CI non la chiama: il processo è operativo, agisce su dati e orologio, ed
è escluso dal giro di rilascio.

---

### Test

* `db/pgtap/dbops/test-vw-processi-programmazione.sql` — la regola del panorama che ha trovato il
  difetto: un job pgAgent senza corse nel giornale è nominato come uno che gira e non registra.
* `db/pgtap/maintenance/test-proc-job-definer-v1.sql` — la procedura è `SECURITY DEFINER`, col
  `search_path` fisso, del proprietario dello schema, senza EXECUTE a `PUBLIC` né all'applicazione.
* `db/pgtap/dbops/test-processi-jobname-wrapper.sql` — il codice passato come `p_jobname` esiste
  in `dbops.processi`.
* `db/pgtap/dbops/test-fn-accoda-chiusura-scadenze.sql` e
  `db/pgtap/dbops/test-chiusura-scadenze-una-volta-al-giorno-v1.sql` — il lavoro che la procedura
  sveglia.

---

### Note di migrazione

* 2026-09-05 — il job passa da esecutore a sveglia, e lo step perde il wrapper che lo registrava.
* 2026-09-06 — nasce questa procedura, e lo step torna a passare dal giornale.
* 2026-10-09 — la sveglia diventa oraria, il lavoro resta uno per giorno aziendale
  (`brief-be-db-fe-un-solo-fuso-aziendale`).
* 2026-10-14 — diventa `SECURITY DEFINER` con le altre procedure dei job
  (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — lo step chiama la procedura solo a sveglia accesa
  (`brief-db-processi-accensione-per-ambiente`).

---

{% include-markdown "signature-core.md" %}

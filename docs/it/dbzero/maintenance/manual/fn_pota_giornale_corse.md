## 📘 Documentazione Concettuale – Funzione `maintenance.fn_pota_giornale_corse`

> **Ultimo aggiornamento**: 23 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale che la funzione pota
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — `potatura_esclusione`, i processi le cui corse si tengono tutte
>
> Approfondimento viste:
>
> * [maintenance.vw_job_run_corsie](/dbzero/maintenance/views/vw_job_run_corsie) — le corsie, da cui la funzione parte
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — legge l'ultima corsa vera e l'ultima fallita di ogni corsia
> * [maintenance.vw_job_run_da_superuser](/dbzero/maintenance/views/vw_job_run_da_superuser) — legge l'ultima corsa col ruolo di ogni processo
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — legge l'ultima corsa, l'ultima di pgAgent e l'ultimo esito di ogni processo
>
> Approfondimento funzioni:
>
> * [maintenance.proc_pota_giornale_corse_job](/dbzero/maintenance/funzioni/proc_pota_giornale_corse_job) — il job che la chiama, con la soglia di 12 mesi

---

### 🎯 Scopo Principale

La ritenzione del giornale delle corse. Cancella le corse **chiuse** più vecchie della soglia,
tranne quelle che i lettori del giornale leggono ancora come «l'ultima», e tranne le corse dei
processi che dichiarano di volere tutta la loro storia. Restituisce l'esito
`{soglia, cancellate}`, che il giornale conserva nella riga della corsa che l'ha chiamata.

La soglia è un parametro: la ritenzione di 12 mesi la fissa il job. Con la soglia `NULL` la
funzione non fa niente (`STRICT`).

---

### Che cosa resta, a qualunque età

Una corsa vecchia resta se è una di queste, per la sua **coppia** processo e job:

| Resta | Perché, cioè chi la legge |
| --- | --- |
| l'ultima in assoluto | «mai partito» e l'ultima corsa del panorama dei processi; la liveness del backend |
| l'ultima conclusa e non saltata | l'ultima conclusa e l'esito della lista dei processi e del digest |
| l'ultima col ruolo registrato | il presidio dei superuser (`vw_job_run_da_superuser`) |
| l'ultima fallita | l'ultimo rosso di `vw_job_run_da_guardare`, con la sua causa |
| l'ultima di pgAgent | `GIRA_E_NON_REGISTRA` del panorama: pgAgent ha girato, il giornale lo sa? |
| ogni corsa aperta | non è storia chiusa: da appesa è proprio ciò che il presidio mostra |

Spesso sono la stessa riga, quindi per ogni coppia restano poche righe oltre la soglia.

⭐ **La chiave è la coppia, non il job.** I lettori cercano «l'ultima» per job, per processo, o
per «processo K oppure job K»: l'ultima di ciascuno di questi insiemi è l'ultima di una coppia.
Il solo nome del job non basta, perché nulla lega un job a un processo solo: l'ultima riga di un
job può essere di un altro processo, e allora la potatura toglierebbe l'ultima del primo.

⚠️ L'«ultima non saltata» non serve come voce a parte: o è aperta, e resta, o è l'ultima
conclusa.

---

### Chi non si pota

Un processo con `dbops.processi.potatura_esclusione` valorizzata tiene tutte le sue corse: il
testo dice perché. Oggi lo dichiarano le tre corsie della fatturazione, perché il pannello degli
esiti apre qualunque mese, anche di anni prima. Un processo nuovo con lo stesso bisogno si
dichiara nel seed dei processi, senza toccare la funzione.

---

### Come lavora

* Le coppie vengono da `maintenance.vw_job_run_corsie`, che le legge saltando nell'indice delle
  corsie da una coppia alla successiva; per ciascuna ogni voce della tabella qui sopra è una sola
  ricerca nell'indice. Il costo segue il numero delle coppie, non la storia.
* Le candidate si leggono dall'indice per data.
* È `SECURITY INVOKER`: cancella chi ne ha il diritto. L'applicazione non ha `DELETE` sul giornale
  e non ha `EXECUTE` sulla funzione; la chiama il job, che gira come proprietario.

ℹ️ Non è il framework di pulizia delle automazioni (`dbops.fn_run_automations_cleanup`). Quello dà
a ogni riga una scadenza alla nascita e cancella ciò che è scaduto, schema per schema. Qui una riga
vecchia resta se è «l'ultima» di qualcosa: la regola dipende dalle righe vicine, non dalla riga.

---

### Che cosa si perde, e chi lo vede

Oltre la soglia il giornale non è più la storia completa:

* gli elenchi delle corse (di tutto il giornale, di un processo) non arrivano oltre la soglia,
  salvo le righe che restano;
* i conteggi sulle corse contano gli ultimi 12 mesi, più le righe che restano;
* per una corsa appesa da più di un anno, `vw_job_run_da_guardare` conta i fallimenti dei sette
  giorni prima solo fra le righe che il giornale tiene. Il verdetto e la causa non cambiano;
* un lavoro di `dbops.coda_lavori` che puntava a una corsa cancellata resta, con `job_run_id`
  vuoto: lo azzera la FK `fk_coda_lavori_job_run_log` (`ON DELETE SET NULL`), nella stessa
  cancellazione. La funzione non lo fa da sé, e l'esito non lo conta.

---

### Test

* `db/pgtap/maintenance/test-pota-giornale-corse-v1.sql` — che cosa si cancella e che cosa resta,
  voce per voce; la coppia contro il solo job; la corsa recente che rende potabile la vecchia; il
  processo escluso; `STRICT`; la postura; il seed e il job.

---

### Note di migrazione

* 2026-11-22 — nasce, con la ritenzione di 12 mesi decisa da Tid
  (`brief-db-giornale-corse-indici` §7, §8). Prima il giornale non si potava, e cresceva per
  sempre.
* 2026-11-23 — le coppie vengono da `maintenance.vw_job_run_corsie`, la sede che legge anche
  `vw_job_run_da_guardare`; prima la discesa stava qui, in una CTE sua. Righe tenute e cancellate
  non cambiano.

---

{% include-markdown "signature-core.md" %}

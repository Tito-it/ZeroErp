## 📘 Documentazione Concettuale – Funzione `dbops.fn_accoda_chiusura_scadenze`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — dove finiscono i lavori, uno per azienda
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il processo `chiusura_scadenze_daily`, di classe `DOMINIO`
>
> Approfondimento viste:
>
> * [dbops.vw_processi_roster](/dbzero/dbops/views/vw_processi_roster) — le aziende e le identità tecniche per cui si accoda
> * [dbops.vw_emittenti_non_serviti](/dbzero/dbops/views/vw_emittenti_non_serviti) — le aziende che il roster non nomina
> * [dbops.vw_coda_lavori_da_guardare](/dbzero/dbops/views/vw_coda_lavori_da_guardare) — dove si vede un lavoro fallito o mai preso
>
> Approfondimento funzioni:
>
> * [dbops.fn_accoda_lavoro](/dbzero/dbops/funzioni/fn_accoda_lavoro) — la porta della coda, idempotente sui lavori vivi
> * [dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/funzioni/fn_apply_chiusura_scadenze) — la chiusura vera, che esegue il drenatore
> * [maintenance.proc_accoda_chiusura_scadenze_job](/dbzero/maintenance/funzioni/proc_accoda_chiusura_scadenze_job) — il wrapper del job pgAgent che la chiama
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — scrive la corsa e legge il riepilogo
>
> Guide:
>
> * [Processi automatici: classe e identità](/guide/processi-automatici-classe-e-identita) — la regola «pgAgent sveglia, la coda lavora»

---

### 🎯 Scopo Principale

**Sveglia** la chiusura per scadenza senza eseguirla: mette in coda un lavoro
`CHIUSURA_SCADENZE` per ogni azienda del roster del processo `chiusura_scadenze_daily`, ciascuno
con l'identità tecnica di quell'azienda, e restituisce un riepilogo.

Il lavoro vero lo fa il drenatore, minuti dopo, dentro la row level security e con un nome.

---

### ⭐ pgAgent sveglia, la coda lavora

La chiusura per scadenza è un processo di dominio: tocca i contratti e i listini delle aziende.
Dentro pgAgent non avrebbe un'identità, e un fallimento non arriverebbe a nessuno. Per questo
pgAgent chiama solo questa funzione (attraverso il wrapper
`maintenance.proc_accoda_chiusura_scadenze_job`), e ogni lavoro accodato porta:

* `run_as = OPERATORE`, non `SISTEMA`: lo pretende il guard di classe di `dbops.fn_accoda_lavoro`
  per un processo di dominio;
* nello scope, la terna dell'utente tecnico e l'emittente **congelato** all'accodamento
  (`emittente_attivo_id` e l'elenco con quel solo emittente). Senza, il drenatore girerebbe in
  modalità globale: un lavoro chiesto per A chiuderebbe anche le righe di B, senza che nessun
  errore lo dica;
* nel payload l'emittente, che serve solo a dire nell'esito per chi è girato il lavoro;
* `origine = CRON`.

Le aziende sono quelle che `dbops.vw_processi_roster` nomina per il processo, nell'ordine della
vista. Un'azienda senza identità tecnica attiva non è nel roster: qui non c'è niente da accodare,
e il riepilogo non la conta. La nomina `dbops.vw_emittenti_non_serviti`.

---

### ⚠️ Una volta per giorno aziendale

La sveglia suona ogni ora; il giorno di una scadenza è quello dell'azienda. La chiave del lavoro è
fatta di tipo, azienda e **giorno aziendale** (`script.fn_data_operativa()`), senza l'ora, letto una
volta sola per tutto il giro: la chiave e il controllo «già fatto» parlano dello stesso giorno.

* Un lavoro di oggi ancora vivo (`PENDING`, `IN_CORSO`): la chiave idempotente di
  `fn_accoda_lavoro` non ne crea un secondo e restituisce quello esistente.
* Un lavoro di oggi già `FATTO`: chiude il giorno, l'azienda si salta e si conta fra i saltati.
  Questo controllo sta qui perché la chiave di `fn_accoda_lavoro` protegge solo i lavori vivi.
* Un lavoro di oggi finito in `ERRORE` o `ANNULLATO` non chiude il giorno: la sveglia dopo
  riaccoda quell'azienda.

---

### ⭐ Un'azienda che fallisce non ferma le altre

L'accodamento di ogni azienda sta in un blocco suo: se fallisce, l'errore si conta, il messaggio
(accorciato) entra nel dettaglio, e si passa all'azienda successiva.

La funzione **restituisce un riepilogo** invece di sollevare: accodati, falliti, saltati, il
dettaglio per azienda (il lavoro accodato o l'errore) e l'istante del giro. Lo legge
`maintenance.fn_run_and_log`, che lo scrive nel giornale e, con almeno un fallito, chiude la corsa
**rossa** (`E_JOB_ESITO_CON_SCARTI`) senza annullare i lavori accodati per le altre aziende.

---

### Test

* `db/pgtap/dbops/test-fn-accoda-chiusura-scadenze.sql` — un lavoro per azienda del roster, come
  `OPERATORE`, con l'emittente congelato nello scope; una seconda sveglia a lavori vivi non
  raddoppia, la chiave non contiene l'ora; un guasto iniettato su una sola azienda lascia accodate
  le altre.
* `db/pgtap/dbops/test-chiusura-scadenze-una-volta-al-giorno-v1.sql` — la chiave porta il giorno
  aziendale; a lavori `FATTO` la sveglia dopo non accoda e li conta come saltati; un lavoro in
  `ERRORE` fa riaccodare solo la sua azienda.
* `db/pgtap/dbops/test-vw-processi-roster.sql` — il roster da cui la funzione legge.
* `db/pgtap/maintenance/test-fn-run-and-log-lock-ed-esito-v1.sql` — un riepilogo con falliti rende
  rossa la corsa e il lavoro fatto resta.

---

### Note di migrazione

* 2026-09-05 — nasce: il job notturno smette di chiudere le scadenze e le accoda, un'azienda alla
  volta (`brief-db-processi-automatici-identita-e-perimetro`).
* 2026-10-09 — la sveglia diventa oraria e il lavoro resta uno per giorno aziendale
  (`brief-be-db-fe-un-solo-fuso-aziendale`).
* 2026-11-03 — il riepilogo arriva nel giornale e un'azienda fallita rende rossa la corsa. Prima
  `fn_run_and_log` scartava il risultato, e la corsa risultava riuscita anche con accodamenti
  falliti (`brief-db-revisione-maintenance` D5).

---

{% include-markdown "signature-core.md" %}

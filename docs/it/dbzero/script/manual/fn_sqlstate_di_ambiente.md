## 📘 Documentazione Concettuale – Funzione `script.fn_sqlstate_di_ambiente`

> 👀 **Vedi anche**
>
• [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/manual/vw_job_run_da_guardare) — *la causa di ogni lavoro da guardare*
>
• [dbops.cause_fallimento](/dbzero/dbops/manual/cause_fallimento) — *le cause, e a chi tocca*

### 🎯 Scopo Principale
(latest review 16-10-2026)

Risponde a una domanda sola: **questo errore è un guasto dell'ambiente?** Cioè una
cosa che rimedia chi gestisce il server o il database, e non lo sviluppo.

| Codice (SQLSTATE) | Che cosa vuol dire |
| --- | --- |
| classe `08` | la connessione al database è caduta o è stata rifiutata |
| classe `53` | mancano risorse: spazio su disco, memoria, connessioni |
| classe `57` | un intervento dell'operatore: arresto, riavvio, cancellazione |
| classe `58` | un errore di sistema (file, I/O) |
| `42501` | a un ruolo manca un permesso: si rimedia col provisioning |
| `55P03` | una tabella era occupata da un'altra operazione oltre il tempo massimo |

⚠️ **Non** sono dell'ambiente le altre `42xxx` (oggetto inesistente, sintassi), le
violazioni di vincolo (`23xxx`), gli errori di dominio (`P0001`) e il deadlock
(`40P01`, due lavori che si contendono in un ordine sbagliato): sono programma.
Senza codice la risposta è no.

---

### ⭐ Perché una funzione

La stessa domanda la fanno:

* la vista [`maintenance.vw_job_run_da_guardare`](/dbzero/maintenance/manual/vw_job_run_da_guardare),
  per dare la causa `AMBIENTE` a un lavoro fallito;
* i gestori d'errore del framework delle automazioni (`dbops.fn_run_automations_*`,
  `dbops.fn_ensure_storico_table`). Quando la risposta è sì, scrivono l'errore nel
  registro col loro contesto e lo **rilanciano com'è**, invece di trasformarlo nel
  loro codice. Così il lavoro notturno arriva al giornale col motivo vero.

Una lista sola, perché dieci copie prima o poi risponderebbero in modi diversi.

---

### Verifica

`db/pgtap/dbops/test-automazioni-guasto-ambiente-rilanciato-v1.sql`: la tabella di
verità e la forma dei gestori. `db/pgtap/maintenance/test-vw-job-run-da-guardare-causa-v1.sql`:
la causa nella vista.

---

*Brief: `brief-db-presidio-job-run-a-chi-tocca.md` §10.*

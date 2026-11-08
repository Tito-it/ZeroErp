## 📘 Documentazione Concettuale – Vista `dbops.vw_processi_programmazione_da_guardare`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il catalogo dei processi
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale delle corse
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo in cui la vista è un presidio, con la causa come variante
> * [dbops.presidi_testi](/dbzero/dbops/tabelle/presidi_testi) — il testo per chi agisce, per ogni causa
> * [dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause) — a chi tocca ogni causa
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il panorama che questa vista proietta, con gli stati e le cause
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — il presidio delle corse che falliscono
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Presidio: i processi automatici la cui sveglia e la cui ultima corsa non tornano. È il panorama dei
processi ristretto alle righe da guardare, ognuna con la sua causa. Deve restare vuota.

---

### ⭐ Due oggetti, due mestieri

Il panorama [vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) elenca
anche i sani, e serve: senza sapere quanti sono i sani, un guasto sembra la norma.

⛔ Ma proprio per questo il panorama non può stare nel pannello dei presidi. Quel pannello ha un
patto: ciò che ci compare o deve restare vuoto, o è un debito che deve calare. Mettergli davanti le
righe verdi insegnerebbe a leggere il verde come un problema, cioè a saltare l'avviso.

⇒ Uno per capire, uno per accorgersi.

---

### ⛔ Il criterio del guasto è scritto in un posto solo

Questa vista **non decide** che cosa sia un guasto: prende le righe del panorama con `da_guardare`
vero, cioè quelle che hanno una causa. Se ripetesse qui un elenco di stati sani, il vocabolario
degli stati sarebbe scritto due volte, e il giorno in cui ne nasce uno nuovo qualcuno dovrebbe
ricordarsi di venire a decidere da che parte cade. La divergenza non darebbe nessun errore:
cambierebbe soltanto ciò che il presidio smette di mostrare.

Restano fuori, quindi, gli stati senza causa: `OK`, `IN_ATTESA`, `SPENTO`, `FUORI_PORTATA` e
`SU_RICHIESTA`. Gli ultimi due non sono guasti per ragioni opposte: un limite di vista del database
(un `COMMAND` senza contratto lo presidia il backend) e la natura del processo (un `CODA` lo sveglia
una persona).

---

### ⭐ La causa sceglie il testo e il destinatario

Ogni riga porta la sua `causa`, mai vuota: lo stesso stato può avere rimedi diversi. `MUTO` è un
timer fermo o un servizio caduto; `MAI_PARTITO` è un timer mai installato o un job pgAgent mai
partito. Nel catalogo dei presidi la causa è la colonna variante: sceglie il testo che il pannello
e il digest mostrano e, attraverso `dbops.presidi_cause`, a chi mandarlo. L'elenco completo degli
stati e delle cause sta nel panorama.

⭐ Lo stato che vale più di tutti è `GIRA_E_NON_REGISTRA`: lo scheduler dice che il job è girato, il
giornale non lo sa. È la firma di un lavoro che muore prima di riuscire a raccontarlo.

---

### ⭐ Le colonne sono la prova del verdetto

La riga porta le date che servono a contestare il verdetto:

| Colonna | Che cosa dice |
| --- | --- |
| `pgagent_ultima_corsa` | quando lo scheduler l'ha fatto partire |
| `giornale_ultima_corsa_pgagent` | quando il giornale ha registrato una corsa dello scheduler: il verdetto poggia su questa |
| `giornale_ultima_corsa` | quando il giornale ha registrato una corsa qualunque: il contesto |

⛔ Un presidio che mostra due date e ne usa una terza consegna un verdetto che chi guarda non può
contestare: vedrebbe due orari coerenti e una riga rossa. ⭐ E se la corsa qualunque è più recente
di quella dello scheduler, qualcuno ha registrato sotto questo nome senza essere lo scheduler.

Le righe sono ordinate per canale e processo.

---

### ⚠️ Una causa non accertata, da cui ricominciare

Per sei mesi e mezzo un lavoro settimanale di manutenzione è girato senza lasciare una riga nel
giornale; la corsa forzata del giorno in cui la vista è nata è andata verde. Il lavoro quindi non
era rotto: si era rotto il modo in cui raccontava di aver lavorato. Ma una corsa riuscita non spiega
perché tante corse riuscite non abbiano scritto niente, e da qui non si accerta: lo storico degli
esiti dello scheduler sta in pgAgent, che l'applicazione non legge.

⇒ Non è una condizione di riapertura: è il punto da cui cominciare la prossima volta che questo
giornale tace.

---

### Chi la guarda

Nel catalogo dei presidi è un presidio che deve restare vuoto, guardato ogni giorno, con la causa
come variante. La vista gira coi privilegi del proprietario, e l'applicazione la legge.

---

### Test

* `db/pgtap/dbops/test-vw-processi-programmazione-da-guardare.sql` — ha un commento (il pannello ci
  legge la natura del presidio); non contiene mai uno stato sano, e nomina un guasto costruito;
  presidio e panorama non possono dissentire; l'applicazione la legge; la riga porta la data su cui
  poggia il verdetto.
* `db/pgtap/dbops/test-presidio-processi-testo-per-causa-v1.sql` — nessuna riga senza causa; ogni
  causa costruita esce col suo stato e ha il suo testo.

---

### Note di migrazione

* 2026-09-07 — nasce, su richiesta del backend (`brief-db-sveglia-dei-processi`). Nacque con due
  righe: un lavoro notturno che aveva appena ricevuto la capacità di registrarsi, e che ha
  registrato alla corsa dopo; e un lavoro settimanale che dal 21 febbraio 2026 girava senza lasciare
  traccia, uscito con la corsa forzata del 7 settembre. A sera era vuota.
* 2026-10-09 — nasce la colonna `causa` (`brief-db-presidio-processi-testo-per-causa`).

---

{% include-markdown "signature-core.md" %}

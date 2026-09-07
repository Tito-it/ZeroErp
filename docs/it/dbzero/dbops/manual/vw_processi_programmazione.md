## 📘 Documentazione Concettuale – View `dbops.vw_processi_programmazione`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.processi](/dbzero/dbops/manual/processi)
>
[maintenance.job_run_log](/dbzero/maintenance/manual/job_run_log)
>
Approfondimenti viste:
>
[dbops.vw_processi_programmazione_da_guardare](/dbzero/dbops/manual/vw_processi_programmazione_da_guardare)

---
### 🎯 Scopo Principale
(latest review 07-09-2026)

È il **panorama** dei lavori che il sistema fa da solo: per ognuno, chi dovrebbe
svegliarlo, quando girerà, e quando ha girato davvero.

Risponde a una domanda che prima non aveva risposta scritta da nessuna parte:

> **Questo lavoro sta ancora girando?**

⭐ E la risposta non viene da una fonte sola: viene dal **confronto** fra due.
Lo scheduler del database dice *quando* ha fatto partire un lavoro; il giornale
delle corse dice *che cosa quel lavoro ha fatto*. Finché le due si somigliano,
va bene. Quando si smentiscono, è successo qualcosa che nessuno ha raccontato.

---

### ⭐ La colonna che vale più di tutte è `stato`

E il valore che conta è **«è girato e non l'ha detto»**: lo scheduler dichiara di
aver fatto partire il lavoro, il giornale non ne sa niente.

È la firma esatta di un lavoro che muore **prima** di riuscire a raccontarlo. Non
è un caso di scuola: un lavoro settimanale di manutenzione è morto ogni settimana
per **sei mesi**, con l'ultimo verdetto agli atti a «fatto», e lo si è scoperto
per caso. Questo confronto lo avrebbe trovato in un giorno.

| stato | che cosa vuol dire |
| --- | --- |
| `OK` | lo scheduler lo sveglia e il giornale lo registra |
| `GIRA_E_NON_REGISTRA` | ⛔ girato secondo lo scheduler, mai arrivato al giornale |
| `MAI_PARTITO` | programmato, acceso, e non è mai partito |
| `JOB_SPENTO` | il lavoro esiste ma qualcuno l'ha disattivato |
| `JOB_ASSENTE` | il catalogo dichiara un lavoro che lo scheduler non ha |
| `NON_PROGRAMMATO` | nessuno ha dichiarato chi lo sveglia |
| `FUORI_PORTATA` | la sveglia vive fuori dal database |
| `SU_RICHIESTA` | lo sveglia una persona: una cadenza non esiste |

---

### ⚠️ Due stati non sono guasti, e per ragioni **opposte**

È la distinzione entrata il 2026-09-07, e serve perché prima quei due casi
stavano sotto la stessa parola — facendo contare insieme cose diverse.

| | Che cosa vuol dire | Perché non è un guasto |
| --- | --- | --- |
| **`FUORI_PORTATA`** | il lavoro lo fa partire il sistema operativo | è un limite di **vista**: il database non può saperlo. Chi può saperlo è il backend, che dal 2026-09-06 lo presidia da `backend/deploy/sveglie.json` |
| **`SU_RICHIESTA`** | il lavoro lo mette in coda una **persona** | non esiste nessuna cadenza da confrontare: è la **natura** del lavoro, e non cambierà |

Il primo è un confine che un giorno si potrebbe spostare; il secondo no.

⛔ **Dire «tutto bene» su un lavoro che non si vede sarebbe una bugia**, ed è il
modo più efficace di far smettere di guardare. La vista si ferma dove deve.

⚠️ **Un caso resta fra i `FUORI_PORTATA` di proposito**: il listener sempre
acceso, che scrive una sola corsa — quella di avvio. Presidiarne la vitalità
sull'ultima corsa direbbe «fermo» su un servizio sano acceso da tre settimane.
Ma **che sia un listener il database non lo sa**: nessuna colonna lo dice, e
dedurlo dal nome sarebbe una coincidenza travestita da regola. ⇒ Se servirà, è
una colonna — cioè un pezzo di modello, non un ramo in più.

---

### ⭐ `da_guardare`: il criterio del guasto sta in un posto solo

La vista porta una colonna che dice, per ogni riga, **se quello stato è un
guasto**. Non è una comodità: è la sede unica di quel criterio.

⛔ La vista di presidio ([vw_processi_programmazione_da_guardare](/dbzero/dbops/manual/vw_processi_programmazione_da_guardare))
la **proietta** invece di ripetere un elenco di stati sani. Se lo ripetesse, il
vocabolario degli stati sarebbe scritto in **due** posti, e il giorno in cui ne
nasce uno nuovo qualcuno dovrebbe *ricordarsi* di andare a decidere da che parte
cade. ⚠️ Un allineamento affidato alla memoria è quello che manca per primo, e
mancherebbe senza dare nessun errore: cambierebbe soltanto ciò che il presidio
smette di mostrare.

⇒ Chi aggiunge uno stato passa di qui, e lì deve decidere. **Non c'è un
comportamento predefinito in cui cadere per distrazione.**

---

### ⚠️ Due cose da sapere leggendo la vista

* **Il legame col lavoro dello scheduler non è il nome.** Si legge da una
  colonna dichiarata (`dbops.processi.jobname_pgagent`), perché due lavori su
  quattordici si chiamano diversamente dal processo che registrano.
* **Il giornale si legge in due modi**, per processo *oppure* per nome del
  lavoro: le corse storiche non hanno il processo valorizzato, e senza il
  ripiego ogni lavoro sembrerebbe non aver mai girato prima di settembre 2026.

---

### ⭐ È un panorama, non un presidio

Elenca **anche i sani**, ed è voluto: senza sapere quanti sono i sani, un guasto
sembra la norma. È la tabella che si apre per capire, non la lista delle cose da
fare — quella è la vista di presidio, e sta apposta da un'altra parte.

---

### Verifica

`db/pgtap/dbops/test-vw-processi-programmazione.sql` — fra i dieci test, quello
che conta costruisce il caso «è girato e non l'ha detto» togliendo le righe di
giornale di un lavoro sano, e gli ultimi due tengono legati due vocabolari che
vivono in posti diversi: i canali ammessi dal vincolo di tabella e i rami che la
vista dichiara. Un canale nuovo senza verdetto fa rosso il test, invece di
produrre un falso allarme in produzione.

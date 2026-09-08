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

### ⛔ Le date del giornale sono **due**, e il confronto usa la seconda

Dal 2026-09-07 la vista porta due date di giornale, e la differenza fra loro non
è un dettaglio.

| | Che cosa dice |
| --- | --- |
| `giornale_ultima_corsa` | l'ultima corsa registrata sotto questo lavoro, **chiunque** l'abbia scritta |
| `giornale_ultima_corsa_pgagent` | l'ultima corsa che può valere come **risposta dello scheduler** |

La domanda del confronto è **«la sveglia dello scheduler ha lasciato
traccia?»**. Una corsa scritta da qualcun altro — un comando lanciato a mano, un
programma del backend che registra sotto lo stesso nome — non è una risposta a
quella domanda: parla di un altro fatto. ⛔ Ma prima **contava lo stesso**, e
spostando avanti la data spegneva l'allarme proprio sul lavoro che si stava
sorvegliando.

⚠️ **Non era un'ipotesi.** Il 2026-09-07 un lavoro di amministrazione risultava
«ultima corsa alle 11:11» per via di **sei righe lasciate da una prova**, mentre
lo scheduler l'aveva fatto partire alle 06:00. Su un lavoro *giornaliero* un
equivoco così rientra da solo il giorno dopo; su uno *settimanale* — cioè
esattamente sul lavoro che ha reso famoso questo difetto — copre l'intera
settimana.

⭐ **Le due date restano entrambe, e sono due apposta.** Quella piena serve ai
lavori che lo scheduler non sveglia affatto: per loro è l'unica informazione
utile della riga, e filtrarla la svuoterebbe. E quando le due **divergono**,
quella divergenza è essa stessa un'informazione: vuol dire che qualcuno ha
registrato sotto questo nome senza essere lo scheduler.

⚠️ **Il limite, detto qui e non scoperto dopo.** Chi ha scritto una corsa si
legge da una colonna il cui valore *predefinito* è «lo scheduler»: chi registra
senza dichiararsi finisce lì dentro. ⇒ Il confronto distingue il backend, che si
dichiara sempre, e **non** distingue lo scheduler da un lavoro lanciato a mano
dalla console del database. È meno di quanto sembri, ed è molto più di niente.

⚠️ E l'esito dell'ultima corsa (`ultimo_esito`) **non** è filtrato: è contesto,
non la prova del verdetto. Le corse andate male hanno un presidio loro
([maintenance.vw_job_run_da_guardare](/dbzero/maintenance/manual/vw_job_run_da_guardare)).

---

### ⭐ È un panorama, non un presidio

Elenca **anche i sani**, ed è voluto: senza sapere quanti sono i sani, un guasto
sembra la norma. È la tabella che si apre per capire, non la lista delle cose da
fare — quella è la vista di presidio, e sta apposta da un'altra parte.

---

### Verifica

`db/pgtap/dbops/test-vw-processi-programmazione.sql` — tredici test.

Quelli che contano **costruiscono** il caso invece di cercarlo fra i dati di
oggi: si toglie il giornale a un lavoro e si pretende «è girato e non l'ha
detto»; gli si rimette una corsa dello scheduler e si pretende che torni sano;
gli si rimette una corsa di **qualcun altro** e si pretende che l'allarme
**resti acceso**.

⚠️ Il lavoro su cui si costruisce si sceglie sulla **struttura** — canale
dichiarato, sveglia accesa, almeno una partenza dello scheduler — e non sul
verdetto che la vista dà oggi. Sceglierlo sul verdetto era il difetto corretto
il 2026-09-07: bastava una rottura che eliminasse tutti i lavori sani perché il
file non trovasse nessun soggetto e **smettesse di verificare senza diventare
rosso**.

Gli ultimi due tengono legati due vocabolari che vivono in posti diversi: i
canali ammessi dal vincolo di tabella e i rami che la vista dichiara, e —
allo stesso modo — i modi in cui una corsa può essere stata registrata e quali
di essi valgono come risposta dello scheduler. Un valore nuovo senza verdetto fa
rosso il test, invece di produrre un falso allarme in produzione.

## 📘 Documentazione Concettuale – View `dbops.vw_processi_programmazione_da_guardare`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.processi](/dbzero/dbops/manual/processi)
>
[maintenance.job_run_log](/dbzero/maintenance/manual/job_run_log)

---
### 🎯 Scopo Principale
(latest review 07-09-2026)

Elenca i lavori automatici la cui **sveglia** e la cui **ultima corsa** non
tornano. Deve restare vuota.

Sono due fonti che raccontano lo stesso fatto: lo scheduler del database dice
*quando* ha fatto partire un lavoro, e il giornale delle corse dice *che cosa
quel lavoro ha fatto*. Finché si somigliano, tutto bene. Quando si smentiscono,
qualcosa è successo e nessuno l'ha raccontato.

---

### ⭐ Perché è una vista a parte, e non un filtro sull'elenco completo

L'elenco completo — il **panorama** — c'è, e serve: mostra *tutti* i lavori
automatici, anche quelli che stanno andando bene. Senza sapere quanti sono i
sani, un guasto sembra la norma.

⛔ Ma proprio per questo il panorama **non può stare nel pannello dei presidi**.
Quel pannello ha un patto: ciò che ci compare o deve restare vuoto, o è un elenco
di debiti che deve calare. Mettergli davanti dodici righe verdi insegnerebbe a
leggere il verde come un problema — cioè a saltare l'avviso. È il modo più
efficace di spegnere un presidio senza spegnerlo.

⇒ Due oggetti, due mestieri: uno per capire, uno per accorgersi.

---

### ⛔ Il criterio del guasto è scritto in un posto solo

Questa vista **non decide** che cosa sia un guasto: lo chiede al panorama, che
porta una colonna apposta (`da_guardare`), calcolata accanto al punto in cui gli
stati vengono decisi.

⚠️ Sembra un dettaglio e non lo è. Se il criterio fosse riscritto anche qui —
*«prendi tutti gli stati tranne questi tre»* — ci sarebbero **due elenchi** degli
stati possibili. Il giorno in cui ne nasce uno nuovo, qualcuno dovrebbe
*ricordarsi* di venire ad aggiornare anche il secondo; e la divergenza non
darebbe nessun errore, cambierebbe soltanto ciò che il presidio smette di
mostrare.

⇒ Chi aggiunge uno stato passa da un punto solo, e lì deve decidere se è un
guasto. Non c'è un comportamento predefinito in cui cadere per distrazione.

Dal 2026-10-09 ogni riga porta anche la sua **causa** (ultima colonna), che
sceglie il testo per chi deve agire: lo stesso stato può avere rimedi diversi —
un timer fermo non si ripara come un servizio scollegato. Elenco delle cause in
[vw_processi_programmazione](/dbzero/dbops/manual/vw_processi_programmazione).

---

### ⚠️ Due situazioni non sono guasti, e per ragioni opposte

| | Che cosa vuol dire | Perché non è un guasto |
| --- | --- | --- |
| **fuori portata** | il lavoro lo fa partire il sistema operativo, non il database | è un limite di **vista**: il database non può saperlo, e chi può saperlo — il backend — lo controlla per conto suo |
| **su richiesta** | il lavoro lo mette in coda una **persona** | non esiste nessuna cadenza da confrontare: è la **natura** del lavoro, e non cambierà |

⭐ Tenerle sotto la stessa parola faceva contare insieme cose diverse. La prima è
un confine che un giorno si potrebbe spostare; la seconda no.

⚠️ Dire «tutto bene» su un lavoro che non si vede sarebbe una bugia
rassicurante, ed è il modo più rapido per far smettere di guardare.

---

### ⭐ Lo stato che conta di più

**«È girato e non l'ha detto.»** Lo scheduler dichiara di aver fatto partire il
lavoro; il giornale non ne sa niente.

È la firma esatta di un lavoro che muore *prima* di riuscire a raccontarlo — e
non è un caso di scuola: un lavoro settimanale di manutenzione è morto ogni
settimana per **sei mesi**, con l'ultimo verdetto agli atti a «fatto», e lo si è
scoperto per caso.

---

### ✅ Al 7 settembre 2026, a fine giornata, questa vista è vuota

Ci ha messo poche ore, e le due righe con cui è nata se ne sono andate per
strade diverse — vale la pena tenerle distinte, perché solo una delle due è una
risposta.

* un lavoro **notturno** che aveva appena ricevuto la capacità di registrarsi:
  ha registrato alla corsa successiva, e la riga è sparita da sé. Atteso;
* ⛔ un lavoro **settimanale** che quella capacità ce l'aveva già, e che dal
  febbraio 2026 girava senza lasciare traccia. Quello non si sarebbe tolto da
  solo: la corsa è stata **forzata** il 7 settembre, e ha lasciato una traccia.

**Che cosa dice quella traccia, e che cosa no.** È **verde**: quindi il lavoro
non era rotto, e ciò che si era rotto era il modo in cui raccontava di aver
lavorato. ⚠️ Ma una corsa riuscita oggi non spiega **perché** sei mesi di corse
riuscite non abbiano scritto niente: quella domanda si risponde solo guardando
lo storico dello scheduler, che da qui non si legge.

⇒ Il sintomo è sparito, la causa non è accertata. Sono due cose diverse, e la
seconda va tenuta scritta: la prossima volta che questo giornale tace, si
comincia da lì.

✅ **Il commento della vista è stato riallineato lo stesso giorno**: portava il
fatto datato *«questa vista NASCE con due righe»* — una riga che dichiarava la
propria scadenza — ed è quello che il pannello dei presidi mostra. Lasciarlo
avrebbe detto a chi guarda di aspettarsi due righe che non ci sono più, cioè
avrebbe insegnato a non fidarsi del numero. ⚠️ Al suo posto resta scritta la
causa non accertata: non è una condizione di riapertura, è il punto da cui
ricominciare la prossima volta che quel giornale tace.

---

### ⭐ Le colonne sono la **prova** del verdetto, non un ornamento

La riga porta tre date, e servono a essere lette insieme.

| | Che cosa dice |
| --- | --- |
| quando lo scheduler l'ha fatto partire | la prima fonte |
| quando il giornale ha registrato **una corsa dello scheduler** | la seconda fonte, ed è quella su cui poggia il verdetto |
| quando il giornale ha registrato una corsa **qualunque** | il contesto |

⛔ Un presidio che mostra due date e ne usa una terza consegna un verdetto che
chi guarda **non può contestare**: vedrebbe due orari coerenti e una riga rossa.
Per questo la data su cui il confronto poggia davvero è esposta.

⭐ E la terza serve a leggere il caso storto: se la corsa «qualunque» è più
recente di quella dello scheduler, **qualcuno ha registrato sotto questo nome
senza essere lo scheduler**. Dettaglio in
[vw_processi_programmazione](/dbzero/dbops/manual/vw_processi_programmazione).

---

### Verifica

`db/pgtap/dbops/test-vw-processi-programmazione-da-guardare.sql` — costruisce un
lavoro guasto e pretende che la vista lo nomini, verifica che nessuna situazione
sana ci entri, confronta la vista col panorama per impedire che qui rispunti un
criterio suo, e pretende che le tre date della prova siano tutte nella riga.
⚠️ Quest'ultimo serve perché il difetto sarebbe **muto**: le colonne le sceglie
chi scrive la vista, e toglierne una non dà nessun errore.

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

### 🔴 Al 7 settembre 2026 questa vista non è vuota

E non è un difetto della vista: è la prima cosa che ha da dire.

* un lavoro notturno che ha appena ricevuto la capacità di registrarsi:
  registrerà alla prossima corsa, e la riga sparisce da sé;
* ⛔ un lavoro settimanale che **quella capacità ce l'aveva già**, e che dal
  febbraio 2026 gira senza lasciare traccia. Quello non si toglie da solo: la
  prima corsa utile per capirlo è **sabato 12 settembre 2026**, e ciò che ci si
  aspetta è una traccia — verde o rossa, ma una.

---

### Verifica

`db/pgtap/dbops/test-vw-processi-programmazione-da-guardare.sql` — costruisce un
lavoro guasto e pretende che la vista lo nomini, verifica che nessuna situazione
sana ci entri, e confronta la vista col panorama per impedire che qui rispunti un
criterio suo.

## 📘 Documentazione Concettuale – Funzione `dbops.fn_conta_presidio_per_variante`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.presidi](/dbzero/dbops/manual/presidi) — *il catalogo da cui questa funzione legge tutto*
> • [dbops.presidi_cause](/dbzero/dbops/manual/presidi_cause) — *le cause, e a chi tocca ciascuna*
>
**Approfondimento funzioni:**
>
• [dbops.fn_conta_presidio](/dbzero/dbops/manual/fn_conta_presidio) — *il conteggio intero, che è la somma di questo*
>
**Approfondimento guide:**
>
• [Presidi e registri del debito](/guide/presidi-e-registri-del-debito)
>

### 🎯 Scopo Principale
(latest review 10-10-2026)

Dice **quante righe di una vista di controllo chiedono un intervento, per
ciascuna causa**.

Alcuni controlli raccolgono guasti **diversi** nella stessa vista: il presidio
dei processi automatici, per esempio, mette insieme un timer fermo, un servizio
scollegato e un lavoro del database mai partito. Ogni causa ha il suo rimedio e
spesso una persona diversa che deve intervenire. Il catalogo dice da quale
colonna della vista si legge la causa (`colonna_variante` di
[`dbops.presidi`](/dbzero/dbops/manual/presidi)), e questa funzione conta le
righe di ciascuna.

---

### Perché serve un conteggio per causa

Il pannello e il messaggio di posta mostrano **un campione** delle righe, non
tutte. Contare le cause sul campione darebbe numeri sbagliati appena le righe
sono più del campione, e una causa che tocca allo sviluppo, finita oltre la
quinta riga, non arriverebbe mai a chi deve intervenire.

Il conteggio quindi lo fa il database, sulla vista intera.

---

### Che cosa restituisce

Una riga per ciascuna causa **presente**, con quante righe la portano:

* le cause che in questo momento non hanno righe **non compaiono**;
* le righe senza causa formano un gruppo a sé, con la causa vuota: non spariscono
  dal conteggio e non si confondono con un'altra causa;
* per un controllo che **non** distingue le cause esce una riga sola, con la causa
  vuota e il totale — anche quando il totale è zero. Così chi legge ha un modo
  solo di chiedere, per qualunque controllo.

Le righe che contano sono le stesse di sempre: tutta la vista, oppure, se il
catalogo dichiara uno stato atteso, quelle **diverse** da quello stato (vedi
[`dbops.fn_conta_presidio`](/dbzero/dbops/manual/fn_conta_presidio), *Che cosa
conta, esattamente*).

---

### ⭐ È l'unico posto in cui si conta

Il perimetro (solo le viste a catalogo, attive e non ritirate; le altre si
rifiutano, non si contano a zero) e il filtro sullo stato atteso sono scritti
**qui e solo qui**. Il conteggio intero,
[`dbops.fn_conta_presidio`](/dbzero/dbops/manual/fn_conta_presidio), è la somma
dei gruppi di questa funzione.

Così le due risposte non possono mai essere diverse: non perché qualcuno si
ricordi di tenerle allineate, ma perché la regola è scritta una volta sola.

---

### Sicurezza

Come il conteggio intero, la funzione gira con i permessi del **proprietario**
delle tabelle, perché alcune viste di controllo, lette da un programma senza un
utente in sessione, risponderebbero zero per cecità (il difetto è spiegato in
[`dbops.fn_conta_presidio`](/dbzero/dbops/manual/fn_conta_presidio)).

E gli stessi due limiti la rendono sicura:

* **torna numeri, mai le righe.** Il nome della causa che esce è un codice del
  catalogo delle cause, non un dato di un cliente o di un documento;
* **conta solo ciò che è a catalogo**, e rifiuta tutto il resto.

---

*Brief: `docs/it/dev/work-in-progress/brief-db-presidio-processi-testo-per-causa.md` §6.2 (R-2).*

## 📘 Documentazione Concettuale – Funzione `vendite.fn_riporta_lotto_a_draft`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids)  
> • [vendite.fn_annulla_lotto_da_draft](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft)  
> • [vendite.fn_elimina_fattura_da_lotto](/dbzero/vendite/funzioni/fn_elimina_fattura_da_lotto)  

---

### 🎯 Scopo Principale
(latest review 03-08-2026)  

La funzione **`vendite.fn_riporta_lotto_a_draft()`** riporta **in bozza** un lotto
già lavorato, perché l'operatore possa correggere qualcosa a monte e **rifare il
giro**. È il pezzo mancante del disegno *«EMESSA = documento non modificabile;
per correggere si riporta a DRAFT e si ricalcola»*: fino al 03-08-2026 la matrice
degli stati ammetteva il ritorno, ma **nessuna funzione lo eseguiva**.

**È un rollback, non una riapertura.** Le fatture del lotto non vengono
"riaperte": vengono **cancellate**, e il rilancio della pipeline le rigenera dai
dati corretti. Il lotto invece **resta vivo** e riparte dal suo primo passo — ed è
questa la differenza con la sorella
[`fn_annulla_lotto_da_draft`](/dbzero/vendite/funzioni/fn_annulla_lotto_da_draft),
che invece **chiude** il lotto portandolo ad ANNULLATA.

---

### Perché le fatture si cancellano invece di riaprirsi

Due ragioni, entrambe misurate:

* la generazione delle righe è **solo inserimento**, non riscrive quelle esistenti:
  lasciare in piedi le righe vecchie le farebbe **duplicare** al rilancio;
* il difetto tipico sta **nella chiave** della fattura. Il termine di pagamento,
  per esempio, concorre a decidere *quante fatture nascono*: corretto il termine,
  il rilancio calcola una chiave diversa e produce una fattura **diversa** — la
  testata vecchia resterebbe lì, vuota e senza padrone.

Effetto collaterale gradito: le segnalazioni critiche se ne vanno insieme alle
fatture, quindi il lotto riaperto riparte senza doverle disattivare una per una.

---

### Si torna indietro per qualsiasi motivo

Che il lotto contenga fatture **in errore** o fatture **semplicemente da
correggere** non fa differenza: chi opera sa perché lo riporta indietro, e il
database deve solo permetterlo. Quindi **nessun controllo sul motivo**.

Ciò che resta vietato non è riaprire un lotto, ma **numerare un documento
incoerente** — e quel presidio vive altrove, nella funzione che assegna il numero.

---

### Regole principali

* Ammessa su lotti **MASSIVO** e **GIORNALIERO**.
* Ammessa se il lotto è in stato **DRAFT** o **EMESSA** (documento non ancora
  fiscale). Oltre c'è la numerazione, e da lì non si torna.
* Tutte le fatture del lotto devono essere in **DRAFT** o **EMESSA**.
* ⚠️ **Rifiuta se anche una sola fattura ha già un numero.** Il controllo guarda
  il **numero** e non lo stato: cancellare un documento numerato aprirebbe un
  buco irreparabile nella numerazione fiscale, e un presidio che si fida di
  un'implicazione cade il giorno in cui l'implicazione cambia.
* ⚠️ **Non contiene nessuna riga di pulizia.** Il ripristino — fatture, righe,
  riepiloghi IVA, note, segnalazioni, collegamento al lotto, saldo
  d'arrotondamento, fondi, `attivita_fatturabili` **e** `commesse_attivita` —
  è tutto di
  [`fn_cleanup_fatture_by_ids`](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids),
  che ne è il **proprietario unico**.
  Questa funzione decide **cosa** si riporta indietro e **in che stato lascia il
  lotto**; il **come si ripulisce** non le appartiene. È la divisione che rende
  sicuro aggiungere un livello domani: si tocca **un punto solo** e le tre
  operazioni che chiamano la primitiva lo ereditano.
* Il lotto viene marcato:
  * `stato_doc_fiscale = DRAFT`
  * `stato_operativo = APERTO` (ha di nuovo lavoro da fare)
  * `riaperto_il = now()`
* ⚠️ **`stato_lotto` non viene toccato**, di proposito: da COMPLETATO come da
  ERRORE l'unica transizione ammessa è verso IN_ESECUZIONE, che è esattamente
  quello che farà il giro successivo.
* ⚠️ **Le esecuzioni dei task (`fatturazione_lotti_task_runs`) non vengono
  toccate.** Sono un registro storico di cosa è stato eseguito, non una macchina
  di stato: nessuno le consulta per decidere se rifare un passo, e cancellarle
  distruggerebbe traccia utile senza sbloccare nulla.

---

### A cosa serve `riaperto_il`

A distinguere **«riaperto»** da **«rotto»**.

Chi rilancia il lavoro deve sapere se deve **rifare** il primo passo o se può
saltare avanti. L'unico segnale disponibile prima era *«il lotto è andato in
errore»* — che su un lotto riaperto di proposito sarebbe **falso**, e lo farebbe
comparire in rosso fra i lotti falliti nei cruscotti.

È una **data** e non un interruttore, per la stessa ragione per cui altrove si usa
una data di obsolescenza invece di un flag: si spiega da sola, si ordina, e non
chiede a nessuno di ricordarsi di spegnerla.

⚠️ **Va però riportata a vuoto quando il lotto avanza** oltre la bozza, altrimenti
il lotto rifarebbe lo stesso passo per sempre. Lo spegnimento non è compito di
questa funzione.

---

### Output

Ritorna una riga con **cinque** contatori, tenuti separati di proposito: un numero
unico direbbe «dieci cose fatte» senza distinguere fatture cancellate da attività
rimesse in coda, che per chi guarda il cruscotto sono fatti diversi.

* `updated_lotti`
* `updated_attivita` — attività fatturabili sbloccate
* `deleted_fatture`
* `deleted_righe`
* `riemesse_attivita` — attività di commessa tornate emittibili

---

### Esempio d'uso

```sql
SELECT *
FROM vendite.fn_riporta_lotto_a_draft(
  p_lotto_id => 1200
);
```

---

{% include-markdown "signature-core.md" %}

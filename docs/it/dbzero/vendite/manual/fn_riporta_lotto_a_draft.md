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
(latest review 31-08-2026)  

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
* 🔴 **Le esecuzioni dei task (`fatturazione_lotti_task_runs`) vengono chiuse ad
  `ANNULLATO`** — tutte quelle attive del lotto, non solo quelle dello step
  DRAFT. È il passo **RD-6**, ed è indispensabile:
  [`fn_resolve_lotto_task_execution_mode`](/dbzero/vendite/funzioni/fn_resolve_lotto_task_execution_mode)
  legge l'**ultimo** task_run per (lotto, task, stato_doc) e su `COMPLETATO`
  risponde `SKIP`. Senza questo passo **il lotto riaperto rilancia a vuoto**: i
  task vengono saltati tutti, in silenzio — nessun errore, nessun task_run
  nuovo, e il giro *sembra* riuscito.
  * ⚠️ **Non si cancellano: si chiudono con un esito**, tramite
    `fn_cancel_lotto_task_run` con motivo `ritorno_a_draft`. Il giro nuovo apre
    `tentativo = MAX+1`, quindi la storia resta leggibile per intero — che è la
    ragione per cui «registro storico» resta vero anche dopo il passaggio.
  * ⚠️ **Non basterebbe `attivo = false`**: quella SELECT non filtra su
    `attivo`. La leva è l'**esito**.

> 📌 **Rettifica del 31-08-2026 — questo punto diceva l'opposto, e lo motivava
> con un fatto confutato.** Fino a oggi la scheda affermava *«le esecuzioni dei
> task non vengono toccate … nessuno le consulta per decidere se rifare un
> passo»*, sulla base di una misura del 03-08-2026. Il changeSet **`20260803-12`**,
> dello **stesso giorno**, introduceva il passo RD-6 proprio perché qualcuno le
> consulta — `fn_resolve_lotto_task_execution_mode`. Non era una descrizione
> incompleta: era una scelta spiegata con una premessa falsa, e chi leggeva
> imparava una cosa sbagliata sul motore dell'esecuzione.

* 🔴 **L'atto viene REGISTRATO nel giornale** (RD-7, dal 31-08-2026): una riga
  `LOTTO_RIAPERTO` in `vendite.event_log`, scritta con
  [`fn_log_event`](/dbzero/vendite/funzioni/fn_log_event), severity **WARN**, e
  nel `payload` lo stato fiscale di partenza più i cinque contatori.
  Prima di allora la riapertura si leggeva **solo di rimbalzo**, dai task_run
  passati ad `ANNULLATO`: l'unico atto della funzione che **cancella documenti**
  era anche l'unico senza una riga propria.

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

### Perché la riapertura si scrive in `event_log` e non fra le segnalazioni

Il giornale del lotto ([`script.vw_giornale_entita`](/dbzero/script/views/vw_giornale_entita))
unisce quattro registri, e due potevano ospitare questa riga. Non sono
equivalenti, e la differenza non è di gusto:

| | `vendite.fatturazione_lotti_log` | `vendite.event_log` |
| --- | --- | --- |
| Si può spegnere una riga? | **sì**, ha `disabilitato` | no |
| Si può modificarla? | sì | **no**, append-only per trigger |
| Come la si cerca? | dal testo del messaggio | dal **codice**, che è a catalogo |
| Alimenta le segnalazioni? | **sì** | no |

Le prime tre righe dicono la stessa cosa: un atto che **cancella documenti** non
deve poter essere silenziato, riscritto, o ritrovato solo indovinando come era
stata scritta la frase.

⭐ **Ma è la quarta a decidere, ed è di comportamento, non di leggibilità.** Le
segnalazioni del lotto si compongono da `fatture_log` unito a
`fatturazione_lotti_log`; da `event_log` si legge soltanto l'ancora del giro
corrente (`PIPELINE_STARTED`). Scrivere la riapertura nel registro delle
segnalazioni l'avrebbe fatta entrare nel conteggio su cui si decide se
l'avanzamento è ammesso: **un atto registrato sarebbe diventato un atto che
blocca**. In `event_log` la riga si legge e non condiziona nulla.

#### Perché WARN e non INFO

La **conseguenza** dell'atto è già `WARN` nel giornale — il giornale mappa un
task_run `ANNULLATO` a `WARN`, e la riapertura ne produce uno per ogni step.
Se la **causa** restasse `INFO`, chi filtra per gravità vedrebbe otto corse
annullate e non il motivo per cui lo sono: la gravità sarebbe invertita fra
effetto e causa. Qui `severity` non risponde a *«si è rotto qualcosa»* ma a
*«quanto deve saltare all'occhio di chi indaga»*.

#### Perché la riga non può far fallire la riapertura

È la domanda giusta da farsi davanti a una scrittura aggiunta in coda a
un'operazione che oggi riesce. Il giornale rifiuta una riga **solo** quando non
sa dire di chi è — e qui lo sa sempre, per costruzione: `LOTTO` è un tipo
giornalabile a catalogo, il perimetro si copia da
`fatturazione_lotti.emittente_soggetto_ruolo_id` che è **NOT NULL**, e che il
lotto esista è già garantito dalle precondizioni. Non è una scommessa sui dati
di oggi: è una proprietà dello schema.

---

### Output

Ritorna una riga con **sei** contatori, tenuti separati di proposito: un numero
unico direbbe «dieci cose fatte» senza distinguere fatture cancellate da attività
rimesse in coda, che per chi guarda il cruscotto sono fatti diversi.

* `updated_lotti`
* `updated_attivita` — attività fatturabili sbloccate
* `deleted_fatture`
* `deleted_righe`
* `riemesse_attivita` — attività di commessa tornate emittibili
* `annullati_task_run` — esecuzioni di task chiuse ad `ANNULLATO` (RD-6)

⭐ **Cinque di questi sei finiscono anche nel `payload` della riga di giornale**,
insieme allo stato fiscale da cui il lotto è tornato (`stato_precedente`).
Resta fuori `updated_lotti`, che vale sempre 1 e non direbbe niente. È la
ragione per cui quella riga vale: *«riaperto»* si deduce già dai task_run
`ANNULLATO`, *«riaperto, e ha cancellato N fatture e M righe»* no — e chi
indaga a mesi di distanza non ha altro modo di saperlo.

> 📌 **Rettifica del 31-08-2026**: la scheda diceva «cinque» ed elencava i primi
> cinque. `annullati_task_run` è nella firma dal changeSet `20260803-12`, lo
> stesso che ha introdotto il passo RD-6 — mancava qui, non nella funzione.

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

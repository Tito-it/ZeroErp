## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_titoli_iva_movimenti`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — il titolo di cui è il registro
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — il documento che consuma o restituisce
>
> Approfondimento viste:
>
> * [anagrafiche.vw_stiva_movimenti_dettaglio](/dbzero/anagrafiche/views/vw_stiva_movimenti_dettaglio) — le righe del registro col motivo di blocco dell'annullo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_consuma_plafond_titolo_iva_righe](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva_righe) — chi scrive i movimenti di fattura
> * [anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore](/dbzero/anagrafiche/funzioni/trgfn_soggetti_titoli_iva_movimenti_accumulatore) — chi tiene la somma
> * [anagrafiche.fn_annulla_movimento_titolo_iva](/dbzero/anagrafiche/funzioni/fn_annulla_movimento_titolo_iva) — l'annullo di una forzatura
> * [script.fn_check_annullo_movimento_titolo_iva](/dbzero/script/funzioni/fn_check_annullo_movimento_titolo_iva) — quando una forzatura si può annullare
> * [anagrafiche.trgfn_stiva_movimenti_guard_annullo](/dbzero/anagrafiche/funzioni/trgfn_stiva_movimenti_guard_annullo) — il presidio della riga di annullo
> * [script.fn_check_fatture_con_plafond_consumato](/dbzero/script/funzioni/fn_check_fatture_con_plafond_consumato) — la fattura che ha consumato non si disfa

---

### 🎯 Scopo Principale

`anagrafiche.soggetti_titoli_iva_movimenti` è il registro del plafond: quanto tetto di un titolo IVA è stato usato,
un movimento alla volta. `anagrafiche.soggetti_titoli_iva.imponibile_utilizzato` è la somma di queste righe, e
nessuno la scrive a mano.

---

### Tre tipi di movimento

| Movimento | Segno | Da dove |
| --- | --- | --- |
| `FATTURA` | positivo o negativo | una riga di fattura sotto il titolo: positiva consuma, negativa (uno sconto, un componente di kit negativo) restituisce |
| `NOTA_CREDITO` | negativo | la nota di credito restituisce |
| `FORZATURA` | positivo o negativo | l'operatore, col motivo |

Il plafond si consuma sul **netto** della fattura: la riga negativa scrive il suo movimento col suo segno, e resta
di tipo `FATTURA` perché il tipo dice quale documento l'ha prodotto. La fattura non restituisce mai più di quanto
essa stessa consuma, quindi la sua somma resta fra zero e la capienza. Lo zero non è un movimento.

---

### ⭐ Perché un registro e non una colonna

Il consumato doveva essere memorizzato e correggibile a mano, per le fatturazioni fuori dal sistema, e la nota di
credito doveva restituirlo. Un numero memorizzato e forzabile a mano diverge in silenzio da ciò che rappresenta; su
un plafond è il numero che l'Agenzia delle Entrate verifica.

Col registro la forzatura ha un motivo, un autore e una data; il consumo è algebrico, senza casi speciali per la
nota di credito; la riconciliazione col fatturato è una lettura, non un'indagine.

---

### La forma di ogni riga

* **Una forzatura non nomina nessuna fattura**, gli altri due tipi sì: esiste per registrare ciò che il sistema non
  ha fatturato. Senza, «forzatura» sarebbe la scorciatoia per scrivere un consumo di fattura saltando la funzione
  che lo calcola, la sola che prende il lock.
* **La forzatura ha un motivo**, e uno spazio non è un motivo.
* **La riga di fattura** si nomina solo insieme alla sua fattura.
* **La data è obbligatoria e non ha default**: la porta chi scrive, la data documento della fattura o quella che
  l'operatore dichiara. Un lotto di fatturazione può girare il giorno dopo, e un registro fiscale datato con
  l'orologio del lotto racconterebbe il giorno sbagliato.
* **Lo stesso documento non consuma due volte lo stesso titolo**: un'unicità su titolo, tipo, fattura e riga, sui
  soli movimenti che nominano una fattura. È la rete sotto il lock e sotto l'idempotenza della funzione di consumo,
  che rilegge i movimenti invece di riscriverli. Due forzature identiche invece sono ammesse: possono essere due
  fatti distinti.

Ogni movimento richiede un titolo attivo alla conferma dell'operazione (`E_ATTIVO_PADRE_NON_ATTIVO`).

---

### ⛔ Il registro è solo aggiunte

Una riga scritta non si modifica e non si cancella: `UPDATE` e `DELETE` sono rifiutati con
`E_TITOLO_IVA_MOVIMENTO_IMMUTABILE`. Si vietano tutte e due, e la metà che sembra meno grave è la peggiore: un
`UPDATE` riscrive la storia in silenzio, perché l'accumulatore ricalcola e il totale resta «giusto».

Ne seguono tre cose:

* dell'accumulatore gira solo il ramo dell'inserimento;
* **un titolo con movimenti non si spegne e non si cancella**: la disattivazione è rifiutata
  (`E_ATTIVO_BLOCK_CHILDREN_EXIST`) e la cancellazione la ferma la chiave esterna. Per farlo finire si chiude la sua
  data di fine;
* **una fattura che ha consumato plafond non si disfa**: le porte che riportano una fattura a bozza, annullano un
  lotto o la eliminano la fermano con `E_FATTURE_PLAFOND_CONSUMATO` (`script.fn_check_fatture_con_plafond_consumato`).

---

### ⭐ Una forzatura sbagliata si annulla con una riga in più

Una forzatura sbagliata non si cancella e non si spegne: si scrive una seconda `FORZATURA` di segno opposto,
collegata alla prima da `annulla_movimento_id`.

* La scrive `anagrafiche.fn_annulla_movimento_titolo_iva`: chi chiama dice quale riga e perché, importo e titolo
  li deriva il database.
* Se si può lo decide `script.fn_check_annullo_movimento_titolo_iva`, la stessa che spegne il pulsante in
  `anagrafiche.vw_stiva_movimenti_dettaglio`.
* La riga di annullo la presidia `anagrafiche.trgfn_stiva_movimenti_guard_annullo`: stesso titolo, importo
  esattamente opposto.

Una riga e non un flag, perché il registro resta solo aggiunte; perché l'accumulatore somma senza filtri e il
contro-movimento riporta il consumato al valore giusto da sé; perché la data dell'annullo (quando qualcuno si è
accorto dell'errore) è un'informazione; perché si vedono l'errore e la correzione, ognuno col suo motivo.

Un movimento si annulla una volta sola (unicità sul collegamento), non annulla sé stesso (un controllo sulla
riga), e un annullo non si annulla: se la forzatura serve di nuovo se ne scrive una nuova. Il collegamento non si
svuota mai da solo: la chiave esterna non ha azioni sulla cancellazione.

Un annullo si può rifiutare anche per un motivo che sorprende: se nel frattempo le note di credito hanno superato
le fatture, togliere la forzatura porterebbe la somma sotto zero (`PLAFOND_NEGATIVO`). Il motivo spegne il
pulsante, così l'operatore lo scopre guardando e non premendo.

---

### Il conto non va sotto zero, e il tetto non si controlla qui

L'accumulatore rifiuta una somma negativa (`E_TITOLO_IVA_UTILIZZATO_NEGATIVO`): nessuna lettura del dominio la
ammette.

Il superamento del tetto invece non si blocca. Sulle fatture non si presenta, perché la funzione di consumo
spezza le righe sulla capienza; sulle forzature è un'informazione sul mondo: se le fatturazioni fuori sistema
sfondano il plafond, è il plafond registrato a essere sbagliato, e impedire di scriverlo impedirebbe di
accorgersene.

---

### Chi li vede

La tabella ha la RLS, e la eredita dal titolo: una sessione con ruolo applicativo `OPERATORE` vede e scrive i
movimenti dei titoli presentati a un emittente del suo perimetro; le sessioni degli altri ruoli applicativi non ne
vedono nessuno. I controlli dell'annullo che devono rileggere un movimento fuori perimetro (la check e il guard)
girano coi privilegi del proprietario.

---

### ⚠️ Che cosa oggi non copre

* **Il titolo di un movimento di fattura non si confronta con la fattura.** Nessun controllo verifica che il titolo
  sia del cliente e dell'emittente della fattura che il movimento nomina: lo garantisce chi chiama la funzione di
  consumo, che l'ha avuto dal risolutore.
* **I movimenti di nota di credito non li scrive il database.** Nessuna funzione del database li calcola, e nessun
  controllo impedisce a una nota di credito di restituire più di quanto la fattura rettificata aveva consumato:
  il limite è solo il conto che non va sotto zero.
* **Un titolo sfondato non lo segnala nessuno.** Il superamento del tetto con le forzature è ammesso apposta, ma non
  esiste una lista dei titoli sfondati che qualcuno guardi.

---

### Codici errore

* `E_TITOLO_IVA_MOVIMENTO_IMMUTABILE` — una modifica o una cancellazione di un movimento.
* `E_TITOLO_IVA_UTILIZZATO_NEGATIVO` — la somma del registro scenderebbe sotto zero.
* `E_TITOLO_IVA_ANNULLO_NON_AMMESSO`, `E_TITOLO_IVA_ANNULLO_INCOERENTE` — una riga di annullo non ammessa o
  incoerente.
* `E_ATTIVO_PADRE_NON_ATTIVO` — un movimento su un titolo spento, alla conferma.

I controlli sulla forma della riga (tipo, segno, fattura, motivo, auto-annullo) rispondono con l'errore del
vincolo.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` — il registro che alimenta l'accumulatore, la nota di credito
  che restituisce, la somma sotto zero, la forzatura senza motivo o con una fattura.
* `db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql` — l'annullo e i suoi rifiuti, `UPDATE` e `DELETE` sul
  registro rifiutati.
* `db/pgtap/vendite/test-reset-fattura-plafond-consumato-v1.sql` — la fattura che ha consumato plafond fermata dalle
  tre porte e dalla pulizia col codice, invece che da un errore grezzo della chiave esterna.

---

### Note di migrazione

* 2026-08-29 — nasce col titolo.
* 2026-08-31 — il registro diventa solo aggiunte, e nasce l'annullo col contro-movimento. Prima la regola era una
  promessa del backend, senza nulla nel database che la imponesse.
* 2026-10-04 — un movimento `FATTURA` può essere negativo: il plafond si consuma sul netto della fattura. Lo stesso
  giorno si decide che una fattura che ha consumato plafond non si disfa.

---

{% include-markdown "signature-core.md" %}

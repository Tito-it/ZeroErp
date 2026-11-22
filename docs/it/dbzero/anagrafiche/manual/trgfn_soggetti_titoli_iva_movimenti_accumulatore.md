## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro su cui è montata
> * [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva) — il titolo di cui scrive il consumato
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_consuma_plafond_titolo_iva_righe](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva_righe) — chi scrive i movimenti di fattura, i positivi prima dei negativi
> * [anagrafiche.fn_annulla_movimento_titolo_iva](/dbzero/anagrafiche/funzioni/fn_annulla_movimento_titolo_iva) — il contro-movimento, che questo trigger somma come gli altri

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_titoli_iva_movimenti_accumulatore` riporta il consumato del titolo
(`imponibile_utilizzato`) alla somma del registro dei movimenti, dopo ogni scrittura sul registro, e rifiuta una
somma sotto zero. È ciò che rende vero il consumato memorizzato: nessuno lo scrive a mano.

---

### ⭐ Ricalcola dalla somma, non aggiunge un delta

A ogni movimento scritto rilegge la somma dei movimenti del titolo e la scrive sul titolo, se è cambiata. Un
accumulatore che aggiunge l'importo a quello che c'è va fuori sincrono al primo caso imprevisto; il ricalcolo non
ha casi: qualunque cosa succeda al registro, la colonna dice ciò che il registro dice. Una correzione è una riga
nuova (il contro-movimento di un annullo) e si somma come le altre, senza filtri.

Il registro è solo aggiunte, quindi del trigger gira solo il ramo dell'inserimento. Gli altri due (la modifica e
la cancellazione, che ricalcolano anche il titolo abbandonato quando un movimento cambia titolo) restano come
difesa, nel caso il divieto venisse spento: in quel caso il consumato continuerebbe a dire la verità.

---

### ⛔ Il conto sotto zero si rifiuta qui

Una somma negativa è rifiutata con `E_TITOLO_IVA_UTILIZZATO_NEGATIVO`, col tipo del titolo e l'importo. Il caso
arriva da una nota di credito più grande del consumato o da una forzatura negativa sbagliata. Non è un controllo
sulla colonna perché la colonna la scrive questo trigger, dentro una scrittura su un'altra tabella: un errore di
vincolo lì sarebbe muto per chi scrive il movimento.

Il controllo vale a ogni riga scritta: per questo la funzione di consumo scrive prima i movimenti positivi di una
fattura e poi i negativi.

---

### ⛔ Il tetto non si controlla qui, ed è una decisione

Sulle fatture il superamento non si presenta: la funzione di consumo spezza le righe sulla capienza, sotto un lock
sul titolo. Sulle forzature è un'informazione: se le fatturazioni fuori sistema sfondano il plafond, è il plafond
registrato a essere sbagliato, e impedire di scriverlo impedirebbe di accorgersene.

---

### ⚠️ Che cosa oggi non copre

* **Il consumato si può scrivere a mano.** Nessun controllo impedisce un aggiornamento diretto di
  `imponibile_utilizzato` sul titolo: il valore scritto resta finché il prossimo movimento non lo riporta alla
  somma.
* **Un titolo sfondato non lo segnala nessuno**: il superamento del tetto con le forzature è ammesso, ma non esiste
  una lista dei titoli sfondati che qualcuno guardi.

---

### Codici errore

* `E_TITOLO_IVA_UTILIZZATO_NEGATIVO` — la somma del registro scenderebbe sotto zero.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-titoli-iva.sql` — il registro che alimenta il consumato, la nota di credito che
  lo restituisce, la somma sotto zero rifiutata.
* `db/pgtap/anagrafiche/test-stiva-movimenti-annullo-v1.sql` — il contro-movimento che riporta il consumato al
  valore precedente.

---

### Note di migrazione

* 2026-08-31 — il registro diventa solo aggiunte: i rami della modifica e della cancellazione smettono di essere
  raggiungibili. Il COMMENT della funzione cita ancora `fn_consuma_plafond_titolo_iva`, la forma a una riga
  ritirata il 2026-10-04.

---

{% include-markdown "signature-core.md" %}

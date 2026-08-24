## 📘 Documentazione Concettuale – Funzione `pagamenti.trgfn_vendite_contabili_righe_guard_stato_dati`

### 🎯 Scopo Principale
(rev 2026-08-21)

Una riga contabile in uno stato che **pretende l'abbinamento** deve dire a quale
**fattura** e a quale **cliente** appartiene: sono i due dati da cui nasce il
movimento contabile. Senza, si registrerebbe un incasso che non si sa a chi
attribuire.

⭐ È la metà **«bagaglio»** della regola di cui le transizioni sono la metà
**«percorso»**: la matrice dice *quando* si può passare, questo dice *a quali
condizioni sui dati*.

### Regole applicate
* Quali stati lo pretendano **non è scritto qui**: lo dice la bandiera
  `richiede_abbinamento` del catalogo `vendite_contabili_righe_stati` (vera su
  `ABBINATA` e `POSTATA`). Stessa scelta del guard di transizione, per la stessa
  ragione — una regola in una tabella si legge e si cambia senza toccare il codice.
* ⚠️ **Non era derivabile dalle bandiere che c'erano già**: `ABBINATA` pretende
  l'abbinamento e **non è finale**, quindi una condizione costruita su `is_final`
  l'avrebbe mancata del tutto.
* Il messaggio dice **che cosa manca** in italiano («la fattura», «il cliente», «la
  fattura e il cliente») e mette nel contesto il **campo** da evidenziare.

### ⚠️ La rata resta fuori, ed è una decisione
Su `ABBINATA` la scadenza è **facoltativa**: la riga del fondo fattura ha fattura
sì e rata no, perché è un saldo per **trasferimento** e non denaro arrivato su una
scadenza.

⭐ Per questo il guard è stato scritto **una volta sola**, con la nullità già
prevista: quando arriverà la colonna della rata **non va toccato**. Chi lo
rileggerà allora non deve credere che manchi un pezzo.

### Quando si attiva
* `BEFORE INSERT OR UPDATE` su `pagamenti.vendite_contabili_righe`.
* ⚠️ Anche sull'**INSERT**, a differenza del guard di transizione: una riga che
  nasce già abbinata senza fattura sarebbe sbagliata dal primo istante.

### ⚠️ Error handling
* `E_RIGA_CONTABILE_ABBINAMENTO_INCOMPLETO` (`DATO_ERRATO`, 400): il rimedio è
  compilare un campo, e il contesto porta la chiave `campo` perché l'interfaccia
  possa evidenziarlo.
* **Distinto** da `E_RIGA_CONTABILE_SENZA_ABBINAMENTO`, che scatta molto più tardi
  nel trigger di mirror del movimento: lì è un conflitto di stato perché la riga è
  già arrivata dov'è, qui è l'operatore che la sta muovendo adesso.

{% include-markdown "signature-core.md" %}

## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_conferma_sistemazione`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.sistemazioni](/dbzero/pagamenti/tabelle/sistemazioni) — l'atto che la funzione esegue
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la distinta che nasce da un rimborso o da una compensazione
> * [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — il fondo che nasce da un riporto
>
> Approfondimento viste:
>
> * [pagamenti.vw_eccedenze_da_sistemare](/dbzero/pagamenti/views/vw_eccedenze_da_sistemare) — l'elenco da cui la decisione è partita, con la stessa regola dell'eccedenza
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) — il saldo del documento di partenza, letto al momento della conferma
> * [pagamenti.fn_get_or_create_vendite_contabile](/dbzero/pagamenti/funzioni/fn_get_or_create_vendite_contabile) — la funzione che qui di proposito **non** si usa
> * [pagamenti.fn_annulla_sistemazione](/dbzero/pagamenti/funzioni/fn_annulla_sistemazione) — il verbo gemello, che scarta l'atto

---

### 🎯 Scopo Principale

La funzione madre che esegue un atto di sistemazione in `BOZZA`: sceglie la strada secondo la destinazione, genera il documento che mette in moto il denaro e porta l'atto a `CONFERMATA`.

⭐ **Non inventa nessuna macchina.** Le tre esistevano già tutte:

| Destinazione | Che cosa produce |
| --- | --- |
| `RIPORTO` | un **fondo fattura** `origine = MANUALE`, già `ASSEGNATO` alla fattura di destinazione |
| `RIMBORSO` | una **distinta a importi negativi**: il denaro non ha versi, ha segni |
| `COMPENSAZIONE` | una **distinta sul centro dedicato**, con due righe che sommano a zero |

Ritorna l'esito (fondo creato, distinta di rimborso creata, distinta di compensazione creata)
con la chiave del documento generato.

---

### ⭐ Perché è una madre

Scrive **in più posti** (la distinta, le sue righe o il fondo, l'atto) e o riescono tutte o non
ne resta nessuna. Sta nel database e non nel backend perché è tutto SQL: nessuna orchestrazione
attorno a più chiamate, **l'atomicità è dentro**.

L'atto si blocca in scrittura per primo: due conferme in parallelo creerebbero due documenti
per la stessa decisione. Un atto inesistente e uno fuori perimetro danno lo stesso rifiuto, di
proposito: distinguerli direbbe a chi è fuori perimetro che l'atto esiste.

---

### 🔴 Il controllo dell'eccedenza sta qui, non alla registrazione

Fra il momento in cui una persona **decide** e quello in cui **conferma** può arrivare un altro
incasso, o un'altra sistemazione può aver consumato lo stesso credito.

⚠️ Verificare alla registrazione avrebbe dato una garanzia **che scade**: si controlla al
gesto **irreversibile**, non a quello reversibile. L'eccedenza è la stessa della vista: il saldo del
documento ha cambiato segno rispetto al totale, e l'importo dell'atto, in valore assoluto, non
può superarla.

---

### ⭐ Il segno si ricava dal saldo, e non si scrive due volte

La riga sul documento di partenza vale l'importo dell'atto col **segno del saldo**:

| Il documento | Residuo | Riga generata |
| --- | --- | --- |
| fattura sovra-incassata | negativo | **negativa**: il denaro esce |
| nota di credito sovra-rimborsata | positivo | **positiva**: il denaro rientra |

⚠️ Nessun ramo su «è una fattura o una nota»: la formula **non nomina né l'una né l'altra**. Un
ramo sul tipo di documento è il punto in cui, prima o poi, si dimentica un caso.

⭐ Nella compensazione la seconda riga, sul documento di destinazione, è **l'opposto esatto**
della prima: due righe che sommano a zero, che è letteralmente che cosa vuol dire compensare.

---

### ⭐ Ogni atto ha la sua distinta

`fn_get_or_create_vendite_contabile` è costruita per **condividere**: due rimborsi sullo stesso
canale nello stesso giorno riuserebbero la stessa testata, e il secondo atto sbatterebbe
sull'unicità «una distinta per atto» con un `23505` muto. La distinta di una sistemazione
è **il documento di quell'atto**, quindi si crea diretta.

* Nasce in `BOZZA`, generata, alla data operativa, con le righe già `ABBINATA` alle fatture;
  le righe portano un riferimento che nomina l'atto e il lato (`SIS_<id>_ORIGINE`,
  `SIS_<id>_DESTINAZIONE`).
* Il codice della distinta non si compone qui: lo assegna il trigger di numerazione sul
  registro delle distinte dell'**emittente dell'atto**, come per ogni altra distinta. L'atto si
  ritrova dalla distinta attraverso `sistemazioni.contabile_id`.
* ⚠️ Distinta e righe si scrivono in **due istruzioni separate**: padre e figlio nella stessa
  CTE non passano sotto la row security, perché il padre non è ancora visibile al controllo di
  scrittura del figlio.

---

### Il rimborso: il canale è un parametro

La scelta di **da quale conto esce il bonifico** è una decisione del momento in cui si paga, non di quando
si decide di pagare: per questo il canale è un parametro della conferma e non una colonna
dell'atto. ⛔ Obbligatorio sul `RIMBORSO`, ignorato sulle altre due destinazioni. Il centro
della distinta è quello del canale; per la compensazione è il centro dedicato.

---

### Il riporto: un fondo già assegnato

* Il fondo usa il tipo `F_F_ADD_ACC`, l'unico generico a catalogo, e nasce **`ASSEGNATO`**: il
  riporto nomina già la fattura di destinazione, e un fondo `DISPONIBILE` sarebbe un credito
  che aspetta una decisione **già presa**. Il motivo del fondo è quello dell'atto.
* ⚠️ Il riporto pretende sul documento di partenza tre dati che su `vendite.fatture` sono
  facoltativi e sul fondo sono obbligatori (servizio, tipo documento, valuta): il controllo è
  qui, con un messaggio che dice **quale dato** manca. Un `23502` direbbe solo il nome della
  colonna.

---

### Codici errore

* `E_SISTEMAZIONE_NON_TROVATA` — l'atto non esiste o è fuori perimetro.
* `E_SISTEMAZIONE_NON_CONFERMABILE` — l'atto non è in `BOZZA`.
* `E_SISTEMAZIONE_ECCEDENZA_INSUFFICIENTE` — al momento della conferma il documento di partenza
  non ha più l'eccedenza che l'atto vuole sistemare.
* `E_SISTEMAZIONE_RIPORTO_NON_POSSIBILE` — riporto da un documento senza servizio, tipo
  documento o valuta.
* `E_CONTABILE_DATI_OBBLIGATORI` — rimborso confermato senza il canale di uscita.
* `E_CONFIG_MANCANTE` — manca a catalogo il tipo di fondo `F_F_ADD_ACC`, il centro della
  distinta non si risolve, oppure mancano gli stati contabili `BOZZA` e `ABBINATA`.
* i codici dei guard sulla distinta, sulle sue righe, sul fondo e sull'atto, se uno di questi
  rifiuta la scrittura.

---

### Test

* `db/pgtap/pagamenti/test-sistemazioni-giro-completo.sql` — il rimborso senza canale
  rifiutato e con il canale eseguito, il segno della riga sulla fattura sovra-incassata, la
  riconferma rifiutata, le due righe a somma zero della compensazione, l'eccedenza
  insufficiente rifiutata alla conferma.
* `db/pgtap/pagamenti/test-distinta-numerazione-registro-v1.sql` — i test 12 e 13: la funzione è
  una delle tre madri che scrivono distinte, e nessuna passa il codice.
* `db/pgtap/pagamenti/test-sistemazione-annullo-riporto.sql` — il riporto confermato crea il
  suo fondo, e il fondo nasce `ASSEGNATO`.
* `db/pgtap/rls/test-rls-fondi-fattura-source-functional.sql` — la policy dei fondi resta
  scrivibile in perimetro, cioè il riporto può ancora creare il suo fondo.

---

### Note di migrazione

* 2026-08-22 — nasce con il registro `sistemazioni`. La distinta portava un codice composto qui,
  `SIS_<id>_<timestamp>`.
* 2026-09-15 — il codice della distinta lo assegna il trigger di numerazione sul registro
  dell'emittente dell'atto; le distinte numerate
  prima conservano il loro codice.

---

{% include-markdown "signature-core.md" %}

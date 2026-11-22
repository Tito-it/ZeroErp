### 📋 La copia di un indirizzo

> **Ultimo aggiornamento**: 22 novembre 2026

Copiare un indirizzo vuol dire scrivere **lo stesso indirizzo sotto altri tipi**: «la sede legale è anche
spedizione, fatturazione e posta». È un gesto del drawer degli indirizzi, «Copia come…», sulla card di una riga:
l'operatore sceglie uno o più tipi, e nascono tante righe nuove quanti sono i tipi, tutte o nessuna.

#### Tre verbi, secondo da dove e verso dove

La riga nuova nasce sempre sulla **chiave del drawer**, cioè su ciò che l'operatore ha aperto: il soggetto, il
ruolo, o un servizio (un'istanza) del ruolo. La sorgente può stare altrove.

| Sorgente | Destinazione | Verbo |
| --- | --- | --- |
| un indirizzo del soggetto | il soggetto stesso | `anagrafiche.fn_copia_indirizzo_soggetto` |
| un indirizzo del ruolo, del ruolo o di una sua istanza | il ruolo o una sua istanza | `anagrafiche.fn_copia_indirizzo_ruolo` |
| un indirizzo del soggetto del ruolo | il ruolo o una sua istanza | `anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo` |

Nella cascata del drawer aperto su un ruolo, le righe del soggetto si copiano quindi **sul ruolo**, non sul
soggetto: la destinazione è sempre la chiave aperta. Per copiare su un'altra chiave si apre quella. La copia dal
ruolo al soggetto non c'è.

Per i due verbi verso il ruolo la destinazione è un parametro **obbligatorio**: l'istanza, oppure niente per il
ruolo stesso. Non ha un valore predefinito, perché un default sceglierebbe al posto dell'operatore.

#### Che cosa si copia e che cosa resta legato

La riga nuova porta l'indirizzo della sorgente, e nient'altro:

* un indirizzo **normalizzato** si copia come riferimento allo **stesso dettaglio**: il civico non si duplica, e
  le due righe restano legate a lui. Ciò che cambia il dettaglio (per esempio una fusione dello stradario) vale per
  tutte e due;
* un indirizzo **libero** si copia campo per campo (testo, stato, comune e CAP, oppure località, codice postale,
  regione e sotto-località): dopo la copia le due righe sono indipendenti, e la modifica di una non tocca l'altra;
* non si copiano la geolocalizzazione, l'audit, l'identificativo di transazione né il flag dello storico: sono
  quelli della riga nuova.

L'elemento si ricostruisce dalla riga con `anagrafiche.fn_indirizzo_elemento_da_riga`, e la riga nuova la scrive la
**madre singolare** del suo livello (`anagrafiche.fn_crea_indirizzo_soggetto` o `anagrafiche.fn_crea_indirizzo_ruolo`).
Non c'è una seconda scrittura: la copia passa dagli stessi controlli di «Aggiungi», con gli stessi codici.

#### I rifiuti

* **La sorgente non è della chiave giusta**: un indirizzo che non è del soggetto (`E_INDIRIZZO_SOGGETTO_NON_TROVATO`)
  o del ruolo indicato (`E_INDIRIZZO_RUOLO_NON_TROVATO`). Per il verbo dal soggetto al ruolo, la sorgente deve essere
  del soggetto del ruolo.
* **Il tipo chiesto**: lo giudica la singolare sulla **destinazione**. Un tipo che la destinazione ha già si
  rifiuta anche se la sorgente non ce l'ha, e un tipo che la sorgente ha già si copia se manca sulla destinazione.
  Un tipo ripetuto nell'elenco è un tipo già presente al secondo giro. Si rifiutano anche il tipo che non esiste, quello
  che il tipo di ruolo non ammette e quello che la natura del soggetto non ammette.
* **L'istanza di un altro soggetto** come destinazione la rifiuta il guard della tabella (`E_ISTANZA_ALTRO_SOGGETTO`),
  come per ogni altro indirizzo del ruolo.
* **Tutto o niente**: un tipo rifiutato non lascia scritti quelli prima di lui.

#### ⭐ L'azione spenta: sulla riga per il soggetto, dal picker per il ruolo

Sul **soggetto**, «Copia come…» si spegne riga per riga quando l'indirizzo non si può copiare in nessun tipo, perché
il soggetto li ha già tutti o la sua natura non ne ammette altri. Il motivo lo calcola
`anagrafiche.fn_check_copia_indirizzo_soggetto`, lo espone la vista di riga `anagrafiche.vw_indirizzi_soggetti_azioni`
e lo solleva il verbo (`E_INDIRIZZO_COPIA_NESSUN_TIPO`): il tooltip del pulsante e l'errore del verbo non possono dire
due cose diverse. L'azione è iscritta nel registro `config.azioni_riga` come `COPIA_INDIRIZZO_SOGGETTO`.

Sul **ruolo** il motivo non è di riga. La chiave giudicata è quella di destinazione, la stessa per tutte le righe del
drawer: se non ammette nessun tipo, si spengono insieme «Aggiungi» e «Copia come…», e il motivo lo dà il picker della
destinazione, `anagrafiche.fn_tipi_indirizzo_proponibili_ruolo` (nessun tipo ammesso). Se la copia arriva lo stesso,
la rifiuta la singolare col motivo del tipo chiesto, più preciso di un «nessun tipo». La riga `COPIA_INDIRIZZO_RUOLO`
resta nel registro, spenta.

#### Che cosa lasciano agli altri

Il **permesso** lo controlla l'applicazione. Le **regole dell'indirizzo** (la forma libera, gli obbligatori, il tipo
ammesso) le dicono la singolare e i guard della tabella: i verbi della copia non ne ripetono nessuna.

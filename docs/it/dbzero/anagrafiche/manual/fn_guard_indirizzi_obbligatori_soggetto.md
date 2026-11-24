## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_guard_indirizzi_obbligatori_soggetto`

> **Ultimo aggiornamento**: 24 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto giudicato, con la sua natura
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — i suoi indirizzi
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto](/dbzero/anagrafiche/funzioni/fn_indirizzi_obbligatori_mancanti_soggetto) — che cosa manca
> * [anagrafiche.fn_nomi_tipo_indirizzo_richiesto](/dbzero/anagrafiche/funzioni/fn_nomi_tipo_indirizzo_richiesto) — i nomi della frase
> * [anagrafiche.trgfn_soggetti_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_indirizzi_required) — chi lo chiama quando si scrive il soggetto
> * [anagrafiche.trgfn_indirizzi_soggetti_guard_obbligatori_soggetto](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_soggetti_guard_obbligatori_soggetto) — chi lo chiama quando un indirizzo se ne va
> * [anagrafiche.fn_guard_indirizzi_obbligatori_ruolo](/dbzero/anagrafiche/funzioni/fn_guard_indirizzi_obbligatori_ruolo) — il gemello del livello ruolo

---

### 🎯 Scopo Principale

`anagrafiche.fn_guard_indirizzi_obbligatori_soggetto` rifiuta un soggetto che non ha tutti gli indirizzi che la
sua natura dichiara obbligatori, nel giorno aziendale. È la sede unica del controllo del livello soggetto.

---

### Come giudica

* Legge la natura del soggetto e chiede i mancanti a `anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto` su
  quella natura.
* Al primo mancante, per id del tipo, rifiuta: la frase nomina la natura e il tipo richiesto col suo ripiego, per
  descrizione; se una descrizione manca, al suo posto va l'id. Dice un mancante alla volta: l'elenco intero lo
  dà `anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli`.
* Un soggetto senza natura non deve avere niente; un soggetto che non c'è più, cancellato nella stessa
  transazione coi suoi indirizzi, non si giudica.
* Un id assente è una chiamata sbagliata, non un soggetto da giudicare.

Il `tx_id` che riceve va al log dell'errore. Gira coi permessi di chi scrive: le tabelle che legge non hanno
sicurezza di riga.

---

### Il ripiego che la frase propone è uno che il soggetto può avere

Il ripiego di una riga conta, e la frase lo nomina, solo se la natura lo ammette: lo decide
`anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto`. Gli obbligatori della natura li dice
`anagrafiche.fn_tipo_indirizzo_obbligatorio_per_natura`.

---

### Col tipo che esce, solo ciò che quel tipo dava

L'ultimo parametro, facoltativo, è il tipo dell'indirizzo che esce, per una cancellazione o un cambio di tipo.

* **Detto**: si giudicano solo le righe obbligatorie che quel tipo soddisfaceva, come tipo richiesto o come
  ripiego. Il soggetto perde una cosa che gli era chiesta solo se l'indirizzo che esce era quello che la dava: una riga
  obbligatoria nata dopo, che non ha mai avuto, non ferma la cancellazione di un altro indirizzo.
* **Non detto**: si giudicano tutte le righe. È il giudizio della nascita del soggetto e del cambio di natura.

---

### Un requisito nuovo vale per chi nasce dopo

Una riga della matrice che diventa obbligatoria, o entra nella sua validità, non rigiudica i soggetti che esistono, e
non ferma la loro prossima scrittura su un'altra colonna: come per i tipi ammessi, la matrice che cambia vale per le
scritture che toccano il requisito. Un titolare incompleto per una matrice nuova resta scrivibile, e i mancanti li
dice al form `anagrafiche.fn_indirizzi_obbligatori_mancanti_soggetto_e_ruoli`.

---

{% include-markdown "it/dbzero/anagrafiche/_indirizzi-obbligatori.md" %}

---

### Codici errore

* `E_INDIRIZZO_OBBLIGATORIO_MANCANTE_TIPO_SOGGETTO` — al soggetto manca un indirizzo che la natura chiede. Il
  contesto porta il soggetto, la natura, il tipo richiesto e il ripiego.
* `E_SCRIPT_CHIAMATA_NON_VALIDA` — chiamato senza l'id del soggetto.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — chiamato da solo: il
  soggetto che non esiste tace, l'id assente è una chiamata non valida; i due trigger che lo chiamano senza
  copie della regola; la società a cui la cancellazione o il cambio di tipo tolgono la sede legale, rifiutata, e
  la sostituzione nella stessa transazione, che passa.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-requisito-nuovo-v1.sql` (3, 4, 5, 8) — col requisito nato dopo
  il soggetto: la scrittura su un'altra colonna passa, la cancellazione di un indirizzo che nessuno chiede passa,
  quella dell'unico indirizzo di una riga obbligatoria si rifiuta; il ripiego vietato non si propone.
* `db/pgtap/anagrafiche/test-indirizzo-obbligatorio-mancante-frase-v1.sql` — il codice del livello soggetto e la
  frase intera, con e senza ripiego.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-mancanti-v1.sql` — il guard che legge i mancanti.

---

### Note di migrazione

* 2026-11-17 — nasce come sede unica del controllo del soggetto, chiamata anche dal trigger della cancellazione
  di un indirizzo; prima il controllo stava nel solo trigger della scrittura del soggetto, e sollevava lo stesso
  codice del livello ruolo.
* 2026-11-24 — prende in coda il tipo che esce: dal lato degli indirizzi si giudica ciò che l'indirizzo dava, non
  tutto il soggetto. Prima una riga obbligatoria nata dopo fermava la cancellazione di qualunque indirizzo, e il
  trigger passava un `tx_id` vuoto al log.

---

{% include-markdown "signature-core.md" %}

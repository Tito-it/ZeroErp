## 📘 Documentazione Concettuale – Tabella `anagrafiche.soggetti_ruoli`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — il soggetto del ruolo
> * [config.tipi_ruoli](/dbzero/config/tabelle/tipi_ruoli) — il catalogo dei tipi di ruolo
> * [config.tipi_ruoli_nature_ammesse](/dbzero/config/tabelle/tipi_ruoli_nature_ammesse) — quali macro-tipologie ammette ogni tipo di ruolo
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — gli indirizzi del ruolo
>
> Approfondimento viste:
>
> * [anagrafiche.vw_soggetti_ruoli_dettaglio](/dbzero/anagrafiche/views/vw_soggetti_ruoli_dettaglio) — il ruolo col suo soggetto, in una riga
>
> Approfondimento funzioni:
>
> * [anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_guard_natura_ammessa) — la natura che il ruolo ammette
> * [anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required](/dbzero/anagrafiche/funzioni/trgfn_soggetti_ruoli_guard_indirizzi_required) — gli indirizzi obbligatori del ruolo
> * [anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli](/dbzero/anagrafiche/funzioni/trgfn_soggetti_guard_obbligatori_ruoli) — gli stessi indirizzi quando cambia la natura del soggetto
> * [anagrafiche.fn_ruolo_di_altro_soggetto](/dbzero/anagrafiche/funzioni/fn_ruolo_di_altro_soggetto) — «questo ruolo è di un altro soggetto?»
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il lucchetto sul soggetto del ruolo
>
> Guide:
>
> * [Soggetti e ruoli anagrafici](/guide/soggetti-e-ruoli-anagrafici) — il soggetto, la natura e i ruoli

---

### 🎯 Scopo Principale

`anagrafiche.soggetti_ruoli` dice in quali vesti un soggetto lavora con l'azienda: cliente, fornitore,
gestore, emittente, vettore, reseller, risorsa umana e gli altri tipi di `config.tipi_ruoli`. Una riga è un
soggetto in un ruolo, e un soggetto ha al più un ruolo per tipo (`uq_soggetto_ruolo`).

---

### ⭐ Il ruolo è la porta del soggetto nei processi

I processi non nominano il soggetto, nominano il ruolo. Le specializzazioni (emittenti, fornitori, gestori,
vettori, reseller, PSP, filiali bancarie, risorse umane), i billing account e i clienti, gli indirizzi, i
contatti e i conti del ruolo, e le testate dei documenti di vendita, acquisto, magazzino, pagamenti e
pratiche puntano a `soggetti_ruoli.id`. Il soggetto dà l'identità (nome, codice fiscale, partita IVA,
natura); il ruolo dice in che veste quell'identità compare.

---

### ⛔ Un ruolo appartiene per sempre al suo soggetto

Il soggetto di un ruolo non si cambia dopo la nascita: il lucchetto di colonna su `soggetto_id` rifiuta la
modifica con `E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE`. Spostare un ruolo su un altro soggetto porterebbe con sé
i billing account, i documenti e gli indirizzi, che diventerebbero di qualcun altro senza che nessuno li
abbia toccati. Chi deve servire un altro soggetto gli crea il suo ruolo.

Il lucchetto è una riga del registro dei lucchetti di colonna, montata dal runner delle automazioni: il
trigger non si scrive a mano.

---

### Le regole alla nascita del ruolo

* **La natura del soggetto deve ammettere il ruolo** (`anagrafiche.trgfn_soggetti_ruoli_guard_natura_ammessa`),
  secondo la matrice dei tipi di ruolo per macro-tipologia: un ruolo che vale solo per le persone giuridiche
  non si dà a un privato. Il controllo è immediato, alla nascita e quando cambia il tipo di ruolo.
* **Il soggetto deve essere attivo.** Lo controlla alla conferma un constraint trigger differito, alla
  nascita del ruolo.
* **Il ruolo deve avere i suoi indirizzi obbligatori** alla conferma della transazione
  (`anagrafiche.trgfn_soggetti_ruoli_guard_indirizzi_required`): il requisito lo dice il tipo di ruolo, sulla
  natura del soggetto, e quando la natura cambia lo ricontrolla
  `anagrafiche.trgfn_soggetti_guard_obbligatori_ruoli`.

---

### Un ruolo non ha uno stato

La tabella non ha una colonna `attivo`: un ruolo c'è o non c'è. Il soggetto, invece, si spegne, ma non
finché ha anche un solo ruolo: il blocco della disattivazione del soggetto conta tutti i suoi ruoli, perché
nessuno è spento.

Un ruolo si cancella solo se nessuno lo nomina: le chiavi esterne verso il ruolo non hanno azione alla
cancellazione (salvo l'origine di alcune copie d'indirizzo sui documenti, che si svuota), quindi un ruolo con un
billing account, un indirizzo o un documento resta. Cancellando un soggetto i suoi ruoli se ne vanno con lui,
alle stesse condizioni. Un tipo di ruolo usato non si cancella dal catalogo.

---

### Chi ha scritto, non che cosa c'era

Le colonne di audit dicono chi ha creato la riga e chi l'ha modificata per ultimo, e quando; la tabella non ha
storico, quindi le versioni precedenti di una riga non restano. `meta` è uno spazio libero per dati del ruolo:
il database non gli dà nessuna regola.

---

### ⚠️ Che cosa oggi non copre

* **Il tipo di ruolo si può cambiare.** Il soggetto del ruolo è bloccato, il tipo no: un ruolo cliente che ha
  già un billing account, o un ruolo nominato da documenti, può diventare un ruolo di un altro tipo. Il cambio
  passa dal solo guard della natura ammessa; le specializzazioni e i billing account controllano il tipo del
  ruolo quando si scrivono loro, non quando cambia il ruolo.
* **Un soggetto che ha lavorato non si spegne.** Il ruolo non ha uno stato, il soggetto non si spegne finché
  ha un ruolo, e un ruolo nominato da un documento non si cancella: per un soggetto con un documento lo
  spegnimento è chiuso.
* **La natura ammessa si giudica solo quando si scrive il ruolo.** Un cambio di natura del soggetto non la
  ricontrolla: restando nella stessa macro-tipologia non serve, ma un soggetto portato alla natura vuota e poi
  a una natura di un'altra famiglia tiene ruoli che quella famiglia non ammette.

---

### Codici errore

* `E_SOGGETTO_RUOLO_SOGGETTO_IMMUTABILE` — si è cambiato il soggetto di un ruolo.
* `E_RUOLO_NATURA_NON_AMMESSA`, `E_RUOLO_NATURA_TIPO_DET_NULL` — dal guard della natura ammessa.
* `E_INDIRIZZO_OBBLIGATORIO_MANCANTE` — dal guard degli indirizzi obbligatori del ruolo, alla conferma.

---

### Test

* `db/pgtap/anagrafiche/test-soggetti-ruoli-guard-natura-ammessa.sql` — le nature ammesse e rifiutate per tipo
  di ruolo, e il soggetto senza natura.
* `db/pgtap/anagrafiche/test-istanza-dello-stesso-soggetto-v1.sql` — il soggetto del ruolo che non si cambia
  (test 17) e la domanda «ruolo di un altro soggetto» (test 2).
* `db/pgtap/anagrafiche/test-emittente-soggetto-immutabile-v1.sql` — la catena emittente, ruolo, soggetto, che
  non cambia.
* `db/pgtap/anagrafiche/test-indirizzi-obbligatori-ripiego-e-cancellazione-v1.sql` — il ruolo cancellato coi
  suoi indirizzi, e il requisito del ruolo al cambio di natura.

---

### Note di migrazione

* 2026-10-19 — il soggetto del ruolo diventa immutabile, insieme alla regola per cui l'istanza e il ruolo di
  una riga sono del suo soggetto (`brief-db-processi-accensione-per-ambiente`).

---

{% include-markdown "signature-core.md" %}

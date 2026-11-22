## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_create_indirizzo`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.stradario_generale](/dbzero/config/tabelle/stradario_generale) — la via, senza comune
> * [config.stradario](/dbzero/config/tabelle/stradario) — la via nel suo comune, col CAP
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il civico, che la funzione restituisce
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/funzioni/fn_get_or_create_indirizzo_dettaglio) — il civico sulla via, trovato o creato
> * [anagrafiche.fn_indirizzo_elemento_dettaglio](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento_dettaglio) — chi la chiama per le madri degli indirizzi
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — lo stradario e le tre forme di un indirizzo

---

### 🎯 Scopo Principale

`anagrafiche.fn_create_indirizzo` risolve un indirizzo normalizzato in un'istruzione sola: la via, se è nuova, e il
civico su quella via. Restituisce il dettaglio dell'indirizzo, trovato o creato.

La chiamano le madri degli indirizzi, attraverso `anagrafiche.fn_indirizzo_elemento_dettaglio`, e il provisioning dei
dati di sviluppo.

---

### Una via già nota, o una via nuova

* **Una via del catalogo** si indica con la via del comune (`p_stradario_id`): i campi di una via nuova, se ci sono,
  non si guardano.
* **Una via nuova** si indica col tipo strada, il nome, il comune e il CAP. La via generale (tipo strada e nome) e la
  via del comune (via generale, comune e CAP) si trovano se ci sono e si creano se mancano: due chiamate con la stessa
  via danno la stessa riga. Il nome si ripulisce dagli spazi in testa e in coda.

Il civico, con estensione, palazzina, scala, piano e interno, lo risolve
`anagrafiche.fn_get_or_create_indirizzo_dettaglio`, che allo stesso modo non duplica un dettaglio che c'è già.

---

### ⭐ Una via soppressa non si riusa

La via del comune si cerca solo fra le vie **vive**: una via soppressa (`config.stradario.obsoleto_dal`) non si
ritrova, e se nel comune c'è solo lei nasce la via viva accanto. Una via soppressa indicata per id arriva invece al
dettaglio, e lì la rifiuta il guard del ritiro (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`).

---

### ⭐ Tutto o niente

La via e il civico nascono nella stessa istruzione: se il dettaglio si rifiuta, non resta scritta nemmeno la via
appena creata.

---

### ⚠️ Che cosa oggi non copre

* **I campi di una via nuova** non si controllano: tipo strada, nome, comune o CAP mancanti arrivano ai vincoli
  `NOT NULL` delle due tabelle dello stradario, che rifiutano con l'errore grezzo del database e non con un codice
  del catalogo. Lo stesso succede a un elemento che non indica nessuna forma, perché senza via e senza dettaglio la
  madre lo tratta come una via nuova.

---

### Codici errore

La funzione non solleva codici suoi: i rifiuti arrivano dal dettaglio (`anagrafiche.fn_get_or_create_indirizzo_dettaglio`
e i guard di `anagrafiche.indirizzi_dettaglio`, fra cui `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`).

---

### Test

* `db/pgtap/anagrafiche/test-fn-create-indirizzo-v1.sql` — la via nuova, la seconda chiamata che ritrova la stessa via,
  il dettaglio rifiutato che non lascia la via scritta.
* `db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql` — una via nuova sulla terna (via, comune, CAP) che ha anche una via soppressa
  nasce sulla via viva.

---

### Note di migrazione

* 2026-07-08 — nasce, e prende il posto dei tre passi che l'applicazione faceva senza una transazione unica: un
  dettaglio rifiutato lasciava scritte le righe dello stradario.

---

{% include-markdown "signature-core.md" %}

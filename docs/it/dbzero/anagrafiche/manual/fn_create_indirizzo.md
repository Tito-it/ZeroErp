## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_create_indirizzo`

> **Ultimo aggiornamento**: 24 novembre 2026
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
* **Una via nuova** si indica col tipo strada, il nome, il comune e il CAP, tutti e quattro: ogni campo che manca si
  rifiuta con `E_INDIRIZZO_VIA_NUOVA_INCOMPLETA` e il nome del campo, e un nome vuoto conta come mancante. Il nome si
  ripulisce dagli spazi in testa e in coda.
* **Prima si cerca, poi si scrive.** La via generale (tipo strada e nome) e la via del comune (via generale, comune e
  CAP) si ritrovano se ci sono e si creano solo se mancano: due chiamate con la stessa via danno la stessa riga. Una via
  che esiste non si riscrive, e il suo storico non prende una versione per ogni indirizzo creato su di lei. Se due
  sessioni creano la stessa via insieme, la seconda rilegge quella della prima.
* **La descrizione breve** di una via generale nuova sono i primi 50 caratteri del nome: un nome lungo non ferma la
  creazione.

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

### Codici errore

* `E_INDIRIZZO_VIA_NUOVA_INCOMPLETA` — a una via nuova manca il tipo strada, il nome, il comune o il CAP; il campo
  dice quale.
* Gli altri rifiuti arrivano dal dettaglio (`anagrafiche.fn_get_or_create_indirizzo_dettaglio` e i guard di
  `anagrafiche.indirizzi_dettaglio`, fra cui `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`).

---

### Test

* `db/pgtap/anagrafiche/test-fn-create-indirizzo-v1.sql` — la via nuova, la seconda chiamata che ritrova la stessa via,
  il dettaglio rifiutato che non lascia la via scritta.
* `db/pgtap/dbops/test-fusioni-comune-stradario-v1.sql` — una via nuova sulla terna (via, comune, CAP) che ha anche una via soppressa
  nasce sulla via viva.
* `db/pgtap/anagrafiche/test-indirizzi-viste-forma-e-vincoli-v1.sql` (14, 23, 24, 25) — la via nuova senza
  toponomastica; la seconda chiamata con la stessa via nuova, che passa senza riscrivere la via e senza lasciarle
  versioni di storico.

---

### Note di migrazione

* 2026-07-08 — nasce, e prende il posto dei tre passi che l'applicazione faceva senza una transazione unica: un
  dettaglio rifiutato lasciava scritte le righe dello stradario.
* 2026-11-24 — la via nuova si valida qui, col suo codice: prima il controllo era lasciato all'applicazione, e un campo
  mancante cadeva sui vincoli dello stradario. Una via che esiste si ritrova senza riscriverla (prima ogni ritrovamento
  la riscriveva, e lasciava versioni di storico); la descrizione breve prende i primi 50 caratteri del nome.

---

{% include-markdown "signature-core.md" %}

## 📘 Documentazione Concettuale – Funzione `dbops.fn_normalize_indirizzo`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.stradario](/dbzero/config/tabelle/stradario) — le vie fra cui cerca
> * [config.codici_postali](/dbzero/config/tabelle/codici_postali) — dove ritrova il CAP
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — l'indirizzo strutturato che il nome del risultato promette
>
> Approfondimento funzioni:
>
> * [script.fn_get_stradario](/dbzero/script/funzioni/fn_get_stradario) — la ricerca della via che fa davvero il lavoro

---

### 🎯 Scopo Principale

Prova a risolvere un indirizzo scritto a mano, dentro un comune, in una via dello stradario:
restituisce la via normalizzata, il CAP e la geolocalizzazione della prima via che trova.

È dichiaratamente una base, e nessuno la chiama: né il backend, né un'altra funzione, né un test.

---

### Che cosa fa davvero

Cerca il testo ricevuto dentro il nome completo delle vie del comune (toponimo più nome, senza
badare a maiuscole e minuscole) con `script.fn_get_stradario`, e prende **la prima** in ordine
alfabetico. Di quella restituisce:

* la via normalizzata: il nome completo, in maiuscolo;
* il CAP, ritrovato in `config.codici_postali` per codice e comune;
* la geolocalizzazione della via.

Se non trova niente, restituisce una riga tutta vuota.

---

### ⚠️ Che cosa non fa, anche se il nome lo promette

* **Non legge il civico.** Il civico normalizzato è sempre vuoto. E siccome cerca il testo intero
  dentro il nome della via, un indirizzo scritto con il civico («Via Roma 10») non trova nessuna
  via: funziona solo col nome della via da solo.
* **Non risolve un indirizzo dettaglio.** La colonna `indirizzo_dettaglio_id` del risultato porta
  in realtà l'id della **via dello stradario**, non quello di un indirizzo dettaglio.
* **Non sceglie fra più vie.** Una ricerca parziale prende la prima in ordine alfabetico fra
  tutte quelle che contengono il testo, che non è detto sia quella giusta.

⭐ La conseguenza pratica: il risultato va verificato, non dato per buono. Un indirizzo che non
risolve è più utile di uno risolto male, perché il secondo entra in anagrafica e ci resta.

---

### Codici errore

Nessuno: un indirizzo che non si risolve torna vuoto, non è un errore.

---

### Note di migrazione

* 2026-08-04 — la ricerca del CAP legge la colonna `codice` di `config.codici_postali`: prima
  nominava una colonna che non esisteva più dal 2025-08-17, e la funzione era rotta.

---

{% include-markdown "signature-core.md" %}

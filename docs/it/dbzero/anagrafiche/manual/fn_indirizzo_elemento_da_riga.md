## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzo_elemento_da_riga`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_soggetti](/dbzero/anagrafiche/tabelle/indirizzi_soggetti) — una delle due righe da cui si legge
> * [anagrafiche.indirizzi](/dbzero/anagrafiche/tabelle/indirizzi) — l'altra, con le stesse colonne dell'indirizzo
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_indirizzo_elemento](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento) — la grammatica in cui l'elemento è scritto
> * [anagrafiche.fn_copia_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_soggetto) — la copia sul soggetto
> * [anagrafiche.fn_copia_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_ruolo) — la copia dalla riga del ruolo
> * [anagrafiche.fn_copia_indirizzo_soggetto_su_ruolo](/dbzero/anagrafiche/funzioni/fn_copia_indirizzo_soggetto_su_ruolo) — la copia dalla riga del soggetto al ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — la copia nel drawer

---

### 🎯 Scopo Principale

`anagrafiche.fn_indirizzo_elemento_da_riga` ricostruisce, dalle colonne di un indirizzo salvato, l'elemento che le
madri degli indirizzi sanno scrivere, senza il tipo. È il primo passo di ogni copia: il verbo ci aggiunge il tipo, e la
singolare scrive la riga nuova.

---

### ⭐ Che cosa porta e che cosa no

* **Un indirizzo normalizzato** diventa il solo riferimento al dettaglio: la riga nuova punta allo stesso civico, che non
  si duplica.
* **Un indirizzo libero** diventa i suoi campi valorizzati: il testo, lo stato, comune e CAP del catalogo, località,
  codice postale, regione e sotto-località. I campi vuoti restano fuori, e la forma (nazionale o estera) arriva intera.
* **Non porta** il tipo, l'istanza, la geolocalizzazione, l'audit, l'identificativo di transazione né il flag dello
  storico: sono quelli della riga nuova.

Le due tabelle degli indirizzi, del soggetto e del ruolo, hanno le stesse colonne dell'indirizzo con gli stessi tipi, e
la funzione serve tutte e due: i verbi le passano le colonne, non la riga.

È pura: non legge tabelle, e a parità di colonne dà sempre lo stesso elemento.

---

### Test

* `db/pgtap/anagrafiche/test-copia-indirizzo-v1.sql` — la copia di un dettaglio, che porta lo stesso dettaglio, e di un
  indirizzo libero nazionale ed estero, con tutte le colonne della forma.
* `db/pgtap/anagrafiche/test-copia-indirizzo-destinazione-v1.sql` — la copia da un'istanza a un'altra, con tutte le
  colonne della forma.

---

### Note di migrazione

* 2026-11-15 — nasce, col verbo della copia sul soggetto.

---

{% include-markdown "signature-core.md" %}

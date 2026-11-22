## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzo_elemento_dettaglio`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — il dettaglio che la funzione restituisce
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_indirizzo_elemento](/dbzero/anagrafiche/funzioni/fn_indirizzo_elemento) — il passo prima: l'elemento letto
> * [anagrafiche.fn_create_indirizzo](/dbzero/anagrafiche/funzioni/fn_create_indirizzo) — la via e il civico, trovati o creati
> * [anagrafiche.fn_crea_indirizzo_soggetto](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_soggetto) — la madre del soggetto
> * [anagrafiche.fn_crea_indirizzo_ruolo](/dbzero/anagrafiche/funzioni/fn_crea_indirizzo_ruolo) — la madre del ruolo
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — le tre forme di un indirizzo

---

### 🎯 Scopo Principale

`anagrafiche.fn_indirizzo_elemento_dettaglio` dice quale dettaglio (l'indirizzo normalizzato) porta un elemento già
letto da `anagrafiche.fn_indirizzo_elemento`: nessuno, quello indicato, o quello della via e del civico, trovato o
creato. Lo chiamano le due singolari, nel momento in cui scrivono la riga.

---

### ⭐ Una forma sola, in quest'ordine

| L'elemento porta | Restituisce |
| --- | --- |
| un testo libero, non vuoto | niente: la riga è libera |
| un dettaglio (`indirizzo_dettaglio_id`) | quello |
| altrimenti, una via e il civico | il dettaglio risolto da `anagrafiche.fn_create_indirizzo`, che non duplica |

L'ordine decide quando l'elemento porta più forme: il testo libero vince sul dettaglio, che si scarta, e il dettaglio
vince sui campi di una via, che non si guardano. I campi vuoti del civico (estensione, palazzina, scala, piano,
interno) valgono come assenti.

Si chiama solo per le righe che si scrivono davvero: una plurale che salta un tipo già presente non risolve la sua via.

---

### ⚠️ Che cosa oggi non copre

* **Un elemento senza forma.** Senza testo libero e senza dettaglio, l'elemento si tratta come una via nuova anche se
  non ne porta i campi: una via incompleta, o un indirizzo libero col solo stato e comune e il testo vuoto, finisce sui
  vincoli `NOT NULL` dello stradario con l'errore grezzo del database, invece che sul guard della forma libera col suo
  codice.

---

### Codici errore

La funzione non solleva codici suoi: i rifiuti arrivano da `anagrafiche.fn_create_indirizzo` e dal dettaglio.

---

### Test

Non ha un test suo: la provano i test delle madri, `db/pgtap/anagrafiche/test-fn-crea-indirizzi-ruolo-v1.sql` (le tre
forme, due civici diversi sulla stessa via) e `db/pgtap/anagrafiche/test-fn-crea-indirizzo-soggetto.sql` (il dettaglio).

---

### Note di migrazione

* 2026-10-18 — nasce, insieme alla grammatica comune, dal corpo della madre del ruolo.

---

{% include-markdown "signature-core.md" %}

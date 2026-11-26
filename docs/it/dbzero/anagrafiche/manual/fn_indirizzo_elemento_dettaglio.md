## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_indirizzo_elemento_dettaglio`

> **Ultimo aggiornamento**: 24 novembre 2026
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
> * [anagrafiche.trgfn_indirizzi_guard_forma_libera](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_guard_forma_libera) — il giudizio della riga libera, anche quando l'elemento è vuoto
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
| nessuna chiave di una via (`stradario_id`, `toponomastica_id`, `descrizione_via`) | niente: la riga è libera |
| altrimenti, una via e il civico | il dettaglio risolto da `anagrafiche.fn_create_indirizzo`, che non duplica |

L'ordine decide quando l'elemento porta più forme: il testo libero vince sul dettaglio, che si scarta, e il dettaglio
vince sui campi di una via, che non si guardano. I campi vuoti del civico (estensione, palazzina, scala, piano,
interno) valgono come assenti.

La forma la decide il database dalle chiavi. Un elemento senza testo libero, senza dettaglio e senza le chiavi di una
via si scrive come riga libera, e lo giudica il guard della forma
(`anagrafiche.trgfn_indirizzi_guard_forma_libera`), che dice che cosa manca: un elemento vuoto, o col solo tipo, ha
`E_INDIRIZZO_LIBERO_INCOMPLETO` sul campo `indirizzo_libero`. Comune e CAP non decidono la forma: valgono anche per
l'indirizzo libero del catalogo. Una via nuova incompleta la rifiuta `anagrafiche.fn_create_indirizzo`, col campo che
manca.

Si chiama solo per le righe che si scrivono davvero: una plurale che salta un tipo già presente non risolve la sua via.

---

### Codici errore

La funzione non solleva codici suoi: i rifiuti arrivano da `anagrafiche.fn_create_indirizzo` (la via nuova
incompleta, `E_INDIRIZZO_VIA_NUOVA_INCOMPLETA`), dal dettaglio e, per la riga libera, dal guard della forma
(`E_INDIRIZZO_LIBERO_INCOMPLETO`).

---

### Test

Non ha un test suo: la provano i test delle madri, `db/pgtap/anagrafiche/test-fn-crea-indirizzi-ruolo-v1.sql` (le tre
forme, due civici diversi sulla stessa via) e `db/pgtap/anagrafiche/test-fn-crea-indirizzo-soggetto.sql` (il dettaglio),
e `db/pgtap/anagrafiche/test-indirizzi-viste-forma-e-vincoli-v1.sql` (12, 13, 14: il testo libero vuoto, l'elemento col
solo tipo, la via nuova senza toponomastica).

---

### Note di migrazione

* 2026-10-18 — nasce, insieme alla grammatica comune, dal corpo della madre del ruolo.
* 2026-11-24 — la forma si decide dalle chiavi: un elemento senza le chiavi di una via è libero. Prima si trattava come
  una via nuova, e cadeva sui vincoli dello stradario con l'errore grezzo; il commento che lasciava al backend il
  controllo della via nuova si ritira.

---

{% include-markdown "signature-core.md" %}

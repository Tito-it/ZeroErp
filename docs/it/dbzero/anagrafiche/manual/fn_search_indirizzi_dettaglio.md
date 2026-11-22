## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_search_indirizzi_dettaglio`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — i civici che cerca
>
> Approfondimento viste:
>
> * [anagrafiche.vw_indirizzi_dettaglio](/dbzero/anagrafiche/views/vw_indirizzi_dettaglio) — la vista da cui legge, e la forma delle righe che restituisce
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/funzioni/fn_get_or_create_indirizzo_dettaglio) — il «trova o crea», che normalizza prima di cercare
> * [anagrafiche.fn_build_indirizzo_normalizzato](/dbzero/anagrafiche/funzioni/fn_build_indirizzo_normalizzato) — come si salvano i valori su cui si cerca
>
> Guide:
>
> * [Gestione degli indirizzi](/guide/gestione-degli-indirizzi) — il quadro degli indirizzi e dello stradario

---

### 🎯 Scopo Principale

`anagrafiche.fn_search_indirizzi_dettaglio` cerca fra i civici attivi, per via e dettaglio oppure per un pezzo
del testo dell'indirizzo, e restituisce le righe di `anagrafiche.vw_indirizzi_dettaglio`. Legge soltanto: non
crea niente.

---

### Due modi di cercare

* **Per via**: con la via passata, la ricerca resta su quella via, e ogni valore del dettaglio passato è un
  filtro in più (civico, estensione, palazzina, scala, piano, interno). Un valore non passato non filtra; un
  testo vuoto passato vuol dire «senza quel valore».
* **Per testo**: un pezzo dell'indirizzo normalizzato (`p_indirizzo_norm`), cercato in qualunque punto della
  stringa, senza badare a maiuscole e minuscole. Gli spazi in testa e in coda non contano, e un testo di soli
  spazi è come non passato.

Il testo si applica sempre quando c'è, anche insieme alla via. Serve almeno uno dei due: senza via e senza
testo la funzione si ferma.

Le righe escono in ordine di indirizzo normalizzato, al massimo `p_limit` (cinquanta, se non detto).

---

### ⚠️ Che cosa oggi non copre

* **Il dettaglio si confronta col valore grezzo**: la riga ha i valori normalizzati (maiuscolo, estensione col
  `/`), il parametro no. Un'estensione `A` non trova la `/A`, e una scala `b` non trova la `B`. Il «trova o
  crea» normalizza prima di cercare; questa funzione no.
* **Il rifiuto della ricerca senza criteri non ha un codice**: è un errore scritto direttamente nella funzione,
  non passa dal catalogo dei messaggi, e chi lo riceve non ha un codice né un campo da accendere.
* **Il limite non ha un tetto**: chi passa un numero molto grande legge tutta la tabella, e un numero negativo
  fa fallire la query con un errore tecnico.
* **Il testo cercato non è protetto**: `%` e `_` dentro `p_indirizzo_norm` valgono come caratteri jolly.
* **La ricerca per testo non usa l'indice trigram** della tabella: confronta la colonna portata in maiuscolo,
  e l'indice è sulla colonna com'è.
* **I civici di una via che non si risolve non si trovano**, perché la vista da cui legge li perde.

---

### Test

* `db/pgtap/anagrafiche/create-gestore-indirizzo-res-domfisc.sql` — il civico appena creato si ritrova per
  testo. Nessun test prova i filtri del dettaglio.

---

{% include-markdown "signature-core.md" %}

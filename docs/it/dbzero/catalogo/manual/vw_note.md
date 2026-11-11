## 📘 Documentazione Concettuale – Vista `catalogo.vw_note`

> **Ultimo aggiornamento**: 11 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.note](/dbzero/catalogo/tabelle/note) — la tabella madre delle note di catalogo, che la vista espone
> * [config.note_stili](/dbzero/config/tabelle/note_stili) — lo stile della nota
> * [config.lingue](/dbzero/config/tabelle/lingue) — la lingua della nota
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_note](/dbzero/catalogo/views/vw_articoli_note) — la legge per le note degli articoli
> * [catalogo.vw_articoli_componenti_note](/dbzero/catalogo/views/vw_articoli_componenti_note) — la legge per le note dei legami di distinta

---

### 🎯 Scopo Principale

La proiezione di una nota di catalogo: una riga per nota, di ogni partizione, con le colonne
della nota e la decodifica dello stile e della lingua. È scritta una volta sola: le due viste
delle note di un bersaglio la leggono e aggiungono i nomi del loro oggetto.

---

### Una riga per nota

Le colonne della nota hanno il prefisso `nota_`, quelle dello stile `stile_`, quelle della
lingua `lingua_`. La vista non filtra: le note nascoste e quelle di sola stampa ci sono, e
quali mostrare lo sceglie chi legge, con `nota_visibile`, `nota_solo_stampa`, la posizione e la
sequenza.

Si legge filtrando per `nota_target_tipo`, che è la chiave di partizione: il filtro scende sulla
tabella madre e legge una sola partizione. Si legge e basta: le note si scrivono sulla madre o
sulla partizione.

`tx_id` non c'è: è la correlazione tecnica con l'audit, non un dato della nota.

---

### Perché qui

Le colonne di nota, stile e lingua erano scritte due volte, nelle due viste delle note: un
ritocco fatto su una sola le avrebbe fatte divergere senza errore. La lettura comune delle note
dei documenti ([script.fn_get_note](/dbzero/script/funzioni/fn_get_note)) qui non serve, perché
vuole un bersaglio `bigint` e le note di catalogo hanno un `uuid`.

---

### Test

* `db/pgtap/catalogo/test-note-catalogo-forma-v1.sql` — la vista ha una riga per nota, e la vista
  delle note di un articolo mostra le stesse note.

---

### Note di migrazione

* 2026-11-11 — nasce come proiezione comune delle due viste delle note
  (brief-db-revisione-catalogo, giro 4).

---

{% include-markdown "signature-core.md" %}

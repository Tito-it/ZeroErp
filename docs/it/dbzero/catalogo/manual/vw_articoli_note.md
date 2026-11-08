## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_note`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.note_articoli](/dbzero/catalogo/tabelle/note_articoli) — la partizione delle note che la vista legge
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'articolo annotato, da cui prende codice e descrizione
> * [config.note_stili](/dbzero/config/tabelle/note_stili) — lo stile della nota
> * [config.lingue](/dbzero/config/tabelle/lingue) — la lingua della nota
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_componenti_note](/dbzero/catalogo/views/vw_articoli_componenti_note) — la stessa lettura per le note dei legami di distinta

---

### 🎯 Scopo Principale

Le note degli articoli, una riga per nota, con il codice e la descrizione dell'articolo annotato e la decodifica dello stile e della lingua.

Si legge per mostrare o stampare le note di un articolo; si scrive sulla partizione
[catalogo.note_articoli](/dbzero/catalogo/tabelle/note_articoli), non qui.

---

### Mostra ogni nota, anche quelle da non mostrare

La vista non filtra: espone le note visibili e quelle nascoste, quelle di sola stampa e le
altre, e anche le note ancorate a `RIGA`, che su un articolo non hanno significato. Scegliere
quali note far vedere, e in che ordine, tocca a chi legge, con i flag `visibile` e
`solo_stampa` e con posizione e sequenza della nota.

Un articolo senza note non compare.

---

### ⚠️ Che cosa oggi non copre

* **È una copia.** La proiezione della nota (colonne della nota, stile e lingua) è la stessa di
  [catalogo.vw_articoli_componenti_note](/dbzero/catalogo/views/vw_articoli_componenti_note),
  scritta due volte: un ritocco fatto su una sola delle due le fa divergere senza errore.
* **Non passa dalla lettura comune.** Le note dei documenti si leggono con
  [script.fn_get_note](/dbzero/script/funzioni/fn_get_note), che qui non si può usare perché
  vuole un bersaglio `bigint`.

---

### Test

* `db/pgtap/catalogo/test-vw-articoli-note.sql` — su un articolo costruito dal test, la nota
  compare nella vista con lo stile e la lingua giusti.

---

{% include-markdown "signature-core.md" %}

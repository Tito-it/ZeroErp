## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_note`

> **Ultimo aggiornamento**: 11 novembre 2026
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
> * [catalogo.vw_note](/dbzero/catalogo/views/vw_note) — la proiezione della nota che questa vista legge
> * [catalogo.vw_articoli_componenti_note](/dbzero/catalogo/views/vw_articoli_componenti_note) — la stessa lettura per le note dei legami di distinta

---

### 🎯 Scopo Principale

Le note degli articoli, una riga per nota, con il codice e la descrizione dell'articolo annotato e la decodifica dello stile e della lingua.

Si legge per mostrare o stampare le note di un articolo; si scrive sulla partizione
[catalogo.note_articoli](/dbzero/catalogo/tabelle/note_articoli), non qui.

---

### Mostra ogni nota, anche quelle da non mostrare

La vista non filtra: espone le note visibili e quelle nascoste, quelle di sola stampa e le
altre. Le colonne della nota, dello stile e della lingua vengono da
[catalogo.vw_note](/dbzero/catalogo/views/vw_note), per le note con `target_tipo` `ARTICOLO`.
Scegliere
quali note far vedere, e in che ordine, tocca a chi legge, con i flag `visibile` e
`solo_stampa` e con posizione e sequenza della nota.

Un articolo senza note non compare.

---

### ⚠️ Che cosa oggi non copre

* **Non passa dalla lettura comune.** Le note dei documenti si leggono con
  [script.fn_get_note](/dbzero/script/funzioni/fn_get_note), che qui non si può usare perché
  vuole un bersaglio `bigint`.

---

### Test

* `db/pgtap/catalogo/test-vw-articoli-note.sql` — su un articolo costruito dal test, la nota
  compare nella vista con lo stile e la lingua giusti.
* `db/pgtap/catalogo/test-note-catalogo-forma-v1.sql` — la vista mostra le note dell'articolo
  come la vista base, con le colonne di prima nello stesso ordine.

---

### Note di migrazione

* 2026-01-14 — nasce.
* 2026-11-11 — legge la proiezione comune [catalogo.vw_note](/dbzero/catalogo/views/vw_note),
  con le stesse colonne; `nota_user_insert` e `nota_user_update` sono testo
  (brief-db-revisione-catalogo, giro 4).

---

{% include-markdown "signature-core.md" %}

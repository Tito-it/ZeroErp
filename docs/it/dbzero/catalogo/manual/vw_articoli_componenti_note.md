## 📘 Documentazione Concettuale – Vista `catalogo.vw_articoli_componenti_note`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.note_articoli_componenti](/dbzero/catalogo/tabelle/note_articoli_componenti) — la partizione delle note che la vista legge
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — il legame di distinta annotato
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — il padre e il componente del legame, da cui prende codice e descrizione
> * [config.note_stili](/dbzero/config/tabelle/note_stili) — lo stile della nota
> * [config.lingue](/dbzero/config/tabelle/lingue) — la lingua della nota
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_note](/dbzero/catalogo/views/vw_articoli_note) — la stessa lettura per le note degli articoli

---

### 🎯 Scopo Principale

Le note dei legami di distinta base, una riga per nota, con il padre e il componente del legame (codice e descrizione) e la decodifica dello stile e della lingua.

Si legge per mostrare o stampare le note di una distinta; si scrive sulla partizione
[catalogo.note_articoli_componenti](/dbzero/catalogo/tabelle/note_articoli_componenti), non qui.

---

### Mostra ogni nota, di ogni versione del legame

La vista non filtra: espone le note visibili e quelle nascoste, quelle di sola stampa e le
altre, e le note dei legami chiusi nel tempo come quelle dei legami in vigore. Chi cerca le
note della distinta a una data deve filtrare il legame per la sua validità; quali note far
vedere, e in che ordine, si sceglie con i flag `visibile` e `solo_stampa` e con posizione e
sequenza della nota.

Un legame senza note non compare.

---

### ⚠️ Che cosa oggi non copre

* **È una copia.** La proiezione della nota (colonne della nota, stile e lingua) è la stessa di
  [catalogo.vw_articoli_note](/dbzero/catalogo/views/vw_articoli_note), scritta due volte: un
  ritocco fatto su una sola delle due le fa divergere senza errore.
* **Non espone la validità del legame.** Per sapere se un legame è in vigore a una data bisogna
  tornare a [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti).
* **Non passa dalla lettura comune.** Le note dei documenti si leggono con
  [script.fn_get_note](/dbzero/script/funzioni/fn_get_note), che qui non si può usare perché
  vuole un bersaglio `bigint`.

---

### Test

* `db/pgtap/catalogo/test-vw-articoli-componenti-note.sql` — su un padre e un componente
  costruiti dal test, la nota del legame compare nella vista con lo stile e la lingua giusti; una
  nota col tipo dell'articolo e il bersaglio di un legame è rifiutata.

---

{% include-markdown "signature-core.md" %}

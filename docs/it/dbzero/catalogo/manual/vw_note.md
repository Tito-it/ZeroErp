## 📘 Documentazione Concettuale – Vista `catalogo.vw_note`

> **Ultimo aggiornamento**: 12 novembre 2026
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
> * [vendite.vw_note](/dbzero/vendite/views/vw_note), [acquisti.vw_note](/dbzero/acquisti/views/vw_note), [magazzino.vw_note](/dbzero/magazzino/views/vw_note) — le sorelle delle altre sedi, con le stesse colonne

---

### 🎯 Scopo Principale

La proiezione di una nota di catalogo: una riga per nota, di ogni partizione, con le colonne
della nota e la decodifica dello stile e della lingua. È scritta una volta sola: le due viste
delle note di un bersaglio la leggono e aggiungono i nomi del loro oggetto.

---

### Una riga per nota

Le colonne della nota hanno il prefisso `nota_`, quelle dello stile `stile_` (anche
`stile_codice_interno`, in coda), quelle della lingua `lingua_`. La vista non filtra: le note nascoste e quelle di sola stampa ci sono, e
quali mostrare lo sceglie chi legge, con `nota_visibile`, `nota_solo_stampa`, la posizione e la
sequenza.

Si legge filtrando per `nota_target_tipo`, che è la chiave di partizione: il filtro scende sulla
tabella madre e legge una sola partizione. Si legge e basta: le note si scrivono sulla madre o
sulla partizione.

`tx_id` non c'è: è la correlazione tecnica con l'audit, non un dato della nota.

---

### ⭐ Una vista per sede, tutte gemelle

Le note hanno quattro sedi della stessa forma: catalogo, vendite, acquisti, magazzino. Ognuna ha
la sua `<schema>.vw_note`, con **le stesse colonne nello stesso ordine**; cambia solo il tipo del
bersaglio (qui `uuid`, altrove `bigint`). La proiezione con stile e lingua sta in queste viste, e
chi legge le note (il backend) legge la vista della sede invece di ricomporla. Le viste sono `security_invoker`: chi le interroga vede ciò che le policy della sede
gli concedono (qui nessuna, perché il catalogo è comune; in vendite e magazzino le policy di
perimetro). Una sede nuova delle note nasce con la sua vista: il presidio è
`db/pgtap/dbops/test-viste-note-gemelle-v1.sql`.

---

### Perché qui

Le colonne di nota, stile e lingua erano scritte due volte, nelle due viste delle note: un
ritocco fatto su una sola le avrebbe fatte divergere senza errore.

---

### Test

* `db/pgtap/catalogo/test-note-catalogo-forma-v1.sql` — la vista ha una riga per nota, e la vista
  delle note di un articolo mostra le stesse note.
* `db/pgtap/dbops/test-viste-note-gemelle-v1.sql` — una vista per sede, gemelle, `security_invoker`.

---

### Note di migrazione

* 2026-11-11 — nasce come proiezione comune delle due viste delle note
  (brief-db-revisione-catalogo, giro 4).
* 2026-11-12 — `stile_codice_interno` in coda e `security_invoker`: la forma comune delle viste
  delle note di tutte le sedi (brief-db-revisione-catalogo §20). Lo stesso giorno si ritira
  `script.fn_get_note`, che ricomponeva la stessa proiezione per le altre sedi e non aveva
  consumatori.

---

{% include-markdown "signature-core.md" %}

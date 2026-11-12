## 📘 Documentazione Concettuale – Vista `acquisti.vw_note`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [acquisti.note](/dbzero/acquisti/tabelle/note) — la tabella madre delle note di acquisti, che la vista espone
> * [config.note_stili](/dbzero/config/tabelle/note_stili) — lo stile della nota
> * [config.lingue](/dbzero/config/tabelle/lingue) — la lingua della nota
>
> Approfondimento viste:
>
> * [catalogo.vw_note](/dbzero/catalogo/views/vw_note) — la sorella di catalogo, dove la forma comune è spiegata

---

### 🎯 Scopo Principale

La proiezione di una nota di acquisti: una riga per nota, di ogni partizione, con le colonne della
nota e la decodifica dello stile e della lingua. Ha le stesse colonne, nello stesso ordine, delle
viste delle note delle altre sedi: la forma comune è spiegata in
[catalogo.vw_note](/dbzero/catalogo/views/vw_note).

---

### Come si legge

La vista non filtra: le note nascoste e quelle di sola stampa ci sono, e quali mostrare lo sceglie
chi legge. Si legge filtrando per `nota_target_tipo`, che è la chiave di partizione: il filtro
scende sulla madre e legge una sola partizione. Si legge e basta: le note si scrivono sulla madre
o sulla partizione.

**Chi vede che cosa.** La vista è `security_invoker`. ⚠️ Oggi `acquisti.note` non ha RLS, né la
madre né le partizioni: la vista mostra tutte le note, e le policy che arriveranno varranno anche
qui senza toccarla.

---

### Test

* `db/pgtap/dbops/test-viste-note-gemelle-v1.sql` — una vista per sede, gemelle, `security_invoker`,
  letta dall'applicazione.

---

### Note di migrazione

* 2026-11-12 — nasce, con le sorelle delle altre sedi; prende il posto di `script.fn_get_note` e
  del suo involucro di questo schema, ritirati (brief-db-revisione-catalogo §20).

---

{% include-markdown "signature-core.md" %}

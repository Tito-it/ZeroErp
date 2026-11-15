## 📘 Documentazione Concettuale – Vista `vendite.vw_note`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.note](/dbzero/vendite/tabelle/note) — la tabella madre delle note di vendite, che la vista espone
> * [config.note_stili](/dbzero/config/tabelle/note_stili) — lo stile della nota
> * [config.lingue](/dbzero/config/tabelle/lingue) — la lingua della nota
>
> Approfondimento viste:
>
> * [catalogo.vw_note](/dbzero/catalogo/views/vw_note) — la sorella di catalogo, dove la forma comune è spiegata

---

### 🎯 Scopo Principale

La proiezione di una nota di vendite: una riga per nota, di ogni partizione, con le colonne della
nota e la decodifica dello stile e della lingua. Ha le stesse colonne, nello stesso ordine, delle
viste delle note delle altre sedi: la forma comune è spiegata in
[catalogo.vw_note](/dbzero/catalogo/views/vw_note).

---

### Come si legge

La vista non filtra: le note nascoste e quelle di sola stampa ci sono, e quali mostrare lo sceglie
chi legge. Si legge filtrando per `nota_target_tipo`, che è la chiave di partizione: il filtro
scende sulla madre e legge una sola partizione. Si legge e basta: le note si scrivono sulla madre
o sulla partizione.

**Chi vede che cosa.** La vista è `security_invoker` e `vendite.note` è sotto RLS, con una
policy per veste (operatore, cliente del portale, cliente dello shop): chi la interroga vede le
note che le policy della madre gli concedono, né una di più né una di meno.

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

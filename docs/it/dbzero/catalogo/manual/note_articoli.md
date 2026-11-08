## 📘 Documentazione Concettuale – Tabella `catalogo.note_articoli`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'articolo che queste note annotano
> * [catalogo.note](/dbzero/catalogo/tabelle/note) — la tabella madre delle partizioni di catalogo
> * [catalogo.note_articoli_componenti](/dbzero/catalogo/tabelle/note_articoli_componenti) — la partizione gemella, per i legami di distinta
> * [vendite.note](/dbzero/vendite/tabelle/note) — il meccanismo delle note, documentato per intero
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_note](/dbzero/catalogo/views/vw_articoli_note) — la lettura di queste note con stile e lingua

---

### 🎯 Scopo Principale

La partizione delle note di catalogo che annotano un articolo ([catalogo.articoli](/dbzero/catalogo/tabelle/articoli)).

---

{% include-markdown "it/dbzero/catalogo/_note-partizioni.md" %}

---

### ⚠️ Una nota sull'articolo vale ovunque l'articolo compare

La nota di un articolo lo segue in ogni documento e in ogni distinta che lo include, anche come
componente di un padre. Per annotare un componente solo dentro una distinta precisa si usa
[catalogo.note_articoli_componenti](/dbzero/catalogo/tabelle/note_articoli_componenti), che
annota il legame e non l'articolo.

---

{% include-markdown "signature-core.md" %}

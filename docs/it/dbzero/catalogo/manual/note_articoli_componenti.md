## 📘 Documentazione Concettuale – Tabella `catalogo.note_articoli_componenti`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)
> • [catalogo.note_articoli](/dbzero/catalogo/tabelle/note_articoli)
> • [vendite.note](/dbzero/vendite/tabelle/note)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

**Partizione** delle note per `catalogo.articoli_componenti`, cioè per le righe di **distinta
base** — non per gli articoli.

Il documento principale del meccanismo è **[vendite.note](/dbzero/vendite/tabelle/note)**.

Contiene 3 righe al 2026-08-21.

---

### ⚠️ Annota il **legame**, non il componente

È la distinzione che il nome non rende evidente. `catalogo.articoli_componenti` è la riga di
distinta: *questo componente, in questa quantità, dentro questo padre*. Una nota qui riguarda
quel legame specifico.

Per annotare il componente **in quanto articolo** — una proprietà che vale ovunque compaia —
si usa `catalogo.note_articoli`, con l'`articolo_id` del componente.

⚠️ Le due cose si confondono facilmente, e producono note che compaiono nel posto sbagliato:
una nota di distinta non segue il componente quando è venduto da solo, e una nota di articolo
compare su **tutti** i padri che lo includono.

---

### La conseguenza sulla BoM

Le note di distinta sono legate a righe che il progetto tratta come **struttura immutabile
quando la BoM è attiva** (`trgfn_articoli_componenti_block_modifica_struttura`).

⚠️ Va tenuto presente scrivendo le fixture: creare una nota di distinta richiede che la riga
di componente esista già, e modificarne la struttura dopo può essere vietato dal guard.

---

{% include-markdown "signature-core.md" %}

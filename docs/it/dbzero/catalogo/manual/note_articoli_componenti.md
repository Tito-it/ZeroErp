## 📘 Documentazione Concettuale – Tabella `catalogo.note_articoli_componenti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti) — il legame di distinta che queste note annotano
> * [catalogo.note](/dbzero/catalogo/tabelle/note) — la tabella madre delle partizioni di catalogo
> * [catalogo.note_articoli](/dbzero/catalogo/tabelle/note_articoli) — la partizione gemella, per gli articoli
> * [vendite.note](/dbzero/vendite/tabelle/note) — il meccanismo delle note, documentato per intero
>
> Approfondimento viste:
>
> * [catalogo.vw_articoli_componenti_note](/dbzero/catalogo/views/vw_articoli_componenti_note) — la lettura di queste note con padre, componente, stile e lingua

---

### 🎯 Scopo Principale

La partizione delle note di catalogo che annotano un legame di distinta base ([catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)): il componente dentro un padre, non il componente come articolo.

---

{% include-markdown "it/dbzero/catalogo/_note-partizioni.md" %}

---

### ⚠️ Annota il legame, non il componente

`catalogo.articoli_componenti` è la riga di distinta: questo componente, in questa quantità,
dentro questo padre, in questo periodo. Una nota qui riguarda quel legame soltanto, e non segue
il componente quando è venduto da solo o quando compare in un altro padre.

Per annotare il componente in quanto articolo, una proprietà che vale ovunque compaia, si usa
[catalogo.note_articoli](/dbzero/catalogo/tabelle/note_articoli) con l'articolo del componente.
Sceglierne una per l'altra produce note che compaiono nel posto sbagliato in stampa.

---

### ⚠️ Il legame non si cancella mai, e con una nota non si spegne

Il legame di distinta è struttura immutabile
([catalogo.trgfn_articoli_componenti_block_modifica_struttura](/dbzero/catalogo/funzioni/trgfn_articoli_componenti_block_modifica_struttura)):
la sua cancellazione è sempre rifiutata con `E_BOM_MODIFICA_VIETATA`, e per correggerlo lo si
chiude con `valido_al` e se ne apre uno nuovo. La cascata che porterebbe via le note, quindi,
su questa partizione non scatta mai.

Insieme al blocco della disattivazione, ne segue che un legame con una nota si può soltanto
chiudere nel tempo: non si cancella e non si spegne. Le note restano libere: si aggiungono e si
correggono anche su un legame chiuso, purché sia attivo.

---

{% include-markdown "signature-core.md" %}

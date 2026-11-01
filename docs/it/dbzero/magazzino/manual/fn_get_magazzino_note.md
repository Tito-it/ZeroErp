## 📘 Documentazione Concettuale – Funzione `magazzino.fn_get_magazzino_note`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.note](/dbzero/magazzino/tabelle/note) — le note che legge
>
> Approfondimento funzioni:
>
> * [script.fn_get_note](/dbzero/script/funzioni/fn_get_note) — il lettore generico che usano gli altri domini

---

### 🎯 Scopo Principale

Estrae le note di un documento di magazzino dalla tabella `magazzino.note`, con
la stessa firma dei lettori di note degli altri domini.

Ordina prima le note di testata, poi quelle di riga, e dentro ciascun gruppo per
posizione e sequenza: è l'ordine naturale di stampa.

⚠️ A differenza di `acquisti.fn_get_acquisti_note` e `vendite.fn_get_vendite_note`,
**non delega** a `script.fn_get_note`: legge `magazzino.note` da sé, con filtri e
ordinamento scritti nel proprio corpo. La forma è la stessa del lettore
generico, ma è una copia della sua logica.

---

### I parametri che contano

`_include_doc` e `_include_righe` decidono se raccogliere le note di testata, quelle di riga o
entrambe; `_only_visible` filtra quelle non visibili. I valori predefiniti (tutti e tre veri)
danno il comportamento di stampa: tutto ciò che l'utente deve vedere. Il tipo del documento si
confronta in maiuscolo, comunque lo si scriva.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}

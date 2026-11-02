## 📘 Documentazione Concettuale – Funzione `magazzino.fn_get_magazzino_note`

> **Ultimo aggiornamento**: 1 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [magazzino.note](/dbzero/magazzino/tabelle/note) — le note che legge
> * [config.note_stili](/dbzero/config/tabelle/note_stili) e [config.lingue](/dbzero/config/tabelle/lingue) — i vocabolari da cui escono stile e lingua
>
> Approfondimento funzioni:
>
> * [script.fn_get_note](/dbzero/script/funzioni/fn_get_note) — il lettore comune, dove sta la regola
> * [vendite.fn_get_vendite_note](/dbzero/vendite/funzioni/fn_get_vendite_note) e [acquisti.fn_get_acquisti_note](/dbzero/acquisti/funzioni/fn_get_acquisti_note) — le gemelle degli altri domini

---

### 🎯 Scopo Principale

Estrae le note di un documento di magazzino: è l'involucro del lettore comune delle note,
applicato alla tabella `magazzino.note`, con la stessa firma e lo stesso risultato delle
gemelle di vendite e acquisti.

Non contiene nessuna regola propria: filtri, ordinamento e risoluzione di stile e lingua li
decide `script.fn_get_note`, uno solo per tutte le famiglie di note.

---

### I parametri che contano

`_include_doc` e `_include_righe` decidono se raccogliere le note di testata, quelle di riga o
entrambe; `_only_visible` filtra quelle non visibili. I valori predefiniti (tutti e tre veri)
danno il comportamento di stampa: tutto ciò che l'utente deve vedere. Il tipo del documento è il
codice della grammatica dei tipi (`INVENTARIO`, `TRASFERIMENTO_RIGA`…) e si confronta in
maiuscolo, comunque lo si scriva.

---

### Note di migrazione

* 2026-11-01 — diventa un involucro di `script.fn_get_note`. Prima ne era una copia scritta a
  parte, perché le note di magazzino tenevano stile e lingua come testo; da quel giorno hanno la
  forma delle altre note (riferimenti ai vocabolari) e la copia si ritira. Il risultato prende i
  tipi delle gemelle: tipo, ancoraggio e posizione escono come testo.

---

{% include-markdown "it/dbzero/magazzino/_dominio-magazzino.md" %}

---

{% include-markdown "signature-core.md" %}

## 📘 Documentazione Concettuale – Funzione `pratiche.fn_pratica_del_documento`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche_sorgenti](/dbzero/pratiche/tabelle/pratiche_sorgenti) — i collegamenti fra pratiche e documenti, da cui conta
>
> Approfondimento funzioni:
>
> * [vendite.fn_documento_lineage_sintesi](/dbzero/vendite/funzioni/fn_documento_lineage_sintesi) — la sintesi della lineage, che la legge per ogni nodo
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga

---

### 🎯 Scopo Principale

La pratica di un documento: quante pratiche lo hanno fra le sorgenti, la prima (per id) e il suo
codice. Una riga sempre: senza pratiche il conteggio è 0 e le altre colonne sono vuote.

È la sede unica di questa regola: la leggono per chiave le sette viste di lista di `vendite`
(`vw_*_lista`, dove la pratica è filtrabile e ordinabile, nelle colonne `pratica_id`,
`pratica_numero`, `n_pratiche`) e la sintesi della lineage.

---

### Il documento si passa con le colonne del modello

Il documento si indica come lo scrive il modello della provenienza: il tipo (`config.sorgenti`),
`sorgente_id` e `sorgente_uid`. I collegamenti si cercano con la **regola d'incontro**: un
collegamento vale se il suo `sorgente_id` è quello passato **oppure** il suo `sorgente_uid` è quello
passato.

* Chi ha il documento in mano (una lista) passa il suo id **e** il suo uid: la regola trova il
  collegamento qualunque sia la chiave del tipo.
* Chi ha solo la chiave del modello passa quella, e vuoto nell'altra.
* ⚠️ Una chiave che non è quella del tipo non trova niente: l'uid di un ordine da solo dà 0, perché
  l'ordine si riconosce dall'id. Non è un errore, è la regola.

La sintesi della lineage, che ha il nodo come chiave in testo, la converte prima con
`script.fn_sorgente_chiave_id` e `script.fn_sorgente_chiave_uuid` e passa le due.

---

### Test

* `db/pgtap/pratiche/test-sorgente-pratiche-sorgenti-v1.sql` — la firma unica sulle colonne del
  modello; la pratica trovata con id e uid del documento o con la sola chiave del modello, per
  preventivo e ordine; le liste e la sintesi della lineage che la mostrano.

---

### Note di migrazione

* 2026-10-11 — nasce come sede unica della pratica di un documento, prima calcolata dentro la
  sintesi della lineage (`brief-db-lineage-seminata-per-chiave`).
* 2026-11-08 — la firma con la chiave in testo è ritirata: il documento si passa con tipo,
  `sorgente_id` e `sorgente_uid`, come `pratiche.pratiche_sorgenti` lo scrive
  (`brief-db-sorgente-documento-e-riga`).

---
{% include-markdown "signature-core.md" %}

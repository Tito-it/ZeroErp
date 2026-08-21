## 📘 Documentazione Concettuale – Funzione `script.fn_norm_via`

> 👀 **Vedi anche**
>
> • [script.fn_norm_testo](/dbzero/script/funzioni/fn_norm_testo)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Compone **toponimo e nome della via** in un'unica stringa normalizzata, delegando a
`script.fn_norm_testo`.

Il corpo è una riga: `fn_norm_testo(coalesce(topo,'') || ' ' || coalesce(via,''))`.

⭐ I due `coalesce` sono la sostanza: senza, un toponimo nullo renderebbe `NULL` l'intera
concatenazione — e in un indice di espressione significa **riga non indicizzata**, quindi
invisibile alle ricerche che usano quell'indice. Un dato mancante non deve far sparire il
resto.

Anche questa è `IMMUTABLE`, per la stessa ragione della funzione che chiama.

---

{% include-markdown "signature-core.md" %}

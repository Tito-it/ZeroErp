## 📘 Documentazione Concettuale – Funzione `vendite.fn_versioni_listino_da_chiudere(p_versione_id)`

> 👀 **Vedi anche**
>
> [vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino) ·
> [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)

### 🎯 Scopo
(28-10-2026 — brief `brief-modello-documento-vendita` §16, L-4)

**Le versioni che l'attivazione di una versione chiude**, con la fine che prenderebbero.

### Regole

* Sono le versioni dello stesso listino, accese, in stato ATTIVA, con decorrenza precedente a
  quella della versione da attivare e periodo che la tocca.
* Prendono la fine al giorno prima della decorrenza nuova (`valido_al_dopo`).
* Ordinate per decorrenza. Sotto RLS (`SECURITY INVOKER`): i soli listini del perimetro.

La usano il verbo dell'attivazione, per chiuderle, e il backend, per l'anteprima del dialogo
di conferma: una regola sola.

---

{% include-markdown "signature-core.md" %}

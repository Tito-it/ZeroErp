## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_template_flussi_default_definizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — lo step di template che riceve l'edizione
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le edizioni di una definizione
>
> Approfondimento funzioni:
>
> * [pratiche.fn_risolvi_definizione](/dbzero/pratiche/funzioni/fn_risolvi_definizione) — l'unico punto di risoluzione dell'edizione
> * [pratiche.trgfn_pratiche_default_definizione](/dbzero/pratiche/funzioni/trgfn_pratiche_default_definizione) — la stessa regola sulle pratiche
> * [pratiche.trgfn_template_flussi_guard_immutabile](/dbzero/pratiche/funzioni/trgfn_template_flussi_guard_immutabile) — il guard che protegge un'edizione pubblicata

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_template_flussi_default_definizione` assegna un'edizione a uno step
di template inserito senza: lo step appartiene al preset pubblicato del suo tipo di prestazione.

Chi lavora su un'edizione specifica, per esempio la bozza di un fork, passa l'edizione esplicita.

---

### Le regole

* Interviene solo all'inserimento, e solo quando l'edizione manca: un valore esplicito passa intatto,
  e la FK composita (edizione, tipo di prestazione) ne garantisce già la coerenza col tipo.
* L'edizione si risolve con `pratiche.fn_risolvi_definizione` senza emittente: il preset `PUBBLICATA`
  del tipo.
* Se il tipo non ha un preset pubblicato, la risoluzione fallisce con un errore parlante.
* ⭐ Gira nella fase dei guard ma prima di loro (il nome del trigger, `default`, precede in ordine i
  `guard`): il guard di immutabilità vede già l'edizione risolta, e un passo aggiunto a un'edizione
  pubblicata, anche per default, si ferma lì. Chi configura passa dalle bozze.

L'inserimento senza edizione resta la forma dei seed e delle fixture, anche se la colonna è
obbligatoria.

---

### Codici errore

* `E_DEFINIZIONE_NON_TROVATA` — il tipo di prestazione non ha un preset pubblicato (sollevato da
  `pratiche.fn_risolvi_definizione`).

---

### Test

* `pratiche/test-workflow-definizioni-fase0` — l'inserimento senza edizione prende il preset, quello
  con l'edizione esplicita la conserva.

---

### Note di migrazione

* 2026-07-02 — nasce con le definizioni versionate, quando l'edizione dello step diventa obbligatoria
  (brief-db-step-dominio-e-definizioni-versionate).

---

{% include-markdown "signature-core.md" %}

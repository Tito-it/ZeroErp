## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_pratiche_guard_pin_immutabile`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica e il suo pin
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le edizioni di workflow
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_pratiche_default_definizione](/dbzero/pratiche/funzioni/trgfn_pratiche_default_definizione) — assegna il pin alla nascita
> * [pratiche.trgfn_flussi_guard_definizione](/dbzero/pratiche/funzioni/trgfn_flussi_guard_definizione) — tiene i flussi sull'edizione della loro pratica

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_pratiche_guard_pin_immutabile` rende definitiva l'edizione di
workflow che una pratica ha ricevuto alla nascita (`definizione_id`, il «pin»): una volta valorizzata
non cambia più.

Le pratiche in volo restano sull'edizione con cui sono nate, qualunque cosa accada dopo alle
definizioni.

---

### Le regole

* Scatta prima di un aggiornamento dell'edizione della pratica.
* È ammessa solo la prima valorizzazione, da vuoto a un valore: una pratica senza pin può riceverlo.
* Una pratica già pinnata non può cambiare edizione, né verso un'altra né verso il vuoto.
* La coerenza col tipo di prestazione la garantisce già la FK composita (edizione, tipo di
  prestazione); questo guard aggiunge l'immutabilità.

L'una assegna il pin (`pratiche.trgfn_pratiche_default_definizione`, all'inserimento), l'altra ne
impedisce la modifica. Per lavorare su un'altra edizione la pratica si ricrea: nasce col pin risolto
al momento della creazione.

---

### Codici errore

* `E_PRATICHE_PIN_IMMUTABILE` — si tenta di cambiare l'edizione di una pratica già pinnata.

---

### Test

* `pratiche/test-workflow-definizioni-fase1` — il cambio di pin di una pratica pinnata è rifiutato.

---

### Note di migrazione

* 2026-07-03 — nasce con le definizioni versionate; la prima valorizzazione resta ammessa per il
  backfill delle pratiche già esistenti (brief-db-step-dominio-e-definizioni-versionate).

---

{% include-markdown "signature-core.md" %}

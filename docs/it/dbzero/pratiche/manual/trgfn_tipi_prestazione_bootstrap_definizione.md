## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_tipi_prestazione_bootstrap_definizione`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.tipi_prestazione](/dbzero/pratiche/tabelle/tipi_prestazione) — il tipo di prestazione appena creato
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — dove nasce il suo preset
>
> Approfondimento funzioni:
>
> * [pratiche.fn_risolvi_definizione](/dbzero/pratiche/funzioni/fn_risolvi_definizione) — trova sempre il preset che questo trigger crea
> * [pratiche.fn_pubblica_definizione](/dbzero/pratiche/funzioni/fn_pubblica_definizione) — la pubblicazione con le sue validazioni, che il bootstrap non attraversa

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_tipi_prestazione_bootstrap_definizione` crea, alla nascita di un tipo
di prestazione, la sua definizione preset: versione 1, `PUBBLICATA`, senza emittente.

Regge un'invariante: ogni tipo di prestazione ha sempre un preset che `pratiche.fn_risolvi_definizione`
trova. Così l'assegnazione automatica della definizione ai template e alle pratiche trova sempre
l'edizione, e né i seed dei tipi né le fixture dei test devono creare definizioni.

---

### Le regole

* Scatta dopo l'inserimento di un tipo di prestazione, come effetto collaterale finale, e solo
  all'inserimento.
* È idempotente: se il tipo ha già una pubblicata senza emittente, non fa niente (l'indice unico «una
  sola pubblicata per perimetro» assorbe il conflitto).
* Il preset nasce pubblicato e vuoto: gli step arrivano dopo. La regola «pubblicabile solo con almeno uno
  step attivo» vale per `pratiche.fn_pubblica_definizione`, non per il bootstrap.
* Il preset porta il `tx_id` della riga del tipo.

---

### ⚠️ Perché è `SECURITY DEFINER`

`pratiche.workflow_definizioni` è in sola lettura per il ruolo applicativo: ci si scrive solo attraverso
le funzioni del dominio. Coi permessi del chiamante questo inserimento fallirebbe, e il ruolo
applicativo non potrebbe creare un tipo di prestazione. Il bootstrap non è una scrittura che l'utente
sceglie: è il dominio che si prepara da sé, a partire dal solo tipo appena nato. Il `search_path` è
fisso, e lo ereditano i trigger della tabella delle definizioni.

---

### Test

* `pratiche/test-workflow-definizioni-fase0` — il tipo nuovo nasce col suo preset pubblicato.

---

### Note di migrazione

* 2026-07-02 — nasce con le definizioni versionate; i tipi già esistenti hanno ricevuto il preset da un
  recupero una tantum (brief-db-step-dominio-e-definizioni-versionate).
* 2026-07-03 — la tabella delle definizioni diventa in sola lettura per il ruolo applicativo, e il
  trigger diventa `SECURITY DEFINER`.

---

{% include-markdown "signature-core.md" %}

## 📘 Documentazione Concettuale – Vista `pratiche.vw_definizioni_drift`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.workflow_definizioni](/dbzero/pratiche/tabelle/workflow_definizioni) — le definizioni, preset e fork
>
> Approfondimento funzioni:
>
> * [pratiche.fn_fork_definizione](/dbzero/pratiche/funzioni/fn_fork_definizione) — crea il fork e ne scrive la provenienza
> * [pratiche.fn_pubblica_definizione](/dbzero/pratiche/funzioni/fn_pubblica_definizione) — fa avanzare il preset

---

### 🎯 Scopo Principale

La vista `pratiche.vw_definizioni_drift` elenca le edizioni forkate in drift: i fork di un emittente il
cui preset d'origine ha oggi una pubblicata di versione superiore a quella da cui il fork è nato.

Alimenta il banner «preset aggiornato» con un confronto informativo. Allineare il fork al preset resta
una scelta manuale, mai automatica.

---

### Chi entra

* Solo i fork di un emittente (emittente valorizzato) che portano la provenienza: il preset d'origine e
  la versione d'origine.
* Solo le edizioni vive, in `BOZZA` o `PUBBLICATA`: una edizione ritirata non è più in drift.
* Il confronto è col **preset corrente** del tipo di prestazione, la pubblicata senza emittente: il fork
  è in drift quando la versione del preset corrente supera la sua versione d'origine.

---

### Le colonne che non si capiscono dal nome

* `versione_edizione`, `stato_edizione` — versione e stato del fork.
* `versione_origine` — la versione del preset da cui il fork è nato.
* `preset_corrente_id`, `versione_preset_corrente` — la pubblicata corrente del preset.
* `versioni_indietro` — di quante versioni il fork è rimasto indietro.

---

### Accesso

La vista è `security_invoker`: gira coi permessi di chi la legge. `pratiche.workflow_definizioni` non ha
la RLS, quindi la vista mostra i fork di tutti gli emittenti a chi può leggerla.

---

### Test

* `pratiche/test-workflow-definizioni-fase2` — il fork compare quando il preset avanza.

---

### Note di migrazione

* 2026-07-03 — nasce con i fork delle definizioni (brief-db-step-dominio-e-definizioni-versionate).

---

{% include-markdown "signature-core.md" %}

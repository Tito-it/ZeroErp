## 📘 Documentazione Concettuale – Tabella `pratiche.template_flussi_prerequisiti`

> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi)
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi)

---

### 🎯 Scopo Principale

La tabella `pratiche.template_flussi_prerequisiti` definisce il **grafo diretto aciclico (DAG) dei prerequisiti** tra template flussi. Un flusso puo' essere creato solo se tutti i suoi prerequisiti sono stati completati.

---

### 🧱 Ruolo nel processo

* Configura le **dipendenze** tra step del workflow: "il flusso B richiede il completamento del flusso A".
* Il trigger guard `trg_flussi_a10_guard_prerequisiti_ins` (DB-5) verifica i prerequisiti al momento della creazione di un flusso.
* La funzione `pratiche.fn_check_prerequisiti_flusso()` (DB-5) consente la verifica lato API/UI senza tentare l'inserimento.

---

### ⚙️ Caratteristiche

| Aspetto | Dettaglio |
|---------|-----------|
| **Relazione** | Immutabile: si cancella e ricrea (no UPDATE). |
| **Audit** | Solo `data_insert/user_insert` — coerente con l'immutabilita'. |
| **Self-reference** | CHECK `template_flusso_id <> prerequisito_id` impedisce auto-riferimenti. |
| **FK ON DELETE** | CASCADE — se un template flusso viene rimosso, i suoi prerequisiti spariscono. |

---

### 💡 Esempio

Per un tipo_prestazione "Allacciamento" con 3 step:

| template_flusso_id | prerequisito_id | Significato |
|--------------------|-----------------|-------------|
| Sopralluogo (id=2) | Richiesta (id=1) | Il sopralluogo richiede la richiesta completata |
| Esecuzione (id=3) | Sopralluogo (id=2) | L'esecuzione richiede il sopralluogo completato |

---

{% include-markdown "signature-core.md" %}

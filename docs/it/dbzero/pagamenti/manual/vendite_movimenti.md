## 📘 Documentazione Concettuale – Tabella `pagamenti.vendite_movimenti`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
>
---

### 🎯 Scopo Principale

(latest review 10-02-2026)  
`pagamenti.vendite_movimenti` registra i **movimenti di incasso/rimborso**
associati alle fatture di vendita. Supporta piu` movimenti per fattura
ed e` la base per determinare lo stato di pagamento.

---

### 🧱 Campi chiave (semantica)

* `fattura_id`: fattura di riferimento.
* `billing_account_id`: denormalizzato per filtri veloci.
* `data_effettiva`: data di incasso/rimborso.
* `data_registrazione`: data di registrazione.
* `data_contabile`: data contabile (opzionale).
* `importo`: positivo = incasso, negativo = rimborso/storno.
* `meta`: dettagli esterni (es. riferimento bonifico).

---

### ✅ Note operative

* Il pagamento puo` essere parziale (piu` movimenti).
* Una fattura e` considerata **pagata** quando `SUM(importo) >= totale_a_pagare`
  (policy da formalizzare in logica applicativa).

---

{% include-markdown "signature-core.md" %}

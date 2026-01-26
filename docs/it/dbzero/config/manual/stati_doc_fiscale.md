## 📘 Documentazione Concettuale – Tabella `config.stati_doc_fiscale`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**    
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)     
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)     
>
---

### 🎯 Scopo Principale

(latest review 23-01-2026)
`config.stati_doc_fiscale` definisce gli **stati documento** utilizzati dal ciclo
fatturazione. Gli stessi stati possono essere applicati sia alle **fatture** sia
ai **lotti**, tramite flag di applicabilita`.

---

### 🧱 Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` (progressione di stato).
* **Applicabilita`**:
  * `applica_fattura` → stato valido per `vendite.fatture`.
  * `applica_lotto` → stato valido per `vendite.fatturazione_lotti`.
* **Governance**: `attivo`, `meta`.

---

### ✅ Regole operative

* Gli stati **possono essere condivisi** tra lotto e fattura, ma vanno marcati con i flag.
* Le **transizioni ammesse** sono definite in `config.stati_doc_fiscale_transizioni`.

---

{% include-markdown "signature-core.md" %}

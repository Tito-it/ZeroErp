## 📘 Documentazione Concettuale – Tabella `config.stati_doc_fiscale_transizioni`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale)  
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
---

### 🎯 Scopo Principale

(latest review 24-01-2026)
`config.stati_doc_fiscale_transizioni` definisce le **transizioni ammesse** tra stati
documento, con validita` separata per **lotti** e **fatture**.

---

### 🧱 Campi chiave (semantica)

* **Transizione**: `stato_from_id` → `stato_to_id`.
* **Ammissibilita`**: `ammesso` (TRUE/FALSE).
* **Scope**:
  * `solo_lotto` → transizione valida solo per i lotti;
  * `solo_fattura` → transizione valida solo per le fatture.
* **Governance**: `meta`, audit.

---

### ✅ Note operative

* I guard di stato su `fatture` e `fatturazione_lotti` usano questa tabella.
* La tabella sostituisce i flag generici di rollback.

---

{% include-markdown "signature-core.md" %}

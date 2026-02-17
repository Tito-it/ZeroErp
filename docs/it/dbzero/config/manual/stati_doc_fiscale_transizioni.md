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
* Se `meta.tipo_lotto` e` valorizzato (es. `MASSIVO`, `GIORNALIERO`),
  la transizione e` ammessa **solo** per lotti con lo stesso `tipo_lotto`.
* Se una transizione deve valere per **piu` tipi lotto** con la stessa coppia
  `stato_from_id -> stato_to_id` (es. `DEFINITIVA -> INVIATA`), **non**
  valorizzare `meta.tipo_lotto` e usare `meta = {}`.
  Questo evita duplicati sul vincolo unico
  `(stato_from_id, stato_to_id, solo_lotto, solo_fattura)`.
* La tabella sostituisce i flag generici di rollback.

---

{% include-markdown "signature-core.md" %}

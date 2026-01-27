## 📘 Documentazione Concettuale – Tabella `vendite.tipi_doc_fiscale_registri`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
>
---

### 🎯 Scopo Principale

(latest review 27-01-2026)
La tabella **`vendite.tipi_doc_fiscale_registri`** definisce il mapping
**tipo documento fiscale → registro di fatturazione**, necessario per la
numerazione e la contabilizzazione dei documenti.

---

### 🧩 Campi chiave

* `tipo_doc_fiscale_id` → tipo documento fiscale (FK).
* `registro_id` → registro di fatturazione associato (FK).
* `codice_interno` → codice di servizio del mapping (opzionale).

---

### ✅ Regole principali

* mapping **univoco** per `tipo_doc_fiscale_id`.
* usato dalle funzioni di risoluzione del registro (`vendite.fn_get_registro_id`).

---

{% include-markdown "signature-core.md" %}

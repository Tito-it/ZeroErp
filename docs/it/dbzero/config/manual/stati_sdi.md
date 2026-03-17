## 📘 Documentazione Concettuale – Tabella `config.stati_sdi`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
>
🎯 Scopo Principale

(latest review 23-01-2026)
`config.stati_sdi` definisce gli **stati di invio SDI** (Italia) utilizzati per
tracciare l’esito di trasmissione dei documenti fiscali.

---

### Campi chiave (semantica)

* **Identita` stato**: `id`, `codice`, `codice_interno`.
* **Ordine**: `ordine` (progressione stato SDI).
* **Governance**: `attivo`, `meta`.

---

### Utilizzo

* Lo stato SDI e` collegato alla relazione lotto‑fattura tramite
  `vendite.fatturazione_lotti_fatture.stato_sdi_id`.
* E` separato dallo stato documento (`config.stati_doc_fiscale`).

---

{% include-markdown "signature-core.md" %}

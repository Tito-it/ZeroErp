## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_lotti_fatture`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
🎯 Scopo Principale

(latest review 23-01-2026)
`vendite.fatturazione_lotti_fatture` rappresenta la **relazione esplicita** tra lotto e fattura,
consentendo di:

* tracciare l’appartenenza del documento a un lotto;
* tracciare lo stato documento fiscale per-fattura nel lotto (`stato_doc_fiscale_id`);
* tracciare l’esito tecnico per-fattura nel lotto (`stato_esecuzione`);
* gestire eventuali esclusioni (`esclusa = true`);
* ospitare lo **stato SDI** (quando introdotto in `config.stati_sdi`).

---

### Campi chiave (semantica)

* **Relazione**: `lotto_id`, `fattura_id`.
* **Snapshot stato documento**: `stato_doc_fiscale_id` (FK -> `config.stati_doc_fiscale`).
* **Esito esecuzione per-fattura**: `stato_esecuzione` (`OK` | `ERRORE`).
* **Esclusione**: `esclusa` (boolean).
* **Stato SDI**: `stato_sdi_id` (FK -> `config.stati_sdi`).
* **Governance**: `meta`, `storicizza`, `tx_id`, audit `data_*`/`user_*`.

---

### Regole operative (policy)

* `esclusa = true` ammesso **solo** se la fattura e` in stato **DRAFT**.
* `stato_esecuzione` e` coerente con `fatture.critical` durante la sync lotto-fatture.
* La tabella e` il punto di estensione per metadati futuri legati al lotto.

---

{% include-markdown "signature-core.md" %}

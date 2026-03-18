## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_lotti_log`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
>
### 🎯 Scopo Principale
(latest review 28-01-2026)
`vendite.fatturazione_lotti_log` registra **warning** e **errori critici**
relativi ai processi del lotto di fatturazione.

---

### Campi chiave (semantica)

* **Contesto**: `lotto_id`.
* **Evento**: `data_ora`, `messaggio`.
* **Severita`**: `status` (I=info, W=warning, C=critical).
* **Gestione**: `disabilitato` (TRUE se ignorato dall’operatore).
* **Governance**: `meta`, audit.
* **Pipeline**: `fase` (descrizione step) e `stato_doc_fiscale_id`.
* **Contesto lotto**: `tipo_lotto`, `stato_operativo` (snapshot al momento del log).

---

### Note operative

* Tabella dedicata al **lotto fatturazione**, distinta da `fatture_log`.
* I record con `status = I` possono essere usati per mostrare l’avanzamento
  della pipeline (es. “caricamento lista”, “generazione righe”).
* Non contiene il dettaglio documento (`fattura_id`): gli errori per-fattura
  restano in `vendite.fatture_log`.
* `DELETE` diretto bloccato: consentito solo con GUC
  `zeroerp.maintenance_allow_delete_logs = on`
  (compatibile con GUC tecnica `zeroerp.maintenance_reset_lotto_draft = on`).

---

{% include-markdown "signature-core.md" %}

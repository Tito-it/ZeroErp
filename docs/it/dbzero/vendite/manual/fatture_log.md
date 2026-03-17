## 📘 Documentazione Concettuale – Tabella `vendite.fatture_log`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
🎯 Scopo Principale

(latest review 29-01-2026)  
`vendite.fatture_log` registra **warning** e **errori critici** associati ai
documenti di fattura. I log critici bloccano numerazione e invio finche` attivi.

---

### Campi chiave (semantica)

* **Contesto**: `fattura_id`.
* **Evento**: `data_ora`, `messaggio`.
* **Severita`**: `status` (W=warning, C=critical).
* **Gestione**: `disabilitato` (TRUE se ignorato dall’operatore).
* **Governance**: `meta`, audit.

---

### Note operative

* Più log possono essere associati alla stessa fattura.
* Se esiste almeno un log **critical** attivo, `fatture.critical = true`.
* `disabilitato = true` esclude il log dal calcolo del flag `critical`.
* La disabilitazione di un log **critical** richiede conferma esplicita.
* Trigger automatici su `INSERT/UPDATE/DELETE` sincronizzano:
  * `vendite.fatture.critical`
  * `vendite.fatturazione_lotti_fatture.stato_esecuzione` (`ERRORE`/`OK`)
    solo per lotti `IN_ESECUZIONE` o `APERTO`.
* `DELETE` diretto bloccato: consentito solo con GUC
  `zeroerp.maintenance_allow_delete_logs = on`
  (compatibile con GUC tecnica `zeroerp.maintenance_reset_lotto_draft = on`).

---

{% include-markdown "signature-core.md" %}

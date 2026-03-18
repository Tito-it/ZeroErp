## 📘 Documentazione Concettuale – Tabella `vendite.attivita_fatturabili_log`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.attivita_fatturabili_lotti](/dbzero/vendite/tabelle/attivita_fatturabili_lotti)  
> • [vendite.attivita_consumi](/dbzero/vendite/tabelle/attivita_consumi)  
>
### 🎯 Scopo Principale
(latest review 24-01-2026)
`vendite.attivita_fatturabili_log` registra **warning** e **errori critici**
relativi ai processi di alimentazione di `attivita_fatturabili`.

---

### Campi chiave (semantica)

* **Contesto**: `lotto_attivita_id`, `attivita_consumi_id`.
* **Evento**: `data_ora`, `messaggio`.
* **Severita`**: `status` (W=warning, C=critical).
* **Gestione**: `disabilitato` (TRUE se ignorato dall’operatore).
* **Governance**: `meta`, audit.

---

### Note operative

* La tabella e` dedicata alla **fase di alimentazione**, separata dal log fatture.

---

{% include-markdown "signature-core.md" %}

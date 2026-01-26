## 📘 Documentazione Concettuale – Tabella `vendite.fatturazione_lotti_log`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
>
---

### 🎯 Scopo Principale

(latest review 24-01-2026)
`vendite.fatturazione_lotti_log` registra **warning** e **errori critici**
relativi ai processi del lotto di fatturazione.

---

### 🧱 Campi chiave (semantica)

* **Contesto**: `lotto_id`.
* **Evento**: `data_ora`, `messaggio`.
* **Severita`**: `status` (W=warning, C=critical).
* **Gestione**: `disabilitato` (TRUE se ignorato dall’operatore).
* **Governance**: `meta`, audit.

---

### ✅ Note operative

* Tabella dedicata al **lotto fatturazione**, distinta da `fatture_log`.

---

{% include-markdown "signature-core.md" %}

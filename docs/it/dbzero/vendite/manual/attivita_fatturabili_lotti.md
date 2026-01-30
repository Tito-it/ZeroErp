## 📘 Documentazione Concettuale – Tabella `vendite.attivita_fatturabili_lotti`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [config.sorgenti](/dbzero/config/tabelle/sorgenti)  
> • [config.utilities](/dbzero/config/tabelle/utilities)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
>
---

### 🎯 Scopo Principale

(latest review 24-01-2026)
`vendite.attivita_fatturabili_lotti` rappresenta il **batch di alimentazione**
per la generazione di `attivita_fatturabili`. E` usato per processi automatici
(consumi, conguagli, calcoli utilities) e per tracciabilita` in dashboard.

---

### 🧱 Campi chiave (semantica)

* **Identita` lotto**: `id`, `lock_batch_id`, `codice`.
* **Parametri**: `competenza_mese`, `utility_id`, `billing_account_id`, `sorgente_tipo_id`.
* **Stato**: `stato_lotto` (IN_ESECUZIONE | COMPLETATO | ERRORE).
* **Governance**: `meta`, `storicizza`, `tx_id`, audit `data_*`/`user_*`.

---

### ✅ Best practice operative

* Usare `lock_batch_id` per isolamento di processo.
* Collegare le righe generate in `attivita_fatturabili` via `lotto_attivita_id`.

---

{% include-markdown "signature-core.md" %}

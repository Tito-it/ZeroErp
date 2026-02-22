## 📘 Documentazione Concettuale – Funzione `vendite.fn_sync_attivita_stato_esecuzione`

---

### 🎯 Scopo Principale

(latest review 22-02-2026)
Sincronizza `stato_esecuzione` delle righe `attivita_fatturabili` collegate a un lotto attività.

---

### 🔧 Regole applicate

* Supporta target esplicito opzionale (`p_target_stato_esecuzione`).
* Se target non passato, deduce da `stato_lotto`:
  * `IN_ESECUZIONE -> RUNNING`
  * `COMPLETATO -> COMPLETED`
  * `ERRORE -> ERRORE`
  * fallback `PENDING`
* Le attività con `fatturato = true` vengono sempre poste a `COMPLETED`.

---

### ✅ Output

Non ritorna record (`RETURNS void`).

---

{% include-markdown "signature-core.md" %}

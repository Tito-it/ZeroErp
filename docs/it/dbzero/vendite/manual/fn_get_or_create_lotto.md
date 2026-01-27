## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_or_create_lotto`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
>
---

### 🎯 Scopo Principale

(latest review 27-01-2026)
La funzione **`vendite.fn_get_or_create_lotto()`** recupera un lotto esistente
(o lo crea se assente) garantendo la coerenza dei parametri di richiesta.

---

### 🔧 Regole applicate

* Se `p_lotto_id` e` valorizzato:
  * verifica l’esistenza del lotto;
  * valida la coerenza di `competenza_mese`, `utility_id`, `tipo_doc_fiscale_id`, `billing_account_id`.
* Se `p_lock_batch_id` e` valorizzato e non esiste un lotto, ne crea uno nuovo.
* Se non e` presente nessun riferimento, delega a `fn_create_fatturazione_lotto`.

---

### ✅ Output

Ritorna l’`id` del lotto esistente o creato.

---

{% include-markdown "signature-core.md" %}

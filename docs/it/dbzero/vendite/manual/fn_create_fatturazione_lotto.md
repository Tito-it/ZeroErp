## 📘 Documentazione Concettuale – Funzione `vendite.fn_create_fatturazione_lotto`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)   
> • [config.utilities](/dbzero/config/tabelle/utilities)   
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)   
> • [vendite.tipi_doc_fiscale_registri](/dbzero/vendite/manual/tipi_doc_fiscale_registri)   
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_get_or_create_lotto](/dbzero/vendite/funzioni/fn_get_or_create_lotto)   
>
---

### 🎯 Scopo Principale

(latest review 27-01-2026)
La funzione **`vendite.fn_create_fatturazione_lotto()`** crea un lotto di
fatturazione con parametri coerenti (competenza, utility, tipo documento, BA) e
inizializza lo stato documento a **DRAFT**.

---

### 🔧 Regole applicate

* `competenza_mese` e` **obbligatoria** e viene normalizzata al primo del mese.
* `utility_id` e` obbligatoria: se `billing_account_id` e` presente viene ricavata da BA.
* `tipo_doc_fiscale_id` e` **obbligatorio** e deve essere attivo.
* Deve esistere il mapping `tipo_doc_fiscale → registro` in `vendite.tipi_doc_fiscale_registri`.
* `stato_doc_fiscale_id` viene impostato su **DRAFT** (solo se applicabile al lotto).
* `lock_batch_id` viene generato se non fornito.

---

### ✅ Output

Ritorna l’`id` del lotto creato in `vendite.fatturazione_lotti`.

---

{% include-markdown "signature-core.md" %}

## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_valuta_id`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
> • [config.utilities](/dbzero/config/tabelle/utilities)  
> • [anagrafiche.gestori](/dbzero/anagrafiche/tabelle/gestori)  
> • [config.valute](/dbzero/config/tabelle/valute)  
>
---

### 🎯 Scopo Principale

(latest review 26-01-2026)
La funzione **`vendite.fn_get_valuta_id`** risolve la valuta con fallback
al **gestore** quando non esistono valori specifici su BA/utility.

---

### 🔍 Parametri di input

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `p_billing_account_id` | `anagrafiche.billing_account.id%TYPE` | Billing account (opzionale). |
| `p_utility_id` | `config.utilities.id%TYPE` | Utility di riferimento (opzionale). |

---

### ✅ Regola applicata

1. Se il BA ha una valuta configurata (se prevista) usa quella.
2. Altrimenti usa `config.utilities.valuta_id` (se prevista).
3. In fallback usa la valuta del **gestore** attivo.
4. Se ancora NULL → errore bloccante.

---

### ✅ Note operative

* Funzione pensata per l’alimentazione di `attivita_fatturabili` e per calcoli pre‑fattura.
* Al momento il fallback effettivo e` il **gestore**; BA/utility sono opzionali.

---

{% include-markdown "signature-core.md" %}

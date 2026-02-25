## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_commessa_stato`

### 🎯 Scopo Principale

(latest review 24-02-2026)
Restituisce stato testata commessa e contatori principali delle sue righe in un solo round-trip DB.

---

### 🔧 Regole applicate

* `commessa_id` obbligatorio.
* Errore esplicito se la commessa non esiste.
* Espone contatori utili per orchestrazione backend:
  `total_attivita`, `total_approvate`, `total_emesse`, `total_prezzo_da_riallineare`.

---

### ✅ Output

Una riga con stato e metriche aggregate della commessa.

---

{% include-markdown "signature-core.md" %}

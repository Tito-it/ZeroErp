## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_or_create_commessa`

### 🎯 Scopo Principale

(latest review 24-02-2026)
Recupera una commessa aperta coerente con i parametri in ingresso oppure ne crea una nuova.

---

### 🔧 Regole applicate

* `billing_account_id` e `utility_id` obbligatori.
* Verifica coerenza tra utility passata e utility del billing account.
* Risolve fallback `emittente_soggetto_ruolo_id` con `anagrafiche.fn_get_emittente_fiscale_id(...)`.
* Se `p_force_new = false`, tenta il riuso di una commessa con stessa chiave funzionale.
* Se non trova match (o `p_force_new = true`) crea una nuova commessa in stato `BOZZA`.

---

### ✅ Output

Ritorna `commessa_id` (esistente o creata).

---

{% include-markdown "signature-core.md" %}

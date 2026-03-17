## 📘 Documentazione Concettuale – Funzione `vendite.fn_resolve_lotto_utility_emittente`

---

### 🎯 Scopo Principale

(latest review 22-02-2026)
Helper condiviso per risolvere e validare `utility_id` ed `emittente_soggetto_ruolo_id` nei flussi lotto (`fatturazione_lotti` e `attivita_fatturabili_lotti`).

---

### Regole applicate

* Se `billing_account_id` presente:
  * risolve `utility_id` dal BA e ne valida la coerenza con input.
  * risolve emittente via `anagrafiche.fn_get_emittente_fiscale_id` (fallback default incluso).
* Se emittente passato esplicitamente con BA presente, deve coincidere con quello risolto.
* Può validare che l'emittente risolto sia attivo (`p_check_emittente_attivo=true`).

---

### Output

Ritorna una riga con:

* `resolved_utility_id`
* `resolved_emittente_soggetto_ruolo_id`

---

{% include-markdown "signature-core.md" %}

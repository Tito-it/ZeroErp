## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_emittenti_fiscali_guard_attivo`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/tabelle/emittenti_fiscali)
> • [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/tabelle/emittenti_fiscali_billing_account)
>
---

### 🎯 Scopo Principale

(latest review 23-01-26)
La funzione **`anagrafiche.trgfn_emittenti_fiscali_guard_attivo()`** impedisce
la disattivazione (`attivo = false`) di un emittente fiscale quando esistono
righe di mapping in `emittenti_fiscali_billing_account` collegate al suo
`emittente_soggetto_ruolo_id`.

---

### 🔍 Regola applicata

* **Evento**: `BEFORE UPDATE OF attivo` su `anagrafiche.emittenti_fiscali`.
* Se `attivo` passa da **true** a **false** e sono presenti mapping associati:
  * la modifica viene **bloccata** con `script.fn_log_and_raise_error`.

---

### ✅ Motivazione

Garantisce coerenza tra configurazione emittenti e mapping billing account:
non si disattiva un emittente ancora in uso.

---

{% include-markdown "signature-core.md" %}

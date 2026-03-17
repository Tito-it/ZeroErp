## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_resellers_guard_attivo`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [anagrafiche.resellers](/dbzero/anagrafiche/tabelle/resellers)  
> • [anagrafiche.resellers_billing_account](/dbzero/anagrafiche/tabelle/resellers_billing_account)  
>
🎯 Scopo Principale

(latest review 26-01-2026)
La funzione **`anagrafiche.trgfn_resellers_guard_attivo()`** impedisce la
**disattivazione** di un reseller quando esistono mapping verso
`resellers_billing_account`.

---

### Regola applicata

* Trigger **BEFORE UPDATE OF attivo** su `anagrafiche.resellers`.
* Se `attivo` passa a `false` e sono presenti righe in
  `resellers_billing_account` per lo stesso `soggetto_ruolo_id`, l’operazione
  viene bloccata con `script.fn_log_and_raise_error`.

---

### Ruolo nel processo

La guard evita che un reseller diventi inattivo mentre risulta ancora associato
ad uno o piu` billing account.

---

{% include-markdown "signature-core.md" %}

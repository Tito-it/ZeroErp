## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_get_emittente_fiscale_id()`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account)    
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/manual/emittenti_fiscali)    
>

🎯 Scopo Principale

(last review 23-01-2026)
La funzione `anagrafiche.fn_get_emittente_fiscale_id()` risolve l’emittente fiscale
associato a un `billing_account`. Se non esiste un mapping specifico,
usa l’emittente **di default globale**.

---

### Regole applicate

1. Cerca un mapping specifico per `billing_account_id`.
2. Se assente, usa la riga con `is_default = true`.
3. Se il default manca, la funzione blocca tramite `script.fn_log_and_raise_error(...)`.

---

{% include-markdown "signature-core.md" %}

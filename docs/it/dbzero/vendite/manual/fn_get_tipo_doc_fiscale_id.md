## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_tipo_doc_fiscale_id`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [config.sorgenti](/dbzero/config/tabelle/sorgenti)  
> • [config.utilities](/dbzero/config/tabelle/utilities)  
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
>
**Approfondimento funzioni:**
>
• [vendite.trgfn_attivita_fatturabili_normalize](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_normalize)  
>
🎯 Scopo Principale

(latest review 27-01-2026)
La funzione **`vendite.fn_get_tipo_doc_fiscale_id`** risolve il tipo documento
fiscale a partire dalla sorgente o dalla utility.

---

### Regola applicata

1. Se `config.sorgenti.tipo_doc_fiscale_id` e` valorizzato → usa quello.
2. Altrimenti usa `config.utilities.tipo_doc_fiscale_id`.
3. Se ancora NULL → errore bloccante.

---

### Note operative

* Funzione pensata per l’alimentazione di `attivita_fatturabili`.
* Non prevede fallback su utility: il tipo documento e` di sistema.

---

{% include-markdown "signature-core.md" %}

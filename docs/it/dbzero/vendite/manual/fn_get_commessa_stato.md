## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_commessa_stato`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  
>
> **Approfondimento funzioni:**
>
> • [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa)  
> • [vendite.fn_list_commesse_emittibili](/dbzero/vendite/funzioni/fn_list_commesse_emittibili)  
>
---

### 🎯 Scopo Principale

(latest review 26-02-2026)  
Restituisce in una singola query lo stato operativo di una commessa:

* identificativo stato (`stato_commessa_id`)
* codice stato (compatibilita` retroattiva)
* flag di governance (`chiude_commessa`, `emittibile`, `modificabile`)
* principali contatori delle righe `commesse_attivita`

---

### ✅ Regole principali

* `p_commessa_id` obbligatorio e `> 0`.
* Errore esplicito se la commessa non esiste.
* `stato_commessa` viene letto da `vendite.stati_commessa.codice`.
* I contatori sono aggregati su `vendite.commesse_attivita`:
  * `total_attivita`
  * `total_approvate` / `total_non_approvate`
  * `total_emesse` / `total_non_emesse`
  * `total_prezzo_da_riallineare`
* `last_update` e` il massimo tra update testata commessa e update ultima riga attivita`.

---

### ✅ Output

Una sola riga con metadati testata + metriche aggregate, utile a dashboard, orchestratori backend e controlli pre-emissione.

---

### 🧪 Esempio d'uso

```sql
SELECT *
FROM vendite.fn_get_commessa_stato(12345);
```

---

{% include-markdown "signature-core.md" %}

## 📘 Documentazione Concettuale – Funzione `config.fn_get_aliquota_iva`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
[config.iva](/dbzero/config/tabelle/iva)  
> [config.iva_stati](/dbzero/config/tabelle/iva_stati)  

---
### 🎯 Scopo Principale
(latest review 10-02-2026)  
La funzione **`config.fn_get_aliquota_iva()`** restituisce l’aliquota IVA
applicando l’eventuale override definito in `config.iva_stati` per lo Stato
specificato.

---

### Regole principali

* `p_iva_id` obbligatorio e `> 0`.
* `p_stato_id` opzionale. Se `NULL`, usa sempre `config.iva.aliquota_iva`.
* Se esiste un override per `(iva_id, stato_id)` lo utilizza, altrimenti usa `config.iva.aliquota_iva`.
* ⭐ **È `STABLE`** (dal 2026-08-29): dentro una stessa istruzione dà sempre la
  stessa risposta, quindi il pianificatore può chiamarla una volta sola invece che
  per ogni riga. Era dichiarata `VOLATILE` senza esserlo — il corpo legge e basta.
* ⛔ **Solleva su `p_iva_id` nullo.** Non ritorna zero: chi la chiama su una riga
  che potrebbe non avere un codice IVA deve **guardarla con un `CASE`**, perché un
  `COALESCE` attorno alla chiamata non fa in tempo a difendere — l'errore è già
  stato sollevato.

> ⚠️ **Quando NON usarla.** Su una riga o un riepilogo di fattura l'aliquota è
> **memorizzata** (`aliquota_iva`): questa funzione dà la percentuale di **oggi**,
> e su un documento congelato è la risposta sbagliata.

---

### Output

Ritorna la percentuale IVA (numeric).

---

### Esempio d’uso

```sql
SELECT config.fn_get_aliquota_iva(1, 100);
```

---

{% include-markdown "signature-core.md" %}

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

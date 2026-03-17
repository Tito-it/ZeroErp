## 📘 Documentazione Concettuale – Funzione `vendite.fn_assign_numero_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)  
> • [vendite.registri_fatturazione_progressivi](/dbzero/vendite/tabelle/registri_fatturazione_progressivi)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_next_progressivo](/dbzero/vendite/funzioni/fn_get_next_progressivo)  
> • [vendite.fn_get_anno_registro](/dbzero/vendite/funzioni/fn_get_anno_registro)  
>
🎯 Scopo Principale

(latest review 09-02-2026)
La funzione **`vendite.fn_assign_numero_fattura()`** assegna il progressivo
in base al registro e aggiorna `anno`, `serie` e `numero` sulla testata fattura.

---

### Regole principali

* `p_fattura_id` obbligatorio e `> 0`.
* Lock sulla riga fattura per coerenza.
* `anno` ricavato da `vendite.fn_get_anno_registro`.
* Numero ottenuto da `vendite.fn_get_next_progressivo`.
* `mese` valorizzato solo se `reset_policy = MENSILE`.

---

### Output

Ritorna una riga con:

* `registro_id`
* `anno`
* `mese`
* `serie`
* `numero`

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_assign_numero_fattura(
  p_fattura_id => 123
);
```

---

{% include-markdown "signature-core.md" %}

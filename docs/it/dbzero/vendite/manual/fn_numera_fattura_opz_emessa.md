## 📘 Documentazione Concettuale – Funzione `vendite.fn_numera_fattura_opz_emessa`

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
### 🎯 Scopo Principale
(latest review 09-02-2026)
La funzione **`vendite.fn_numera_fattura_opz_emessa()`** assegna il numero
fattura in modo **idempotente** e, opzionalmente, imposta lo stato documento
**EMESSA** usando `codice_interno`.

---

### Regole principali

* `p_fattura_id` obbligatorio e `> 0`.
* Lock solo sulla riga fattura (minima concorrenza).
* Se la fattura e` gia` numerata, ritorna i valori correnti.
* Il numero e` assegnato tramite `vendite.fn_assign_numero_fattura`.
* Se `p_set_emessa = true`, imposta lo stato documento `EMESSA`.

---

### Output

Ritorna una riga con:

* `registro_id`
* `anno`
* `mese`
* `serie`
* `numero`

---

### Esempi d’uso

```sql
SELECT *
FROM vendite.fn_numera_fattura_opz_emessa(
  p_fattura_id => 123
);
```

```sql
SELECT *
FROM vendite.fn_numera_fattura_opz_emessa(
  p_fattura_id => 123,
  p_set_emessa => true,
  p_codice_interno_emessa => 'EMESSA'
);
```

---

{% include-markdown "signature-core.md" %}

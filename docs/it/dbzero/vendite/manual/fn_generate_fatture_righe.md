## 📘 Documentazione Concettuale – Funzione `vendite.fn_generate_fatture_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_get_or_create_fattura_header](/dbzero/vendite/funzioni/fn_get_or_create_fattura_header)   
> • [vendite.fn_group_attivita_fatturabili](/dbzero/vendite/funzioni/fn_group_attivita_fatturabili)   
>
### 🎯 Scopo Principale
(latest review 07-02-2026)  
(Deprecate-trasferite in django)  
La funzione **`vendite.fn_generate_fatture_righe()`** genera le righe fattura
partendo dalle `attivita_fatturabili` lockate sul lotto.

---

### Regole principali

* Usa `fn_get_or_create_fattura_header` per la testata.
* Usa `fn_group_attivita_fatturabili` per la chiave riga.
* Aggiorna `fattura_riga_id` e `fatturato = true` sulle attivita.
* `p_dry_run=true` esegue solo il conteggio senza scritture.

---

### Output

Ritorna il numero di righe generate (o conteggiate in dry-run).

---

### Esempio

```sql
SELECT vendite.fn_generate_fatture_righe(
  p_lotto_id := 10,
  p_dry_run := false
);
```

---

{% include-markdown "signature-core.md" %}

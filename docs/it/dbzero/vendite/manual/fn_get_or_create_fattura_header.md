## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_or_create_fattura_header`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)   
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)   
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)   
>
**Approfondimento funzioni:**
>
• [vendite.fn_build_fattura_key](/dbzero/vendite/funzioni/fn_build_fattura_key)   
>
🎯 Scopo Principale

(latest review 29-01-2026)  
La funzione **`vendite.fn_get_or_create_fattura_header()`** recupera o crea una
**testata fattura in bozza** a partire da una riga di `attivita_fatturabili`,
usando la chiave documento (`vendite.fn_build_fattura_key`) e collegandola al lotto.

---

### Regole principali

* La chiave documento include BA fattura, tipo doc, valuta, emittente, reseller, utility, registro.
* Lo stato iniziale della fattura è `DRAFT`.
* Se una fattura con la stessa chiave esiste già nel lotto, viene riutilizzata.
* La relazione lotto ↔ fattura è registrata in `fatturazione_lotti_fatture`.

---

### Output

Ritorna l’`id` della fattura (esistente o creata).

---

### Esempio

```sql
SELECT vendite.fn_get_or_create_fattura_header(
  p_lotto_id => 10,
  p_attivita_id => 12345
);
```

---

{% include-markdown "signature-core.md" %}

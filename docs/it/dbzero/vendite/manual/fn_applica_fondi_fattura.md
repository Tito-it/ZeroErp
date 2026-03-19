## 📘 Documentazione Concettuale – Funzione `vendite.fn_applica_fondi_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
> • [vendite.tipi_fondi_fattura](/dbzero/vendite/tabelle/tipi_fondi_fattura)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_genera_fondi_fattura_source](/dbzero/vendite/funzioni/fn_genera_fondi_fattura_source)  
>
### 🎯 Scopo Principale
La funzione **`vendite.fn_applica_fondi_fattura()`** applica i fondi fattura
in stato `DISPONIBILE` ad una **fattura figlia**, creando le righe in
`vendite.fatture_fondi_fattura` e aggiornando la `source` a stato `ASSEGNATO`.

---

### Regole principali

* `billing_account_id`, `utility_id`, `tipo_doc_fiscale_id`, `emittente_soggetto_ruolo_id`, `valuta_id` obbligatori.
* `fattura_figlia_id` obbligatorio.
* `tipo_fondo_fattura_id` opzionale (se valorizzato filtra i fondi).
* Usa solo righe `source` con `stato = 'DISPONIBILE'` e `fattura_figlia_id IS NULL`.
* Aggiorna la `source`:
  * `fattura_figlia_id`, `data_assegnazione`, `user_assegnazione`
  * `stato = 'ASSEGNATO'`

---

### Output

Ritorna il numero di righe applicate.

---

### Esempio d’uso

```sql
SELECT vendite.fn_applica_fondi_fattura(
  p_billing_account_id => 10,
  p_utility_id => 2,
  p_tipo_doc_fiscale_id => 1,
  p_emittente_soggetto_ruolo_id => 5,
  p_valuta_id => 1,
  p_fattura_figlia_id => 123,
  p_tipo_fondo_fattura_id => NULL
);
```

---

{% include-markdown "signature-core.md" %}

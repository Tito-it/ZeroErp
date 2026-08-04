## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fatturabili_guard_ba_coerenza`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
>
**Approfondimento funzioni:**
>
• [vendite.trgfn_attivita_fatturabili_normalize](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_normalize)  
> • [vendite.trgfn_attivita_fatturabili_guard_commessa](/dbzero/vendite/funzioni/trgfn_attivita_fatturabili_guard_commessa)  
>
### 🎯 Scopo Principale
(latest review 29-01-2026)  
La funzione **`vendite.trgfn_attivita_fatturabili_guard_ba_coerenza()`** valida
la coerenza tra `billing_account_id` e `istanza_utility_id` sulle righe di
`attivita_fatturabili`.

---

### Regole principali

* Se `billing_account_id` e` valorizzato, deve esistere in `anagrafiche.billing_account`.
* `istanza_utility_id` deve coincidere con quella del billing account.
* In caso di incoerenza viene sollevato errore con `fn_log_and_raise_error`.

---

### Output

Nessun output (trigger BEFORE). In caso di errore, l’operazione viene bloccata.

---

### Esempio (caso non valido)

```sql
INSERT INTO vendite.attivita_fatturabili (
  articolo_id, istanza_utility_id, billing_account_id, data_attivita, quantita
)
VALUES (
  :articolo_id, :istanza_non_coerente, :billing_account_id, current_date, 1
);
```

---

{% include-markdown "signature-core.md" %}

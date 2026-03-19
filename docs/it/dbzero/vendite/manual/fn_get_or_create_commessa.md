## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_or_create_commessa`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
>
**Approfondimento funzioni:**
>
• [anagrafiche.fn_get_emittente_fiscale_id](/dbzero/anagrafiche/funzioni/fn_get_emittente_fiscale_id)  
> • [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)  
>
### 🎯 Scopo Principale
(latest review 26-02-2026)  
Recupera una commessa riusabile, coerente con il contesto BA/utility e parametri funzionali, oppure ne crea una nuova in modo sicuro anche con chiamate concorrenti.

---

### Regole principali

* `p_billing_account_id` e `p_utility_id` obbligatori (`> 0`).
* Verifica coerenza tra utility del billing account e utility richiesta.
* `p_competenza_dal` / `p_competenza_al` devono avere range coerente.
* `emittente_soggetto_ruolo_id` usa fallback automatico da `anagrafiche.fn_get_emittente_fiscale_id(...)`.
* Se `p_force_new = false`, usa advisory lock transazionale per evitare doppie create concorrenti sullo stesso perimetro.
* Riuso consentito solo per commesse con stato non terminale:
  * `stati_commessa.chiude_commessa = false`
* Se nessun match e` riusabile, inserisce una nuova commessa (default stato `BOZZA` via `stato_commessa_id = 1`).

---

### Output

Ritorna `commessa_id`:

* id commessa esistente se trovata e riusabile
* id nuova commessa se creata

---

### Esempio d'uso

```sql
SELECT vendite.fn_get_or_create_commessa(
  p_billing_account_id => 1001,
  p_utility_id => 2,
  p_tipo_commessa => 'AUTO',
  p_force_new => false
);
```

---

{% include-markdown "signature-core.md" %}

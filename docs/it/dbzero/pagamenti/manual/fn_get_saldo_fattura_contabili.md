## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_saldo_fattura_contabili`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe)  
> • [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati)  
> • [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili)  
>
### 🎯 Scopo Principale
(latest review 18-09-2026)  
La funzione **`pagamenti.fn_get_saldo_fattura_contabili()`** restituisce il
saldo contabile di una fattura calcolato sulle sole righe in stato
`is_postabile = true`.

---

### Regole principali

* `p_fattura_id` obbligatorio (`> 0`); un valore non positivo è un errore
  **tecnico** (`E_PAGAMENTI_CHIAMATA_NON_VALIDA`): non esce da nessuna
  interfaccia.
* ⭐ `p_escludi_contabile_riga_id` (facoltativo, dal 18-09-2026): la riga
  indicata **non si conta**. È «quanto era dichiarato *prima* di me» per chi
  sta scrivendo o correggendo proprio quella riga — lo stesso parametro, con lo
  stesso mestiere, di `fn_get_saldo_rata` e del nucleo `fn_get_saldi_rate`. La
  riceve da [`fn_get_saldo_fattura`](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura),
  che **delega** il dichiarato a questa funzione invece di riscriverne il
  predicato. Se è fornito e non positivo: errore tecnico.
* Considera solo:
  * `vendite_contabili_righe.attivo = true`
  * `vendite_contabili_righe_stati.is_postabile = true`
  * testata contabile con stato **non finale** (`vendite_contabili_stati.is_final = false`).
    ⚠️ Dal 21-08-2026 lo stato della testata è obbligatorio: il vecchio ripiego
    «`stato_id NULL` trattato come non finale» non esiste più.

---

### 🕘 Storia

* **18-09-2026** — `p_escludi_contabile_riga_id` (P-6 di
  `brief-db-distinta-ricerca-rate`, `20260918-01`). Cambia la firma: `DROP` +
  `CREATE`, perché un secondo overload accanto alla vecchia `(bigint)` sarebbe
  stato ambiguo per ogni chiamata a un argomento.
* **21-08-2026** — cade il ramo «testata senza stato»; guard di chiamata sul
  codice registrato.
* **13-02-2026** — prima stesura.

---

### Output

Ritorna una riga con:

* `saldo_contabile` (numeric)
* `has_righe_postabili` (boolean)

---

### Esempio d’uso

```sql
SELECT *
FROM pagamenti.fn_get_saldo_fattura_contabili(123);
```

---

{% include-markdown "signature-core.md" %}

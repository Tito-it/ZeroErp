## 📘 Documentazione Concettuale – Funzione `vendite.fn_sync_fatture_log_critical_lotto`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)  
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
>
### 🎯 Scopo Principale
(latest review 20-02-2026)  
La funzione **`vendite.fn_sync_fatture_log_critical_lotto()`** sincronizza in modo
set-based:

* il flag `vendite.fatture.critical`
* lo stato tecnico `vendite.fatturazione_lotti_fatture.stato_esecuzione`

a partire dalle fatture toccate da modifiche su `vendite.fatture_log`.

---

### Regole principali

* Input: array di `fattura_id`.
* Il calcolo `critical` considera solo log:
  * `status = 'C'`
  * `disabilitato = false`.
* La propagazione su `fatturazione_lotti_fatture.stato_esecuzione` avviene solo per lotti:
  * `stato_lotto = 'IN_ESECUZIONE'` **oppure**
  * `stato_operativo = 'APERTO'`.
* Mappatura esito:
  * `critical = true` -> `stato_esecuzione = 'ERRORE'`
  * `critical = false` -> `stato_esecuzione = 'OK'`
* Le righe `esclusa = true` non vengono modificate.

---

### Output

Nessun output (RETURN `void`).

---

### Utilizzo previsto

Funzione interna chiamata dai trigger statement-level su `vendite.fatture_log`
(`AFTER INSERT/UPDATE/DELETE`) per mantenere allineata la coerenza logica
tra log fattura, flag `critical` e stato esecuzione nel lotto.

---

{% include-markdown "signature-core.md" %}

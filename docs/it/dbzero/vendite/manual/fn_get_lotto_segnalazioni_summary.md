## 📘 Documentazione Concettuale – Funzione `vendite.fn_get_lotto_segnalazioni_summary`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)   
> • [vendite.fatturazione_lotti_fatture](/dbzero/vendite/tabelle/fatturazione_lotti_fatture)   
> • [vendite.fatture_log](/dbzero/vendite/tabelle/fatture_log)   
> • [vendite.fatturazione_lotti_log](/dbzero/vendite/tabelle/fatturazione_lotti_log)   
>
**Approfondimento funzioni:**
>
• [vendite.fn_log_lotto_esito_fatture](/dbzero/vendite/funzioni/fn_log_lotto_esito_fatture)   
>
### 🎯 Scopo Principale
(latest review 23-02-2026)  
La funzione **`vendite.fn_get_lotto_segnalazioni_summary()`** restituisce
un riepilogo aggregato delle segnalazioni attive (`C`/`W`/`I`) di un lotto,
unificando:

* log fattura (`vendite.fatture_log`) tramite legame lotto-fatture;
* log lotto (`vendite.fatturazione_lotti_log`).
* stato tecnico del ponte lotto-fatture (`vendite.fatturazione_lotti_fatture.stato_esecuzione`).

---

### ⭐ Le criticità di un documento **uscito dal giro** non contano più
(dal 2026-09-08)

Quando l'operatore toglie un documento rotto dal giro
([`vendite.fn_escludi_documento_da_giro`](/dbzero/vendite/funzioni/fn_escludi_documento_da_giro)),
la sua segnalazione **smette di fermare il lotto** — così il giro riparte con i
documenti che restano, e riparte da solo quando esce l'ultimo che lo teneva
fermo.

⭐ **Non si ritira niente.** La segnalazione resta scritta e leggibile nella
storia del lotto: cambia soltanto **chi conta** per bloccare. Non è il
messaggio a essere stato messo a tacere, è il suo documento a non essere più in
gioco.

⚠️ **Una segnalazione senza documento continua a contare**, ed è il
comportamento voluto: significa *«questa criticità è del giro»* — un emittente
non risolto, una configurazione mancante — e una criticità del giro deve fermare
il giro, perché non c'è nessun documento da togliere.

#### Dei tre conteggi, uno solo è cambiato

| Conteggio | Da dove legge | Che cosa è cambiato |
| --- | --- | --- |
| **log di lotto** | le segnalazioni del giro | 🔵 **l'unico toccato**: salta quelle dei documenti usciti |
| **log fatture** | attraverso il legame lotto-fatture | ✅ niente |
| **ponte** | lo stato tecnico del legame lotto-fatture | ✅ niente |

⭐ Gli ultimi due **si sistemano da soli**: togliere un documento dal giro
cancella la sua bozza, quindi il legame sparisce e i due conteggi scendono senza
che nessuno li tocchi.

> 🔴 **Finché chi scrive le segnalazioni non dichiara a quale documento
> appartengono, questa regola non sblocca niente**: le criticità nascono senza
> proprietario e contano tutte. È l'ordine dei lavori, non un difetto.

---

### Regole principali

* `p_lotto_id` è obbligatorio e deve essere `> 0`.
* Le conte vengono calcolate solo su record **attivi** (`disabilitato = false`).
* Le severità considerate:
  * `C` = critical
  * `W` = warning
  * `I` = info (solo su log lotto)
* Ritorna anche il conteggio tecnico:
  * `fatture_stato_esecuzione_errore_count` = numero fatture del lotto in stato esecuzione `ERRORE`.
* Output sempre valorizzato con `0` quando non ci sono righe.

---

### Output

La funzione ritorna una sola riga con:

* `fatture_critical_count`
* `fatture_warning_count`
* `lotto_critical_count`
* `lotto_warning_count`
* `lotto_info_count`
* `fatture_stato_esecuzione_errore_count`

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_get_lotto_segnalazioni_summary(
  p_lotto_id => 120
);
```

---

{% include-markdown "signature-core.md" %}

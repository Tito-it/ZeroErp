## 📘 Documentazione Concettuale – Funzione `vendite.fn_reset_fondi_fattura`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [vendite.fatture_fondi_fattura](/dbzero/vendite/tabelle/fatture_fondi_fattura)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura)  
>
### 🎯 Scopo Principale
(latest review 15-08-2026)

La funzione **`vendite.fn_reset_fondi_fattura()`** ripristina i fondi fattura
applicati ad una **fattura figlia**:

* riapre la `source` (stato `DISPONIBILE`)
* elimina le righe in `fatture_fondi_fattura`
* gestisce i casi bloccati da contabile in stato `CHIUSA`

> ⭐ **È un'operazione TECNICA sul ciclo di vita della figlia** — il ritorno di
> un lotto in bozza — **e non una reazione ai pagamenti**: nessun incasso la
> chiama e nessun incasso deve chiamarla.
>
> La precisazione risponde a una domanda che il piano si era posto: *«che cosa
> succede a un fondo `ASSEGNATO` se la sorgente riceve poi un incasso?»*.
> Risposta: **niente**. Un fondo assegnato non si tocca; l'eventuale doppio
> pagamento diventa un credito sulla sorgente e si governa nel **processo
> rimborsi**, in `pagamenti`. Senza questa riga è il tipo di funzione che al giro
> dopo qualcuno chiama credendo di aver trovato il pezzo mancante.

---

### Regole principali

* `p_fattura_id` obbligatorio.
* Opera solo su `source` con `stato = 'ASSEGNATO'`.
* Resetta campi di assegnazione (`fattura_figlia_id`, date/utente).
* Applica il reset solo ai tipi con `codice_interno = 'F_F_ADD_ACC'`.
* Se esiste una riga contabile fondo agganciata a testata `CHIUSA`:
  * non elimina righe fondo/source
  * imposta `source.stato = 'ANNULLATO'`
  * **scrive la ragione in `source.motivo`** (dal 2026-08-15), oltre al warning
    in `vendite.fatture_log`.

> ⚠️ **Perché la colonna e non solo il log.** La ragione c'era già, ma viveva in
> un **messaggio di diario**: leggibile da una persona, inutilizzabile da una
> query. Con `motivo` obbligatorio su ogni `ANNULLATO`
> (`chk_fondi_source_motivo_obbligatorio`), «perché questo fondo è sparito» si
> risponde guardando la riga.

---

### Output

Ritorna:

* `updated_source` = numero righe source ripristinate
* `deleted_fondi` = numero righe fondi eliminate

---

### Esempio d’uso

```sql
SELECT *
FROM vendite.fn_reset_fondi_fattura(
  p_fattura_id => 123
);
```

---

{% include-markdown "signature-core.md" %}

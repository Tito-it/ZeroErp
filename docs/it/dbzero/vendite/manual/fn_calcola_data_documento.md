## 📘 Documentazione Concettuale – Funzione `vendite.fn_calcola_data_documento`

> 👀 **Vedi anche**
>
> [script.fn_data_operativa](/dbzero/script/funzioni/fn_data_operativa)
> [vendite.fn_imposta_data_documento_lotto](/dbzero/vendite/funzioni/fn_imposta_data_documento_lotto)
> [vendite.registri_fatturazione](/dbzero/vendite/tabelle/registri_fatturazione)
> [vendite.fn_get_or_create_fattura_header](/dbzero/vendite/funzioni/fn_get_or_create_fattura_header)

---

### 🎯 Scopo Principale

**Che data porta un documento emesso su questo registro?**

È la sede **unica** di quella decisione. Chiunque debba datare una fattura la
chiede qui, invece di ricavarsela.

```sql
SELECT vendite.fn_calcola_data_documento(
           p_registro_id     => 3,
           p_competenza_mese => '2026-07-01',
           p_data_dichiarata => NULL);      -- → 2026-07-31
```

---

### La regola, in ordine

| # | Condizione | Risultato |
|---|---|---|
| **1** | c'è una data **dichiarata** | vince quella, sempre |
| **2a** | politica del registro = `OGGI` | `script.fn_data_operativa()` |
| **2b** | politica = `FINE_MESE_COMPETENZA` | l'ultimo giorno del mese di competenza |
| **3** | qualunque altro caso | ⛔ **solleva** |

⭐ **Perché la dichiarata vince su tutto.** Un lotto può contenere documenti di
registri diversi — la nota di credito viaggia su un sezionale suo. Se ogni
documento seguisse la propria politica, un atto unico produrrebbe date diverse.
La dichiarazione è ciò che rende vera la frase *«una data sola per l'intero
atto»*.

---

### ⛔ Nessun ramo silenzioso

Due punti in cui la funzione **rifiuta di indovinare**:

**Competenza assente con politica `FINE_MESE_COMPETENZA`.** Solleva
(`E_VENDITE_CHIAMATA_NON_VALIDA`, classe TECNICO) invece di ripiegare su oggi.
`competenza_mese` è `NOT NULL` sul lotto: un `NULL` qui non arriva da un
operatore, arriva da un programma rotto.

**Politica non riconosciuta.** Non c'è nessun `ELSE` che si comporti come `OGGI`.
Il `CHECK` di colonna rende oggi quel ramo irraggiungibile; se un domani si
allargasse la lista delle politiche, la funzione **si ferma e lo dice** invece di
datare i documenti a oggi fingendo di aver capito.

> Il criterio è sempre lo stesso, ed è già scritto in
> `fn_genera_scadenze_fattura` a proposito della ripartizione non gestita: *una
> data plausibile e sbagliata su un documento fiscale non la nota nessuno, e
> quando la si nota il numero è già stato consumato.*

---

### Note operative

* ⚠️ **Il registro si legge sempre**, anche quando la data è già dichiarata e il
  suo valore non servirebbe. Costa una lettura per chiave primaria su sei righe,
  ed è **l'unico punto** in cui un registro inesistente si fa notare. La tabella
  non ha RLS, quindi qui «non trovato» vuol dire davvero «non esiste», non «non
  lo vedo».
* ℹ️ `date_trunc('month', ...)` sulla competenza **anche se** nei 49 lotti
  misurati è sempre il primo del mese: nessun vincolo lo impone, e la funzione
  non deve dipendere da un'abitudine.
* `STABLE`.
* Brief: `docs/it/dev/work-in-progress/brief-db-numerazione-data-documento-e-sequenza.md` §4 DB-5.

---

{% include-markdown "signature-core.md" %}

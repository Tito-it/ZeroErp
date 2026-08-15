## 📘 Documentazione Concettuale – Funzione `vendite.fn_genera_fondi_fattura_source`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source)  
> • [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities)  
> • [pagamenti.vendite_movimenti](/dbzero/pagamenti/tabelle/vendite_movimenti)  
>
**Approfondimento funzioni:**
>
• [vendite.fn_ricalcola_totali_fattura](/dbzero/vendite/funzioni/fn_ricalcola_totali_fattura) — è lei che **scrive** `minimo`  
> • [vendite.fn_applica_fondi_fattura](/dbzero/vendite/funzioni/fn_applica_fondi_fattura)  
>
### 🎯 Scopo Principale
(latest review 15-08-2026)  
La funzione **`vendite.fn_genera_fondi_fattura_source()`** crea in
`fatture_fondi_fattura_source` i fondi delle fatture **«di minimo»**, cioè quelle
il cui importo cade dentro la banda configurata per emittente × utility: sono i
documenti che **non si incassano da soli** e il cui valore viene riportato sulla
fattura successiva.

---

### ⭐ Che cos'è la «banda», e perché un fondo può essere negativo

Le due soglie di `anagrafiche.emittenti_fiscali_utilities` —
`minimo_soglia_min` e `minimo_soglia_max` — **non sono un minimo e un tetto**:
sono i due capi di un intervallo **che contiene lo zero**. Esempio reale
(`min = −500`, `max = +10`):

```text
                −500 €              0              +10 €
    ────────────────┼───────────────┼───────────────┼──────────────
     RIMBORSO       │      F O N D O   F A T T U R A     │  PAGAMENTO
     (credito       │  a credito  ·  a debito            │  ordinario
      troppo grande)│  si riporta sulla fattura dopo     │  del cliente
```

| Totale della fattura | Esito |
| --- | --- |
| **sopra il massimo** | pagamento ordinario del cliente: nessun fondo |
| fra il massimo e **zero** | troppo piccola per essere incassata da sola → **fondo a debito** |
| fra zero e **il minimo** | credito troppo piccolo per un rimborso → **fondo a credito** |
| **sotto il minimo** | credito importante → processo di **rimborso** (dominio `pagamenti`) |

🔴 **Ne segue che un fondo di importo negativo è normale, non un difetto**: il
capo inferiore della banda esiste apposta per riportare avanti dei crediti. Un
filtro «solo importi positivi» spegnerebbe metà del meccanismo, e lo farebbe in
silenzio — il fondo continuerebbe a funzionare nell'altro verso.

⚠️ **Il flag `minimo` non lo imposta questa funzione**: lo **riscrive**
`fn_ricalcola_totali_fattura` a ogni ricalcolo, confrontando `totale_a_pagare`
con le due soglie. Qui si legge soltanto.

---

### Regole principali

* Parametri obbligatori (ID > 0).
* Seleziona le fatture con `minimo = true` la cui chiave combacia con quella
  passata.
* Inserisce nuove source in stato `DISPONIBILE` solo per saldo effettivo diverso
  da `0`.
* Se la source esiste già e non è assegnata, aggiorna importo e stato
  (`saldo_effettivo = 0` → `ANNULLATO`, altrimenti `DISPONIBILE`).
* `saldo_effettivo` è calcolato come:
  * residuo della fattura (`totale_a_pagare` meno i movimenti);
  * meno il saldo contabile postabile
    (`vendite_contabili_righe_stati.is_postabile = true`).

#### 🔴 Il perimetro dichiarato non è quello applicato

La funzione riceve **`p_utility_id` ma non lo usa come filtro**: lo *scrive* sulla
riga generata. Il `WHERE` confronta soltanto `billing_account_id`,
`tipo_doc_fiscale_id`, `emittente_soggetto_ruolo_id` e `valuta_id`.

**Conseguenza misurata** su un billing account con due utility: a ogni giro del
lotto la stessa riga viene rimarcata con la utility dello scope corrente, e
`fn_applica_fondi_fattura` filtra proprio su quella colonna. **A quale fattura
figlia finisce il fondo dipende dall'ordine dei giri.**

⚠️ Fino al 2026-08-15 questa pagina dichiarava un perimetro
*«BA/utility/tipo_doc/emittente/valuta»* che il codice non applica. La correzione
prevista è più larga della sola utility: il legame fra sorgente e figlia deve
usare **la stessa chiave con cui si accorpano le attività in fattura**
(`fn_build_fattura_key`, **nove** elementi — vi rientrano anche reseller,
registro, termine e modalità di pagamento). Vedi
[il piano](/dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo) §8.2 D-4.

#### 🟠 Che cosa cambia con il piano in corso

Le tre regole qui sotto descrivono il **comportamento di oggi** e sono destinate
a cadere. Sono segnalate perché chi legge non deve progettarci sopra:

| Oggi | Diventerà | Passo |
| --- | --- | --- |
| non c'è **nessun filtro di stato** sulla sorgente: anche una fattura `DRAFT` o **`ANNULLATA`** con `minimo = true` genera un fondo | solo sorgenti **`DEFINITIVA`** | D-1 |
| se la source esiste già, **l'importo viene riaggiornato** («idempotente: riallinea i dati») | il fondo si crea **una volta sola** e non si ricalcola più: una fattura definitiva ha un fondo definitivo | D-1 + D-6 |
| a saldo zero la source passa ad **`ANNULLATO`** da sola | nessun automatismo cambia lo stato di un fondo: la non-capienza si verifica **al momento dell'applicazione** | D-1 + D-3 |

---

### Output

Ritorna il numero totale di record modificati (`insert` + `update`).

---

### Esempio d’uso

```sql
SELECT vendite.fn_genera_fondi_fattura_source(
  p_billing_account_id => 100,
  p_utility_id => 1,
  p_tipo_doc_fiscale_id => 10,
  p_emittente_soggetto_ruolo_id => 7,
  p_valuta_id => 1,
  p_tipo_fondo_fattura_id => 1
);
```

---

{% include-markdown "signature-core.md" %}

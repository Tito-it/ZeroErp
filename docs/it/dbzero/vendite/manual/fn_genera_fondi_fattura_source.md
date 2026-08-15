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
* ⭐ **CREATE-ONLY dal 2026-08-15**: non esiste più un ramo di aggiornamento. Il
  fondo di una fattura `DEFINITIVA` è un **atto** — si scrive una volta con
  l'importo letto in quel momento e non si ricalcola. Prima, ogni giro di
  fatturazione riallineava l'importo delle source non assegnate, **anche di
  fatture già stampate**.
* Inserisce in stato `DISPONIBILE` e `origine = 'AUTOMATICA'`.
* I **cinque filtri di scope** (billing account, **utility**, tipo doc fiscale,
  emittente, valuta) dicono *quali* fatture guarda questa chiamata.

#### ⭐ La regola non è scritta qui: si chiede

Dal 2026-08-15 (sera) l'**inviluppo** — sorgente `DEFINITIVA`, dentro la banda,
utility attribuita, atto unico, importo non nullo e **corrispondenza** col
documento — non sta nel `WHERE` di questa funzione ma dentro
[fn_fondo_fattura_proponibile](/dbzero/vendite/funzioni/fn_fondo_fattura_proponibile),
che viene chiamata in `LATERAL` e di cui si inserisce il risultato.

La ragione è che **lo stesso inviluppo serve all'elenco**
[vw_fondi_fattura_da_decidere](/dbzero/vendite/views/vw_fondi_fattura_da_decidere):
due copie della regola darebbero prima o poi due risposte diverse, e il divario
si vedrebbe come un elenco che propone ciò che il giro notturno non crea.

⚠️ **Non c'è un pre-filtro su `minimo`** in questa funzione, benché costerebbe
poco: sarebbe di nuovo un pezzo di regola in un secondo posto, e il giorno in cui
l'inviluppo cambiasse continuerebbe a tagliare in silenzio. Lo scope riduce già i
candidati a una manciata di documenti per chiamata. *(Nella vista invece il
pre-filtro c'è, perché lì non esiste uno scope: è dichiarato lì.)*

#### ✅ Il perimetro dichiarato adesso è quello applicato

Fino al 2026-08-15 la funzione riceveva **`p_utility_id` senza usarlo come
filtro**: lo *scriveva* soltanto sulla riga. Su un billing account con due
utility, a ogni giro la stessa riga veniva rimarcata con la utility dello scope
corrente — e siccome `fn_applica_fondi_fattura` filtra proprio su quella colonna,
**a quale fattura figlia finisse il fondo dipendeva dall'ordine dei giri**.

Adesso `utility_id` è nel filtro, con `=` e non `IS NOT DISTINCT FROM`: una
fattura senza utility è un **dato incompleto** (BASE è una utility vera) e
un'attribuzione non si indovina. Quel caso non sparisce nel nulla — lo mostra
l'elenco, con motivo `UTILITY_NON_ATTRIBUIBILE`.

ℹ️ Il legame fra sorgente e figlia usa **la stessa chiave con cui si accorpano le
attività in fattura** (`fn_build_fattura_key`, **nove** elementi: vi rientrano
anche reseller, registro, termine e modalità di pagamento). Il confronto si
chiude dentro `fn_applica_fondi_fattura`, che ha entrambe le fatture.

#### ✅ Cosa è caduto, e cosa lo sostituisce

| Prima | Adesso |
| --- | --- |
| nessun **filtro di stato**: anche una fattura `ANNULLATA` con `minimo = true` generava un fondo (`fn_get_saldo_fattura` non guarda lo stato) | solo sorgenti **`DEFINITIVA`** |
| se la source esisteva, **l'importo veniva riaggiornato** | l'atto si scrive **una volta sola**, e il lock di colonna lo rende immutabile |
| a saldo zero la source passava ad **`ANNULLATO`** da sola | 🔴 nessun automatismo la annulla più **qui**: la non-capienza si verifica **al momento dell'applicazione**, dove il denaro si muove davvero |

---

### Output

Ritorna il numero di source **create** (non più `insert` + `update`: gli update
non esistono più).

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

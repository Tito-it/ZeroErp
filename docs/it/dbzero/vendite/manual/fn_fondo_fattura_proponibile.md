## 📘 Documentazione Concettuale – Funzione `vendite.fn_fondo_fattura_proponibile`

> 👀 **Vedi anche**
>
> **Chi la usa — ed è il punto:**
>
> • [vendite.fn_genera_fondi_fattura_source](/dbzero/vendite/funzioni/fn_genera_fondi_fattura_source) — il giro di fatturazione **inserisce ciò che questa funzione risponde**
> • [vendite.vw_fondi_fattura_da_decidere](/dbzero/vendite/views/vw_fondi_fattura_da_decidere) — l'elenco **mostra la stessa risposta**
>
> **Su cosa è costruita:**
>
> • [vendite.fn_saldo_sorgente_fondo](/dbzero/vendite/funzioni/fn_saldo_sorgente_fondo) — il residuo della sorgente
> • [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities) — le due soglie, tramite il flag `minimo`
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-in-progress/brief-db-fondo-fattura-ricalcolo-e-governo) §8.2 D-9

---

### 🎯 Scopo Principale
(latest review 15-08-2026)

**Che cosa farebbe l'automatismo, adesso.**

```text
NUMERIC   → l'importo che il giro di fatturazione scriverebbe oggi
NULL      → non farebbe niente
```

`NULL` è una risposta piena, non un'assenza: significa *«nessuna proposta»*. E
non è uno zero — un fondo di importo zero non è nemmeno ammesso in tabella
(`chk_fondi_source_importo_non_zero`).

---

### ⭐ Perché esiste: la stessa domanda in due bocche

L'elenco «da decidere» e il giro notturno devono rispondere **la stessa cosa**
alla domanda *«questa fattura merita un fondo, e di quanto?»*. Se la regola
vivesse in due posti — il `WHERE` della generazione e il `SELECT` della vista —
prima o poi darebbero due risposte, e il divario avrebbe una forma silenziosa:

```text
l'elenco PROPONE un fondo che il giro non crea
    …oppure…
l'elenco TACE su un fondo che il giro crea
```

Nessun errore. Nessun log. Solo due verità.

> 🔴 Il piano prevedeva questa funzione «costruita su `fn_saldo_sorgente_fondo`,
> così proposta e guard non possono divergere». Vero e **insufficiente**: il
> guard non era l'unico posto da cui divergere. L'*inviluppo* stava nel `WHERE`
> della generazione, e scriverla senza spostarlo ne avrebbe creato la seconda
> copia — proprio la regola che questa funzione esiste per condividere.

---

### I cinque silenzi

`NULL` quando l'automatismo non farebbe niente:

| Condizione | Perché |
| --- | --- |
| la sorgente non è **`DEFINITIVA`** | prima di essere definitiva un documento cambia ancora; e uno stato nullo o fuori vocabolario non entra (fail-closed) |
| non è **«di minimo»** | `minimo IS TRUE` è il flag che dice «dentro la banda delle due soglie», e lo scrive `fn_ricalcola_totali_fattura` |
| non ha **`utility_id`** | ⚠️ non è un dato «da decidere più tardi»: la generazione filtra `f.utility_id = p_utility_id`, e **NULL non è uguale a niente**. È irraggiungibile da qualunque giro |
| esiste già un **atto**, in qualunque stato | anche `ANNULLATO` — quell'annullamento è **una decisione**, e riproporre il fondo sarebbe l'elenco che chiede ogni giorno di rifare ciò che qualcuno ha deciso di non fare |
| il numero è **zero**, o **non corrisponde** al documento | segno diverso dal `totale_a_pagare`, o più grande in valore assoluto |

---

### ⚠️ La corrispondenza, e come NON si scrive

```text
✅  segno uguale  E  valore assoluto non superiore
❌  «compreso fra 0 e il totale»
```

La seconda forma sembra la stessa cosa e non lo è: su una sorgente **a credito**
gli estremi si invertono e l'intervallo diventa vuoto. Sarebbe una porta chiusa
travestita da controllo — e su **metà della banda**, perché il capo inferiore
delle soglie esiste apposta per riportare avanti i crediti.

ℹ️ È la stessa regola del guard
[trgfn_fondi_source_guard_importo](/dbzero/vendite/funzioni/trgfn_fondi_source_guard_importo).
Qui è una **risposta** («non lo propongo»), lì è un **rifiuto**: l'automatismo
non deve fermarsi su un caso ordinario, una scrittura sbagliata sì.

---

### ⚠️ Perché NON è `STABLE`, benché il piano lo dicesse

È costruita su `fn_saldo_sorgente_fondo`, che è deliberatamente `VOLATILE`
perché chiama due funzioni `pagamenti.*` dichiarate `VOLATILE`. Promettere al
planner una stabilità che non c'è autorizza inline e cache sbagliati —
PostgreSQL non lo impedisce, ed è precisamente per questo che va deciso a mano.

⚠️ Conseguenza pratica: **non va chiamata su una tabella intera**. Chi la usa
restringe prima — la generazione con i cinque filtri di scope, la vista col
pre-filtro `DEFINITIVA + minimo`.

---

### Cosa NON controlla, e non è una dimenticanza

I **cinque parametri di scope** (billing account, utility, tipo doc, emittente,
valuta) restano nel chiamante: dicono *quali* fatture guardare, non se una
fattura meriti un fondo.

L'unica eccezione è `utility_id`, che entra qui perché il suo essere `NULL` è una
proprietà **del documento** e non del giro: rende la fattura invisibile a
chiunque, e l'elenco la mostra per questo.

---

### Esempio d'uso

```sql
-- Quanto varrebbe il fondo di questa fattura, se lo si emettesse adesso?
SELECT vendite.fn_fondo_fattura_proponibile(
         p_fattura_sorgente_id   => 12345,
         p_tipo_fondo_fattura_id => (SELECT id FROM vendite.tipi_fondi_fattura
                                      WHERE codice_interno = 'F_F_ADD_ACC')
       );
```

---

{% include-markdown "signature-core.md" %}

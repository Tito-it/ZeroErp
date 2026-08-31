## 📘 Documentazione Concettuale – Trigger function `vendite.trgfn_fondi_source_guard_importo`

> 👀 **Vedi anche**
>
> **Tabella sorvegliata:**
>
> • [vendite.fatture_fondi_fattura_source](/dbzero/vendite/tabelle/fatture_fondi_fattura_source) — trigger `trg_fatture_fondi_fattura_source_a10_guard_importo_ins_upd`
>
> **Da dove nasce la regola:**
>
> • [anagrafiche.emittenti_fiscali_utilities](/dbzero/anagrafiche/tabelle/emittenti_fiscali_utilities) — le due soglie
> • [vendite.fn_ricalcola_totali_fattura](/dbzero/vendite/funzioni/fn_ricalcola_totali_fattura) — è lei che **scrive** `minimo`
>
> **Piano:** [brief-db-fondo-fattura-ricalcolo-e-governo](/dev/work-done/brief-db-fondo-fattura-ricalcolo-e-governo) §8.2 D-3(a)

---

### 🎯 Scopo Principale
(latest review 15-08-2026)

**Un fondo deve assomigliare alla fattura da cui nasce.**

```text
l'importo non è zero
ha lo stesso segno del `totale_a_pagare` della fattura sorgente
non lo supera in valore assoluto
```

Chi non rispetta la regola non entra in tabella: `E_FONDO_NON_CORRISPONDE_SORGENTE`.

---

### 🔴 Quello che il guard NON vieta: il fondo negativo

È il malinteso da togliere di mezzo per primo, perché il progetto lo ha
commesso davvero (tampone del 2026-08-09, corretto il 15-08).

Le due soglie di `emittenti_fiscali_utilities` non sono «un minimo e un
massimo»: sono i due capi di una **banda che contiene lo zero**.

```text
                −500 €              0              +10 €
    ────────────────┼───────────────┼───────────────┼──────────────
     RIMBORSO       │      F O N D O   F A T T U R A     │  PAGAMENTO
     (credito       │  a credito  ·  a debito            │  ordinario
      troppo grande)│  si riporta sulla fattura dopo     │  del cliente
```

Metà della banda serve a riportare avanti dei **crediti**. Un limite «solo
importi positivi» avrebbe spento quella metà — e in silenzio, perché il
meccanismo avrebbe continuato a funzionare nell'altro verso.

---

### ⭐ Il pericolo vero: un fondo che racconta un'altra fattura

```text
fattura sorgente:   +8,00
riga contabile:    +40,00   ← nessun guard di quadratura sulle righe contabili:
                              è la slice 2 del cantiere incassi, oggi non esiste
importo_target = 8 − 40 = −32,00
```

Un fondo **a credito di 32 euro** su un documento che vale **8 a debito**. Non
è «negativo»: **non corrisponde**. Ed è la sola cosa che il guard ferma.

⚠️ **La distinzione non è accademica**: due fondi negativi possono avere cause
opposte — uno è il meccanismo che funziona, l'altro è il difetto. Un controllo
(o un test) che guarda il **segno** non li separa; a separarli è la
**corrispondenza con la sorgente**.

---

### ⚠️ Perché un trigger e non un CHECK

Il confronto deve leggere `vendite.fatture`, e un `CHECK` vede **solo la propria
riga**. Non è una scelta di stile: è l'unica forma possibile.

Il `CHECK` che c'è — `chk_fondi_source_importo_non_zero` — resta come rete di
sicurezza sull'unica cosa che si vede dalla riga sola.

> 🔴 **E i due presidi non sono in serie come sembra.** I trigger `BEFORE ROW`
> girano **prima** dei CHECK: su una sorgente con totale diverso da zero, un
> `importo = 0` viene intercettato **da questo guard** (`sign(0)` non è il segno
> di nessun totale non nullo) e il CHECK non entra mai in gioco. Il CHECK
> diventa raggiungibile solo su una sorgente a **totale zero**, dove il guard
> passa perché 0 e 0 hanno lo stesso segno e lo stesso valore assoluto.
>
> ⚠️ È una trappola per chi scrive i test: un'asserzione «il CHECK rifiuta»
> collauda quasi sempre **il guard**. Il pgTAP
> `test-fondi-fattura-governo.sql` lo dichiara, e ci è cascato alla prima
> stesura.

---

### ⚠️ Come si scrive la regola, e come NON si scrive

```text
✅  segno uguale  E  valore assoluto non superiore
❌  «compreso fra 0 e il totale»
```

La seconda forma sembra la stessa cosa e non lo è: su una sorgente a credito gli
estremi **si invertono** e l'intervallo diventa vuoto — un guard che rifiuta
tutto presentandosi come un controllo che funziona. Il progetto ha già pagato
questa trappola un livello più sotto (il filtro `totale_a_pagare > 0` nella
quadratura rate/totale), e **qui il caso non è di bordo: è metà della banda**.

---

### Regole principali

* Montato `BEFORE INSERT OR UPDATE OF importo, fattura_sorgente_id`, non su
  `UPDATE` nudo: gli altri aggiornamenti della tabella (assegnazione, reset,
  annullamento) non toccano né l'importo né la sorgente, e rileggere la fattura
  a ogni giro sarebbe lavoro sprecato su un confronto che non può cambiare.
* **`totale_a_pagare` non calcolato = rifiuto** (fail-closed): senza una base il
  confronto non è decidibile, e un fondo senza base non è un fondo.
* Il messaggio d'errore porta **importo e totale**, così chi legge vede subito
  quale dei due estremi è stato sforato.

---

### ⚠️ Perimetro: solo `origine = 'AUTOMATICA'` (dal 2026-08-15)

Il guard **si ritira dalla strada manuale**: se `origine = 'MANUALE'` esce in
testa e non confronta niente. La ragione è precisa — la strada manuale ha per
definizione il caso opposto: l'eccedenza di un sovra-incasso è un fondo **a
credito su una fattura dal totale positivo**, cioè di segno opposto per
costruzione. Un guard applicato a tutti rifiuterebbe proprio l'atto per cui
quella strada esiste.

Non è un buco: i due presidi sono **diversi, non uno più debole dell'altro**.

| `origine` | presidio |
| --- | --- |
| `AUTOMATICA` | **vincolato**: il guard legge la sorgente e rifiuta ciò che non le assomiglia |
| `MANUALE` | **governato**: `motivo` obbligatorio (`chk_fondi_source_motivo_obbligatorio`), e l'atto arriva dal processo rimborsi di `pagamenti`, che l'eccedenza la conosce |

⚠️ Il passo che restringe il guard è un changeSet **a parte** (`20260815-18`), e
il piano non lo elencava: senza di lui la colonna `origine` esisterebbe senza
governare nulla. Una colonna che distingue due regole vale quanto il codice che
legge la distinzione.

---

{% include-markdown "signature-core.md" %}

## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_consuma_plafond_titolo_iva_righe()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva)
> • [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti) — il registro dove scrive
>
Approfondimento funzioni:
> • [vendite.fn_resolve_iva_riga](/dbzero/vendite/funzioni/fn_resolve_iva_riga) — dice QUALE titolo vale (domanda di consumo), non quanto copre
> • [vendite.vw_fattura_righe_esposte](/dbzero/vendite/views/vw_fattura_righe_esposte) — dove il kit spezzato diventa due righe padre

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-03, `20261003-07`; rev 2026-10-04, `20261004-06`)

Consuma il plafond di un titolo IVA per **le righe di una fattura** che stanno sotto
quel titolo, e dice per ogni riga quanta parte va al titolo e quanta torna
all'aliquota ordinaria.

La regola, decisa da Tid il 2026-10-04 (decisione C,
`brief-db-bom-flag-quantita-e-kit-in-fattura` §13): **la fattura consuma il suo
valore netto**. Le righe positive consumano, le righe negative (uno sconto, un
componente di kit negativo) restituiscono. Una fattura non consuma più della
capienza e non restituisce più di quanto essa stessa consuma.

Esempio: plafond residuo 500, merce 1000 e sconto −100. Netto 900, coperti 500:
merce 600 al titolo e 400 all'ordinaria, sconto −100 al titolo. Nel registro:
+600 e −100, cioè 500.

---

### Come divide

**1. I gruppi.** Le righe con la stessa `kit_key` sono un gruppo: un kit si spezza
come un'unità sola, con la stessa frazione per tutti i componenti (decisione D-5).
Una riga fuori da un kit è un gruppo da sola. I gruppi vanno nell'ordine di stampa
(la loro prima riga): a plafond quasi esaurito è l'ordine che decide chi resta
coperto. **I gruppi li fa la funzione**, leggendo le righe: il chiamante passa solo
quali righe.

**2. L'importo** di ogni riga si legge dalla riga stessa (`imponibile_riga`). Il
chiamante passa comunque gli importi su cui ha ragionato (`p_imponibili`, la firma
non è cambiata): devono essere quelli della riga, o la chiamata si ferma — vuol dire
che la riga è cambiata dopo che il chiamante l'ha letta.

**3. La quota di ogni gruppo**, sul netto:

| Gruppo | Quanto si copre |
| --- | --- |
| netto **negativo** | fino a quanto valgono i positivi della stessa fattura, in ordine. Il negativo che avanza resta all'ordinaria |
| netto **positivo** | fino alla capienza **più** quanto hanno restituito i negativi, in ordine: il primo per intero, poi uno spezzato, poi gli altri all'ordinaria |
| netto **zero** (un omaggio nel kit, o +50 e −50) | per intero: non consuma niente, quindi il titolo non ha motivo di lasciarlo |

⚠️ **Perché il negativo che avanza non restituisce.** Restituire plafond consumato da
un **altro** documento è il mestiere della nota di credito, che quel documento lo
nomina (P4). Qui la fattura nettizza solo sé stessa.

**4. Dentro il gruppo** la frazione è una: ogni riga prende
`imponibile × frazione`, arrotondato alla scala del suo imponibile (cioè
all'arrotondamento del suo articolo), così la riga spezzata ricalcola esattamente la
sua quota. Il resto dei centesimi va alla riga col **valore assoluto più grande
dello stesso segno del gruppo** (a pari merito l'ultima), poi alle successive se il
suo margine non basta. Nessuna quota cambia segno né supera il suo imponibile, e la
somma è esatta.

Esempio di kit: imponibile 500 su un plafond che ne lascia 200. Frazione 0,4: ogni
componente al titolo per il 40%. In fattura escono due righe di kit: 1,2 kit al
titolo e 1,8 all'ordinaria.

**5. Il registro**: un movimento `FATTURA` per riga con quota diversa da zero, **col
segno della riga**. Prima tutti i positivi, poi i negativi: l'accumulatore rifiuta un
conto sotto zero a ogni movimento scritto, e un negativo scritto per primo su un
titolo intonso lo farebbe scattare anche se la fattura, alla fine, consuma.

**6. Cosa ritorna**, per ogni riga: imponibile, quota coperta, quota ordinaria (che
sommano all'imponibile), la **frazione del suo gruppo** (con cui il chiamante divide
anche quantità e numero di kit), il residuo del titolo e il movimento scritto.

---

### Regole

* È la **sede delle regole di consumo**: guard di invocazione, lock sul titolo,
  validità alla data, titolo senza tetto (copre tutto e non scrive), idempotenza,
  capienza mai negativa.
* **Idempotenza**: se una delle righe ha già un movimento su questo titolo e questa
  fattura, si rilegge il registro. La quota di ogni riga è il suo movimento (zero
  dove non c'è), e la frazione del gruppo si ricava da lì. Con i movimenti col segno
  la rilettura è esatta.
* Le righe passate devono essere **della fattura**, **capofila** (una parte di
  plafond non consuma: il movimento sta sulla capofila) e **non rettifiche** (la loro
  IVA è quella della riga che rettificano). Un **kit si passa intero**: a metà, le
  due chiamate darebbero al kit due frazioni diverse. Nessuna riga `NULL` o
  ripetuta, un importo per riga e uguale a quello della riga.
* **Chi sceglie il titolo è il chiamante**: il backend risolve ogni gruppo con il
  risolutore nella domanda di consumo (un kit sull'articolo **padre**, D-5.1) e passa
  qui, in una chiamata, tutte le righe di quel titolo.
* Non è il risolutore (che non consuma) e non fa la restituzione della nota di
  credito.

⭐ **Ha preso il posto della forma a una riga** `fn_consuma_plafond_titolo_iva`,
ritirata il 2026-10-04 (`20261004-05`): consumava una riga alla volta, e chiamarla
per ogni componente non poteva dare una frazione unica, perché il residuo cambiava a
ogni chiamata. Con lei è uscita la forma storica «riga `NULL`»: un movimento di
fattura nomina sempre la sua riga.

---

{% include-markdown "signature-core.md" %}

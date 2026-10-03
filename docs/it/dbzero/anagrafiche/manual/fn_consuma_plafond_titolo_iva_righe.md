## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_consuma_plafond_titolo_iva_righe()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [anagrafiche.soggetti_titoli_iva](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva)
> • [anagrafiche.soggetti_titoli_iva_movimenti](/dbzero/anagrafiche/tabelle/soggetti_titoli_iva_movimenti)
>
Approfondimento funzioni:
> • [anagrafiche.fn_consuma_plafond_titolo_iva](/dbzero/anagrafiche/funzioni/fn_consuma_plafond_titolo_iva) — la forma a una riga, che è un involucro di questa
> • [vendite.vw_fattura_righe_esposte](/dbzero/vendite/views/vw_fattura_righe_esposte) — dove il kit spezzato diventa due righe padre

---

### 🎯 Scopo Principale

(funzione nata il 2026-10-03, `20261003-07`)

Consuma il plafond di un titolo IVA per un **gruppo di righe che si spezzano
insieme**: in pratica, i componenti di un kit. Un kit si spezza come un'unità sola,
con la stessa frazione per tutti i componenti (decisione D-5 di Tid,
`brief-db-bom-flag-quantita-e-kit-in-fattura` §11).

Esempio: un kit da 3, imponibile 500, su un plafond che ne lascia 200. La frazione è
200 / 500 = 0,4. Ogni componente va al titolo per il 40% del suo imponibile e
all'aliquota ordinaria per il resto. In fattura escono due righe di kit: 1,2 kit al
titolo e 1,8 kit all'ordinaria.

---

### ⭐ Perché non basta la forma a una riga

Il plafond si consumava una riga alla volta. Su un kit voleva dire componente per
componente: i primi coperti per intero, uno spezzato, gli ultimi all'ordinaria. E
chiamare la forma a una riga per ogni componente non può dare una frazione unica,
perché il residuo cambia a ogni chiamata. Serve **un lock e un calcolo** per tutto il
gruppo.

---

### Come divide

* La quota coperta si calcola sulla **somma** del gruppo, come sempre fino a capienza.
* Ogni riga prende `imponibile × frazione`, arrotondato alla scala del suo imponibile
  (cioè all'arrotondamento del suo articolo): la riga spezzata ricalcola esattamente
  la sua quota.
* L'**ultima** riga prende il resto, così la somma delle quote è la quota coperta.
  Il centesimo dell'arrotondamento finisce lì.
* Un movimento nel registro per ogni riga con quota maggiore di zero.
* Ritorna, per ogni riga, la quota coperta, la quota ordinaria e la **frazione
  effettiva**: il chiamante la usa per dividere anche la quantità del kit.

---

### Regole

* È la **sede delle regole di consumo**: guard di invocazione, lock sul titolo,
  validità alla data, titolo senza tetto (copre tutto e non scrive), idempotenza,
  capienza mai negativa. La forma a una riga le eredita da qui.
* **Idempotenza**: se una delle righe ha già un movimento su questo titolo e questa
  fattura, si rilegge il registro; le righe senza movimento valgono zero.
* Una riga `NULL` è ammessa solo in un gruppo di una riga (la forma storica, il
  movimento che nomina solo la fattura). Le righe nominate devono essere della
  fattura passata.
* **Chi raggruppa è il chiamante**: il backend raggruppa per kit e giudica il titolo
  sull'articolo **padre** del kit (D-5.1). La funzione sa solo che quelle righe si
  spezzano insieme.
* Non è il risolutore (che non consuma) e non restituisce plafond per le note di
  credito.

---

{% include-markdown "signature-core.md" %}

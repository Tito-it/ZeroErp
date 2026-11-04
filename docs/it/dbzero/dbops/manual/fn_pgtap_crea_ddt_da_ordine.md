## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ddt_da_ordine`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment) — il legame fra la riga d'ordine e la riga della bolla
>
> Approfondimento funzioni:
>
> * [vendite.fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine) — la madre da cui nasce la bolla
> * [dbops.fn_pgtap_crea_ordine_con_righe](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine_con_righe) — l'ordine confermato da cui parte
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarla avanti
> * [dbops.fn_pgtap_crea_ddt](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt) — la bolla in bozza senza ordine, per il magazzino
> * [dbops.fn_pgtap_crea_ddt_senza_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_senza_ordine) — il gemello, per la bolla senza ordine
> * [vendite.fn_annulla_ddt](/dbzero/vendite/funzioni/fn_annulla_ddt) — il verbo dell'annullo, che resta del test
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

Una bolla nata da un ordine confermato, nello stato chiesto (di norma **consegnata**), in
una chiamata sola, per la strada vera del dominio. È il punto di partenza di tutto ciò che
viene dopo la consegna: il reso, l'accredito, la situazione della merce, la fatturazione
delle bolle.

---

### ⭐ Perché esiste: la trappola d'ordine

Per avere una bolla consegnata servono cinque passi in un ordine obbligato: l'ordine con la
riga, la conferma, la bolla dall'ordine, la causale e gli indirizzi che l'emissione
pretende, i passaggi di stato uno per uno. Ogni test li riscriveva per conto suo, e quando
una regola cambiava si correggevano tutte le copie. La strada ha una sede sola.

---

### Che cosa decide la fixture e che cosa decide il dominio

* **L'ordine** lo costruisce
  [dbops.fn_pgtap_crea_ordine_con_righe](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine_con_righe),
  confermato: una riga di merce costruita (o dell'articolo del test), oppure le righe che il
  test descrive con più righe, sconto e date di consegna, nella grammatica di quel builder.
  Il momento di fatturazione, se il test lo sceglie, si scrive in bozza; senza, resta quello
  ereditato dal cliente. La data dell'ordine si sceglie alla nascita: chi dà alla bolla una
  data passata dà anche quella dell'ordine, perché una bolla più vecchia del suo ordine è
  una fixture incoerente col modello.
* **Il cliente** è quello del billing account passato dal test, verificato nell'azienda di
  chi agisce, oppure uno nuovo.
* **La bolla** la fa la madre
  [vendite.fn_genera_ddt_da_ordine](/dbzero/vendite/funzioni/fn_genera_ddt_da_ordine), come
  in produzione: copia le righe, scrive il legame con la riga d'ordine e proietta l'ordine a
  evaso o parzialmente evaso. Si evade tutto il residuo, oppure una quantità per l'unica
  riga attiva dell'ordine, oppure le righe nella grammatica della madre (le due scelte
  insieme sono un errore). La data della bolla è quella chiesta, o la data operativa.
* **Ciò che l'emissione pretende** e la cascata dall'ordine non porta: la causale per codice
  (di norma `VENDITA`) e gli indirizzi obbligatori mancanti.
* **Lo stato** si raggiunge per la matrice dei passaggi, sotto i controlli veri.
* **Un ordine speciale** — più righe, un kit coi componenti, una data che il test misura — lo
  costruisce e lo conferma il test, e lo passa: la bolla nasce da lì. Cliente, righe, data e
  momento di fatturazione sono allora dell'ordine, e passarli è un errore.

La fixture restituisce la bolla, la sua **prima** riga (per numero di riga) con la quantità
base, l'ordine e la riga d'ordine che quella riga evade, l'articolo, il cliente, l'azienda,
l'operatore e lo stato. Con più righe, il test le legge da sé.

---

### ⚠️ Con un onere nell'ordine, «la prima riga» può essere l'onere

Le righe-onere (il trasporto, le spese) passano dall'ordine alla bolla **intere**, nella
prima bolla, anche se il test non le ha chieste. La fixture non distingue la merce
dall'onere:

* la riga restituita è la prima per numero: se l'onere sta al numero 1, è l'onere;
* la quantità da evadere sull'«unica riga» conta tutte le righe attive dell'ordine, oneri
  compresi: un ordine con una riga di merce e un onere la rifiuta, e il test deve dare le
  righe nella grammatica della madre.

Il builder del reso, invece, sceglie già la prima riga di **merce**.

---

### ⛔ Che cosa non fa

* **Non lavora sulla bolla in bozza al posto del test**: una riga aggiunta a mano, un legame
  in più, un prezzo tolto sono il caso del test. Il test chiede la bolla in `DRAFT`, ci
  scrive, e la porta avanti con
  [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato).
* **Non annulla.** Uno stato abortito si rifiuta prima di costruire: la bolla nata da un
  ordine ha i legami con le righe d'ordine, e il suo annullo li dichiara il verbo
  [vendite.fn_annulla_ddt](/dbzero/vendite/funzioni/fn_annulla_ddt). Si chiede la bolla
  emessa e si annulla dal test.
* **Non sostituisce** [dbops.fn_pgtap_crea_ddt](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt), la
  bolla in bozza senza ordine dei test di magazzino.

---

### I parametri si giudicano prima di costruire

Uno stato o una causale che non esistono, uno stato abortito, la quantità e le righe insieme,
un ordine del test insieme a cliente, righe, data o momento di fatturazione: la fixture si
ferma **prima** di costruire, così un errore del chiamante non lascia un mondo a metà. Un
ordine che non esiste o non si vede si ferma subito dopo.

Senza un contesto aperto, il mondo lo apre sull'operatore che costruisce. Esce con i vincoli
**richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-ddt-da-ordine-v1.sql` — la bolla consegnata nata
  dall'ordine, col numero e la sorgente; il legame fra le due righe; l'ordine evaso; causale
  e indirizzi; la bozza; due spedizioni dalla stessa riga; momento di fatturazione e cliente
  del test; la causale scelta; la data dell'ordine; l'ordine con più righe del test; gli
  errori del chiamante e lo stato abortito rifiutati prima di costruire.

---

### Note di migrazione

* 2026-10-25 — nasce per raccogliere la strada che i test ricopiavano
  (`brief-db-pgtap-bolla-e-reso-costruiti`, giro 1). Lo stesso giorno: lo stato abortito si
  rifiuta prima di costruire; la data dell'ordine si sceglie alla nascita; l'ordine passa al
  builder dell'ordine con le righe, che ritira la copia della strada che stava qui
  (`brief-db-pgtap-reso-costruito`, E-1).
* 2026-10-27 — lo stato iniziale si legge dalla testata e non dal vocabolario
  (`brief-modello-documento-vendita` §15.13).
* 2026-11-03 — con gli oneri sulle righe d'ordine e di bolla, il censimento di
  `brief-db-addebito-trasporto-ordine` (§8.1) segnala che la fixture prende «la prima riga»;
  il giro ha corretto solo il builder del reso.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}

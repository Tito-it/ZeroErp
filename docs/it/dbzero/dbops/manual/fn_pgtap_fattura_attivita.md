## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_fattura_attivita`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — l'attività fatturabile che si aggancia alla riga
> * [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe) — le righe che la fixture scrive
>
> Approfondimento funzioni:
>
> * [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) — la madre che emette le attività
> * [dbops.fn_pgtap_crea_commessa_attivita](/dbzero/dbops/funzioni/fn_pgtap_crea_commessa_attivita) — le attività da fatturare
> * [dbops.fn_pgtap_crea_fattura](/dbzero/dbops/funzioni/fn_pgtap_crea_fattura) — la testata senza lotto
> * [vendite.fn_get_or_create_fattura_header](/dbzero/vendite/funzioni/fn_get_or_create_fattura_header) — la testata dentro un lotto
> * [vendite.fn_cleanup_fatture_by_ids](/dbzero/vendite/funzioni/fn_cleanup_fatture_by_ids) — il verbo che toglie la fattura, se il test lo vuole
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **una o più attività di commessa fatturate**, emesse dal dominio e agganciate a una
fattura vera in bozza, una riga per attività. Restituisce, nell'ordine delle attività, attività,
attività fatturabile, fattura e riga.

Accrediti, rinunce, annulli, chiusure delle partite e lotti partono tutti da «un'attività già
fatturata». I test la costruivano a mano, ognuno a modo suo. Nessuna funzione del dominio scrive
le righe di fattura — le scrive il backend — quindi ogni file le riscriveva: ora la strada ha una
sede.

---

### ⭐ La trappola d'ordine che la fixture tiene

* **Le attività** le costruisce il test (con la loro sorgente, quantità e prezzo): qui si fattura
  ciò che c'è. Devono essere tutte dello stesso conto: una fattura è di un cliente solo.
* **L'emissione** la fa la madre, una volta per commessa, col marchio del lotto se c'è. ⚠️ La madre
  emette **tutte** le attività approvate e non emesse delle commesse coinvolte, non solo quelle
  passate.
* **L'attività fatturabile** si prende **per attività**, l'ultima ancora libera: non per segmento,
  che con le rettifiche prende la riga sbagliata.
* **La testata**: senza lotto da `dbops.fn_pgtap_crea_fattura`, in bozza sul conto delle attività;
  con un lotto dalla funzione del dominio che crea la testata del lotto.
* **Le righe**: quantità, prezzo, articolo, unità e competenza dall'attività fatturabile, la prima
  aliquota IVA attiva, imponibile uguale a quantità per prezzo; una riga per istruzione, in bozza.
* **L'aggancio** della riga all'attività fatturabile viene dopo la riga (il guard sul fatturato
  ammette solo il passaggio da vuoto a valorizzato); col lotto anche il lucchetto e il marchio del
  lotto.

Attività assenti o invisibili, ripetute, di conti diversi, senza un'attività fatturabile libera
dopo l'emissione, o un lotto che non esiste fermano la fixture prima di scrivere.

---

### Che cosa non fa

**Non porta avanti la fattura**: resta in bozza. Emetterla, portarla avanti o toglierla è il caso
del test. Esce con i vincoli richiusi (`IMMEDIATE`).

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-fattura-attivita-v1.sql` — un'attività con la sua fattura in bozza
  e la riga agganciata; l'attività fatturabile scelta per attività; due attività della stessa
  commessa in una fattura, nell'ordine dato; col lotto la testata è del lotto e l'attività
  fatturabile porta marchio e lucchetto; nessuna attività, un'attività già fatturata e attività di
  due conti rifiutate.

---

### Note di migrazione

* 2026-10-25 — nasce per i test del reso costruito (`brief-db-pgtap-reso-costruito`, E-2).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}

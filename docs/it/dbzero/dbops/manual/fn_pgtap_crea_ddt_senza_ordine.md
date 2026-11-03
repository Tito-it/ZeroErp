## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ddt_senza_ordine`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_crea_ddt](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt) — la testata in bozza su cui si appoggia
> * [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — il cliente: quello del test o uno nuovo
> * [dbops.fn_pgtap_crea_ddt_da_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_da_ordine) — il gemello, per la bolla nata da un ordine
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarla avanti
> * [vendite.fn_annulla_ddt](/dbzero/vendite/funzioni/fn_annulla_ddt) — il verbo dell'annullo, che resta del test
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

Una bolla **senza ordine** dietro, con una riga prezzata, nello stato chiesto (di norma
**consegnata**), in una chiamata sola, per la strada vera del dominio.

---

### ⭐ Perché esiste

Per uscire dalla bozza una bolla senza ordine pretende una riga, e la riga deve portare da sé
prezzo e aliquota: senza ordine non c'è da dove ereditarli. Una dozzina di test scrivevano a
mano testata, indirizzi, causale, riga e passaggi di stato. Il builder della testata
([dbops.fn_pgtap_crea_ddt](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt)) dà la bozza senza righe,
che serve al magazzino: mancava proprio il passo con la trappola.

---

### Che cosa decide la fixture e che cosa decide il dominio

* **Il cliente** è quello del billing account passato dal test, verificato nell'azienda di
  chi agisce, oppure uno nuovo; senza un contesto aperto il mondo lo apre sull'operatore che
  costruisce.
* **La testata** la fa [dbops.fn_pgtap_crea_ddt](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt):
  causale per codice (di norma `VENDITA`; una che non esiste la rifiuta lui), magazzino,
  data alla nascita, indirizzi obbligatori.
* **La riga** è una sola: 10 pezzi a 25 se il test non dice altro, con la prima aliquota
  attiva, dell'articolo del test o di un articolo di merce non gestita costruito apposta.
* **Lo stato** si raggiunge per la matrice dei passaggi, sotto i controlli veri.

Restituisce la bolla, la riga con la quantità base, l'articolo, il cliente, l'azienda,
l'operatore e lo stato.

---

### ⛔ Che cosa non fa

* **Non muove merce**: un articolo gestito a magazzino si rifiuta. I test che muovono merce
  scrivono righe e prelievi da sé, sulla bozza di
  [dbops.fn_pgtap_crea_ddt](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt): sono il loro caso.
* **Non annulla**: uno stato abortito si rifiuta. L'annullo è del verbo
  [vendite.fn_annulla_ddt](/dbzero/vendite/funzioni/fn_annulla_ddt).

Stato, articolo gestito e stato abortito si giudicano **prima** di costruire. Esce con i
vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-ddt-senza-ordine-v1.sql` — la bolla consegnata senza
  sorgente, col numero; la riga prezzata con l'aliquota su un articolo costruito non gestito;
  causale e indirizzi completi; bozza, data, causale e cliente scelti; la data alla nascita
  del builder della testata; merce gestita e stato abortito rifiutati.

---

### Note di migrazione

* 2026-10-25 — nasce per raccogliere la strada che i test ricopiavano
  (`brief-db-pgtap-reso-costruito`, E-5).
* 2026-10-27 — lo stato iniziale si legge dalla testata e non dal vocabolario
  (`brief-modello-documento-vendita` §15.13).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}

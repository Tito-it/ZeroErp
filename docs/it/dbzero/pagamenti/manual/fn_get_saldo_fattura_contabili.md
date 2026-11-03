## 📘 Documentazione Concettuale – Funzione `pagamenti.fn_get_saldo_fattura_contabili`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili_righe](/dbzero/pagamenti/tabelle/vendite_contabili_righe) — le righe che somma
> * [pagamenti.vendite_contabili_righe_stati](/dbzero/pagamenti/tabelle/vendite_contabili_righe_stati) — quali stati sono postabili
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — la testata, che deve essere non finale
> * [pagamenti.vendite_contabili_stati](/dbzero/pagamenti/tabelle/vendite_contabili_stati) — quali stati della testata sono finali
>
> Approfondimento funzioni:
>
> * [pagamenti.fn_get_saldo_fattura](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) — le delega il dichiarato, la sua colonna `in_lavorazione`
> * [vendite.fn_saldo_sorgente_fondo](/dbzero/vendite/funzioni/fn_saldo_sorgente_fondo) — la chiama per sapere quanto è in lavorazione sulla sorgente del fondo

---

### 🎯 Scopo Principale

La funzione **`pagamenti.fn_get_saldo_fattura_contabili`** restituisce il **dichiarato** di una
fattura: la somma delle righe contabili attive, in uno stato postabile, sotto una testata non
finale. È la sede unica di questo numero.

Risponde con `saldo_contabile`, la somma, e `has_righe_postabili`, se almeno una riga conta.

---

### Una riga conta finché è pronta e la sua distinta è viva

Entrano nella somma solo le righe che hanno insieme queste tre cose:

* la riga è attiva;
* il suo stato è postabile (`vendite_contabili_righe_stati.is_postabile`);
* la sua testata contabile è in uno stato **non finale** (`vendite_contabili_stati.is_final`).

Una riga sotto una distinta chiusa non è in lavorazione: è ferma. Lo stato della testata è
sempre valorizzato, quindi non c'è un caso «testata senza stato» da trattare.

---

### ⭐ Una sede sola per il dichiarato

[`fn_get_saldo_fattura`](/dbzero/pagamenti/funzioni/fn_get_saldo_fattura) non riscrive il
predicato: chiede a questa funzione il proprio `in_lavorazione`. Due formule per la stessa regola
divergono al primo aggiustamento.

⚠️ Chi legge il saldo di un documento prende `in_lavorazione` da `fn_get_saldo_fattura`, non da
qui: il numero è lo stesso, e leggerlo da due funzioni gli darebbe due sorgenti con lo stesso
nome.

---

### ⭐ Escludere una riga: «quanto era dichiarato prima di me»

`p_escludi_contabile_riga_id`, facoltativo: la riga indicata **non si conta**. Serve a chi sta
scrivendo o correggendo proprio quella riga, che altrimenti si confronterebbe con sé stessa. È lo
stesso parametro, con lo stesso mestiere, di `fn_get_saldo_rata` e del nucleo
`fn_get_saldi_rate`; lo riceve da `fn_get_saldo_fattura`, che glielo passa.

---

### Codici errore

* `E_PAGAMENTI_CHIAMATA_NON_VALIDA` (`TECNICO`) — `p_fattura_id` nullo o non positivo, oppure
  un'esclusione fornita e non positiva: valori che nessuna interfaccia produce, e l'operatore non
  ha niente da correggere.

---

### Test

* `db/pgtap/pagamenti/test-vendite-contabili-stato-obbligatorio.sql` — una riga postabile sotto
  una distinta non finale entra nel saldo, ed esce quando la distinta passa a uno stato finale;
  `has_righe_postabili` segue lo stesso confine; il rifiuto del parametro.
* `db/pgtap/pagamenti/test-fn-get-saldo-fattura-tre-numeri.sql` — coincide con
  `in_lavorazione` della funzione del documento, riceve l'esclusione, rifiuta un'esclusione non
  positiva.
* `db/pgtap/pagamenti/test-righe-contabili-eliminazione-v1.sql` — una riga nuova in bozza entra
  nel dichiarato, una riga eliminata ne esce.

---

### Note di migrazione

* 2026-02-13 — prima stesura.
* 2026-08-21 — cade il ramo «testata senza stato», reso impossibile dal `NOT NULL` sullo stato
  della testata; il rifiuto dei parametri passa al codice registrato.
* 2026-09-18 — nasce `p_escludi_contabile_riga_id`.
  Cambiando la firma la funzione è stata ricreata, perché un secondo overload accanto alla
  vecchia versione a un argomento sarebbe stato ambiguo per ogni chiamata.

---

{% include-markdown "signature-core.md" %}

## 📘 Documentazione Concettuale – Trigger function `pagamenti.trgfn_vendite_contabili_guard_ente_centro`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pagamenti.vendite_contabili](/dbzero/pagamenti/tabelle/vendite_contabili) — dove è montato
> * [pagamenti.enti_incasso](/dbzero/pagamenti/tabelle/enti_incasso) — il canale, che porta il proprio centro
> * [pagamenti.centri_riscossione](/dbzero/pagamenti/tabelle/centri_riscossione) — il centro della distinta
>
> Approfondimento funzioni:
>
> * [pagamenti.trgfn_sistemazioni_guard_dati](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_dati) — dove vive la regola del centro di compensazione
> * [pagamenti.trgfn_vendite_contabili_lotti_guard_sistemazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_lotti_guard_sistemazione) — dove vive il divieto di agganciare a un lotto una distinta nata da un atto

---

### 🎯 Scopo Principale

Tiene coerenti il canale e il centro della distinta contabile: se la testata nomina un
ente di incasso, quell'ente deve avere un centro di riscossione, e deve essere lo stesso
della testata. Senza canale non controlla niente.

⭐ Il canale porta anche il **conto** su cui atterra il denaro: questo guard è ciò che tiene
insieme centro, canale e conto sulla stessa distinta.

---

### Due cause, un codice

L'ente che non esiste e l'ente che esiste ma non ha un centro (la colonna è facoltativa)
danno lo stesso rifiuto, `E_ENTE_INCASSO_SENZA_CENTRO`: il rimedio è lo stesso, si va a
guardare l'ente. Un ente con un centro diverso da quello della distinta è
`E_CONTABILE_CENTRO_ENTE_INCOERENTE`, e la frase nomina i due centri.

---

### ⭐ Le regole delle distinte nate da un atto non stanno qui

La distinta non sa di essere nata da una sistemazione: lo sa l'atto, che tiene l'id della
distinta che ha generato. Le due regole che riguardano quelle distinte vivono quindi dove il
dato che le rende decidibili esiste davvero:

| Regola | Dove vive |
| --- | --- |
| il centro dev'essere quello di compensazione | [trgfn_sistemazioni_guard_dati](/dbzero/pagamenti/funzioni/trgfn_sistemazioni_guard_dati) |
| la distinta non si aggancia a un lotto di fatturazione | [trgfn_vendite_contabili_lotti_guard_sistemazione](/dbzero/pagamenti/funzioni/trgfn_vendite_contabili_lotti_guard_sistemazione) |

*Un controllo che scatta quando l'informazione non c'è ancora non è un presidio: alla
nascita della distinta nessun atto la cita.*

---

### Codici errore

* `E_ENTE_INCASSO_SENZA_CENTRO` — l'ente di incasso non esiste, o non ha un centro di
  riscossione.
* `E_CONTABILE_CENTRO_ENTE_INCOERENTE` — il centro dell'ente non è quello della distinta.

---

### Test

* `db/pgtap/pagamenti/test-contabile-guard-ente-centro-v1.sql` — la distinta col canale e il suo
  centro nasce; con un altro centro, o con un canale senza centro, è rifiutata; il centro non si
  cambia dopo; senza canale il guard tace.

---

### Note di migrazione

* 2026-08-21 — i rifiuti generici passano ai codici registrati, senza cambiare
  nessun predicato.
* 2026-08-22 — sparisce il ramo delle compensazioni, che si apriva su una
  colonna della testata che nominava l'atto; la colonna sparisce girando il verso del legame,
  e le due regole passano ai guard dell'atto e del lotto. La lista di colonne del trigger è
  stata ricreata senza quella colonna: una lista di colonne crea una dipendenza vera nel
  catalogo, e con la colonna dentro la sua eliminazione sarebbe fallita (il corpo di una
  funzione plpgsql, invece, non crea dipendenze).

---

{% include-markdown "signature-core.md" %}

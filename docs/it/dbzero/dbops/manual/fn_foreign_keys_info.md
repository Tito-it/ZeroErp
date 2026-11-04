## 📘 Documentazione Concettuale – Funzione `dbops.fn_foreign_keys_info`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_find_file_usage](/dbzero/dbops/funzioni/fn_find_file_usage) — le sole chiavi esterne in entrata, lette dal catalogo e con lo schema
> * [dbops.fn_get_child_fk_col](/dbzero/dbops/funzioni/fn_get_child_fk_col) — la colonna figlia di un vincolo dato

---

### 🎯 Scopo Principale

Le chiavi esterne in cui compare una tabella, indicata col solo nome: quelle **in entrata** (altre
tabelle che la puntano) e quelle **in uscita** (definite su di lei), distinte da `relazione`. È un
attrezzo di consultazione da lanciare a mano; nessun oggetto del database la chiama.

---

### ⚠️ Che cosa non distingue

* **Lo schema.** La tabella si passa col solo nome, e nomi di tabelle e colonne escono senza schema:
  due tabelle omonime in schemi diversi finiscono mescolate nella stessa risposta.
* **Le chiavi esterne su più colonne.** Ogni colonna figlia viene accoppiata con ogni colonna puntata,
  non per posizione: un vincolo su due colonne dà quattro righe, due delle quali sbagliate.
* **Due vincoli con lo stesso nome nello stesso schema.** PostgreSQL ammette lo stesso nome di
  vincolo su due tabelle diverse, e la funzione li riconosce dal solo nome: le loro colonne si
  mescolano.
* **Ciò che chi chiama non può vedere.** La funzione legge `information_schema`, che mostra solo gli
  oggetti su cui il ruolo corrente ha privilegi (e, per le colonne puntate, solo le tabelle di cui è
  proprietario): con un ruolo applicativo la risposta può essere incompleta senza dirlo.

Per un'analisi d'impatto in entrata su una tabella precisa, `dbops.fn_find_file_usage` risponde con
lo schema e senza dipendere dai privilegi.

---

{% include-markdown "signature-core.md" %}

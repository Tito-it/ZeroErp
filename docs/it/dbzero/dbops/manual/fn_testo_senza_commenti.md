## 📘 Documentazione Concettuale – Funzione `dbops.fn_testo_senza_commenti`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [dbops.fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione) — la porta da cui passa chi legge il corpo di una funzione
> * [dbops.fn_regexp_occorrenze](/dbzero/dbops/funzioni/fn_regexp_occorrenze) — l'altra primitiva testuale dei presidi

---

### 🎯 Scopo Principale

Dato un testo SQL, lo restituisce senza i commenti di riga e a blocco, lasciando intatti i letterali
e gli identificatori fra virgolette anche quando contengono i segni di un commento. È metà del
building block «il corpo di una funzione, senza i commenti»: l'altra metà è
[fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione).

---

### ⭐ Una lettura sola, da sinistra: il primo carattere decide

Il testo si percorre una volta, da sinistra, e in ogni punto la prima cosa che comincia decide che
cos'è il pezzo:

* un **letterale** fra apici, anche nella forma con le sequenze di escape (dove un apice preceduto
  dalla barra rovesciata non chiude), oppure un **identificatore** fra virgolette doppie: si rimette
  com'è;
* un **commento di riga**: si toglie fino a fine riga;
* un **commento a blocco**: si toglie intero, anche se va su più righe.

⇒ Un doppio trattino dentro una stringa cade nella stringa, che comincia prima; un apice dentro un
commento cade nel commento. È proprio il caso che le copie ritirate sbagliavano: un codice scritto
sulla stessa riga dopo una stringa che conteneva un doppio trattino spariva, e un nome dentro un
commento a blocco restava.

⚠️ **Il commento a blocco è scritto in modo da non poter contenere la sua chiusura.** In PostgreSQL
un'alternativa al primo livello di un'espressione regolare è sempre greedy: una forma «pigra» del
commento a blocco si mangerebbe tutto fino all'**ultima** chiusura del testo, codice compreso fra due
commenti. Per questo il commento finisce alla prima chiusura per costruzione, non per pigrizia.

---

### Che cosa non fa

* **non riconosce le stringhe dollar-quoted interne** al testo: un doppio trattino dentro una di
  loro si toglie fino a fine riga come un commento;
* **non riconosce i commenti a blocco annidati**: il commento finisce alla prima chiusura;
* senza un testo restituisce nulla.

È immutabile: lo stesso testo dà sempre lo stesso risultato.

⛔ Quando il testo è il corpo di una funzione non la si chiama direttamente: si passa da
[fn_corpo_funzione](/dbzero/dbops/funzioni/fn_corpo_funzione), che sa anche dove sta il corpo di una
funzione `BEGIN ATOMIC`.

---

### Test

* `db/pgtap/dbops/test-corpo-funzione-senza-commenti-v1.sql`, test 1-6 — un doppio trattino dentro
  un letterale resta e il commento di riga vero esce; un commento a blocco su più righe esce col
  codice che nomina; il codice **fra** due commenti a blocco resta (la trappola greedy); un letterale
  con un apice preceduto dalla barra rovesciata non sposta il resto; un identificatore che contiene
  un doppio trattino resta intero; senza testo, nulla.

---

### Note di migrazione

* 2026-11-04 — nasce per D14 e D15 di `brief-db-revisione-dbops`: nove viste e due strumenti
  toglievano i commenti ognuno a modo suo e leggevano il sorgente testuale, vuoto per le
  `BEGIN ATOMIC`.

---

{% include-markdown "signature-core.md" %}
